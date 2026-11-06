import os
import copy
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.ml.preprocessor import FraudFeaturePipeline
from backend.app.ml.fixed_model import FixedFraudModel
from backend.app.ml.adaptive_model import AdaptiveFraudModel
from backend.app.ml.drift_detector import AdaptiveSlidingWindowDriftDetector
from backend.app.ml.evaluation import compute_metrics, compare_models
from backend.app.models.db_models import (
    DBTransaction, DBModelVersion, DBDriftEvent, DBAlert, DBAuditLog
)

logger = logging.getLogger("driftguard.adaptive_service")

PREPROCESSOR_PATH = "backend/models_saved/preprocessor.joblib"
FIXED_MODEL_PATH = "backend/models_saved/fixed_model.joblib"
ADAPTIVE_MODEL_PATH = "backend/models_saved/adaptive_model.joblib"

class AdaptiveLearningService:
    """
    Coordinates real-time fraud prediction, delayed verified feedback processing,
    concept drift detection, candidate model validation, promotion, and rollback.
    """

    def __init__(
        self,
        preprocessor_path: str = PREPROCESSOR_PATH,
        fixed_model_path: str = FIXED_MODEL_PATH,
        adaptive_model_path: str = ADAPTIVE_MODEL_PATH
    ):
        self.preprocessor_path = preprocessor_path
        self.fixed_model_path = fixed_model_path
        self.adaptive_model_path = adaptive_model_path

        # Load models
        self.preprocessor: Optional[FraudFeaturePipeline] = None
        self.fixed_model: Optional[FixedFraudModel] = None
        self.adaptive_model: Optional[AdaptiveFraudModel] = None
        self.last_stable_model: Optional[AdaptiveFraudModel] = None
        self.last_stable_version_tag: Optional[str] = None

        self._load_models()

        # Initialize concept drift detector
        self.drift_detector = AdaptiveSlidingWindowDriftDetector(
            recent_window_size=80,
            reference_window_size=400,
            min_samples_to_detect=30,
            warning_delta=0.06,
            critical_delta=0.12
        )

        # Counter of verified feedback received since last retraining attempt
        self.feedback_since_last_retrain: int = 0
        self.retrain_feedback_threshold: int = 40

    def _load_models(self):
        """Load fitted pipeline and models from disk."""
        if os.path.exists(self.preprocessor_path):
            self.preprocessor = FraudFeaturePipeline.load(self.preprocessor_path)
            logger.info("Loaded preprocessor artifact.")
        else:
            logger.warning(f"Preprocessor artifact not found at {self.preprocessor_path}.")

        if os.path.exists(self.fixed_model_path):
            self.fixed_model = FixedFraudModel.load(self.fixed_model_path)
            logger.info("Loaded fixed fraud model artifact.")
        else:
            logger.warning(f"Fixed model artifact not found at {self.fixed_model_path}.")

        if os.path.exists(self.adaptive_model_path):
            self.adaptive_model = AdaptiveFraudModel.load(self.adaptive_model_path)
            self.last_stable_model = None
            self.last_stable_version_tag = None
            logger.info(f"Loaded adaptive fraud model ({self.adaptive_model.version_tag}).")
        else:
            logger.warning(f"Adaptive model artifact not found at {self.adaptive_model_path}.")

    def predict_transaction(self, tx_dict: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Sequence A -> B -> C:
        Receives transaction features, extracts features, generates predictions
        for both fixed and adaptive models, and persists record in SQLite with predictions.
        Crucial: Ground truth is never used for prediction.
        """
        if self.preprocessor is None or self.fixed_model is None or self.adaptive_model is None:
            self._load_models()
            if self.preprocessor is None or self.fixed_model is None or self.adaptive_model is None:
                raise RuntimeError("ML Models are not initialized. Run training pipeline first.")

        # Extract features (leakage-free)
        feature_vector = self.preprocessor.transform(tx_dict)

        # Generate predictions
        fixed_pred, fixed_score = self.fixed_model.predict_single(feature_vector)
        adaptive_pred, adaptive_score = self.adaptive_model.predict_single(feature_vector)

        # Ensure tx_id
        tx_id = tx_dict.get("tx_id") or f"TX_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        ground_truth = tx_dict.get("is_fraud_ground_truth") or tx_dict.get("is_fraud")

        # Persist transaction
        db_tx = DBTransaction(
            tx_id=tx_id,
            amount=float(tx_dict["amount"]),
            merchant_category=str(tx_dict.get("merchant_category", "retail")),
            distance_from_home=float(tx_dict.get("distance_from_prev", tx_dict.get("distance_from_home", 5.0))),
            foreign_transaction=int(tx_dict.get("foreign_transaction", 0)),
            device_trust_score=float(tx_dict.get("device_trust_score", 0.9)),
            velocity_1h=int(tx_dict.get("velocity_1h", 1)),
            ip_risk_score=float(tx_dict.get("ip_risk_score", 0.05)),
            pattern_type=str(tx_dict.get("pattern_type", "standard_legitimate")),
            is_fraud_ground_truth=int(ground_truth) if ground_truth is not None else 0,
            fixed_prediction=fixed_pred,
            fixed_score=round(fixed_score, 4),
            adaptive_prediction=adaptive_pred,
            adaptive_score=round(adaptive_score, 4),
            feedback_received=False
        )
        db.add(db_tx)
        db.commit()
        db.refresh(db_tx)

        return {
            "id": db_tx.id,
            "tx_id": db_tx.tx_id,
            "timestamp": db_tx.timestamp,
            "amount": db_tx.amount,
            "merchant_category": db_tx.merchant_category,
            "distance_from_home": db_tx.distance_from_home,
            "foreign_transaction": db_tx.foreign_transaction,
            "device_trust_score": db_tx.device_trust_score,
            "velocity_1h": db_tx.velocity_1h,
            "ip_risk_score": db_tx.ip_risk_score,
            "pattern_type": db_tx.pattern_type,
            "fixed_prediction": fixed_pred,
            "fixed_score": round(fixed_score, 4),
            "adaptive_prediction": adaptive_pred,
            "adaptive_score": round(adaptive_score, 4),
            "adaptive_version": self.adaptive_model.version_tag
        }

    def process_verified_feedback(
        self,
        tx_id: str,
        ground_truth: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Sequence D -> E -> F -> G:
        Processes delayed verified label for an existing transaction.
        Evaluates prediction error, updates drift detector, logs drift events,
        and triggers candidate model training if criteria are met.
        """
        db_tx = db.query(DBTransaction).filter(DBTransaction.tx_id == tx_id).first()
        if not db_tx:
            raise ValueError(f"Transaction with tx_id '{tx_id}' not found.")

        # Update transaction record
        db_tx.feedback_received = True
        db_tx.feedback_label = ground_truth
        db_tx.feedback_timestamp = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_tx)

        # Check prediction error (comparing adaptive model prediction recorded at transaction time)
        prediction_correct = (db_tx.adaptive_prediction == ground_truth)
        is_error = 0 if prediction_correct else 1

        # Update Concept Drift Detector
        drift_status = self.drift_detector.add_element(is_error)
        self.feedback_since_last_retrain += 1

        # Check for drift event recording in database
        learning_action = "none"
        if drift_status["drift_detected"]:
            # Record drift event
            drift_event = DBDriftEvent(
                detector_name="AdaptiveSlidingWindowDriftDetector",
                metric_tracked="prediction_error_rate",
                pre_drift_mean=drift_status["reference_error_rate"],
                post_drift_mean=drift_status["current_error_rate"],
                delta_or_stat=round(drift_status["current_error_rate"] - drift_status["reference_error_rate"], 4),
                window_size=drift_status["recent_samples_count"],
                severity=drift_status["severity"],
                action_taken="Candidate validation triggered" if self.feedback_since_last_retrain >= 15 else "Monitoring",
                details=drift_status["status_message"]
            )
            db.add(drift_event)

            # Record system alert
            alert = DBAlert(
                tx_id=tx_id,
                alert_type="CONCEPT_DRIFT",
                severity=drift_status["severity"],
                message=drift_status["status_message"],
                details_json=json.dumps(drift_status, default=str)
            )
            db.add(alert)
            db.commit()

        # Decide whether to trigger candidate model learning
        # Conditions:
        # 1. Critical drift detected AND >= 15 feedback samples since last retrain attempt
        # 2. Warning drift detected AND >= 25 feedback samples
        # 3. Accumulated feedback >= 40 (routine cadence)
        should_retrain = False
        if drift_status["severity"] == "CRITICAL" and self.feedback_since_last_retrain >= 15:
            should_retrain = True
        elif drift_status["severity"] == "WARNING" and self.feedback_since_last_retrain >= 25:
            should_retrain = True
        elif self.feedback_since_last_retrain >= self.retrain_feedback_threshold:
            should_retrain = True

        if should_retrain:
            validation_result = self.train_and_validate_candidate(db)
            learning_action = validation_result["action"]
            self.feedback_since_last_retrain = 0
        else:
            db.commit()

        return {
            "tx_id": tx_id,
            "feedback_recorded": True,
            "prediction": db_tx.adaptive_prediction,
            "ground_truth": ground_truth,
            "prediction_correct": prediction_correct,
            "drift_status": drift_status,
            "learning_action_triggered": learning_action
        }

    def train_and_validate_candidate(self, db: Session) -> Dict[str, Any]:
        """
        Sequence G -> H -> I:
        Trains candidate model on recent verified data, validates candidate
        against active model on a chronological holdout window, and promotes or rejects.
        """
        # Fetch verified transactions from database in chronological order
        verified_txs = (
            db.query(DBTransaction)
            .filter(DBTransaction.feedback_received == True)
            .order_by(DBTransaction.id.asc())
            .all()
        )

        min_required = 40
        if len(verified_txs) < min_required:
            msg = f"Insufficient verified samples for candidate validation ({len(verified_txs)}/{min_required})."
            logger.info(msg)
            return {"action": "deferred", "reason": msg}

        # Convert to DataFrame
        records = []
        for tx in verified_txs:
            records.append({
                "amount": tx.amount,
                "merchant_category": tx.merchant_category,
                "distance_from_prev": tx.distance_from_home,
                "foreign_transaction": tx.foreign_transaction,
                "device_trust_score": tx.device_trust_score,
                "velocity_1h": tx.velocity_1h,
                "ip_risk_score": tx.ip_risk_score,
                "tx_hour": tx.timestamp.hour if tx.timestamp else 12,
                "new_device": 1 if tx.device_trust_score < 0.6 else 0,
                "is_fraud": tx.feedback_label
            })
        
        # Chronological Split: 75% training, 25% validation holdout
        n_samples = len(records)
        split_idx = int(n_samples * 0.75)
        train_records = records[:split_idx]
        val_records = records[split_idx:]

        X_train = self.preprocessor.transform(train_records)
        y_train = np.array([r["is_fraud"] for r in train_records], dtype=int)

        X_val = self.preprocessor.transform(val_records)
        y_val = np.array([r["is_fraud"] for r in val_records], dtype=int)

        # Candidate Model: clone active adaptive model
        candidate = copy.deepcopy(self.adaptive_model)
        candidate.version_tag = f"candidate-{candidate.version_tag}"

        # Train candidate on verified training slice with fraud reweighting
        weights = np.where(y_train == 1, 2.5, 1.0)
        candidate.partial_fit(X_train, y_train, sample_weight=weights, promote_version=False)

        # Evaluate both models on identical chronological validation holdout
        active_val_preds = self.adaptive_model.predict(X_val)
        candidate_val_preds = candidate.predict(X_val)

        active_metrics = compute_metrics(y_val, active_val_preds, model_name="active_adaptive")
        candidate_metrics = compute_metrics(y_val, candidate_val_preds, model_name="candidate")

        # Candidate Validation Criteria
        # 1. Candidate recall >= active recall (or candidate F1 >= active F1)
        # 2. Candidate FPR <= 0.08 (guard against false positive explosion)
        # 3. Overall F1 score >= active F1 - 0.01
        recall_improved = candidate_metrics["recall"] >= active_metrics["recall"]
        f1_acceptable = candidate_metrics["f1_score"] >= (active_metrics["f1_score"] - 0.02)
        fpr_acceptable = candidate_metrics["fpr"] <= 0.08

        promoted = recall_improved and f1_acceptable and fpr_acceptable

        if promoted:
            # Promote Candidate
            # 1. Backup current active model
            self.last_stable_model = copy.deepcopy(self.adaptive_model)
            self.last_stable_version_tag = self.adaptive_model.version_tag

            # 2. Promote candidate
            new_counter = self.adaptive_model.version_counter + 1
            new_version_tag = f"v1.{new_counter}-adaptive-promoted"
            candidate.version_tag = new_version_tag
            candidate.version_counter = new_counter
            self.adaptive_model = candidate

            # 3. Save to disk
            self.adaptive_model.save(self.adaptive_model_path)

            # 4. Update SQLite version table
            # Mark previous active versions as superseded
            db.query(DBModelVersion).filter(
                DBModelVersion.model_name == "adaptive",
                DBModelVersion.status == "active"
            ).update({"status": "superseded"})

            mv = DBModelVersion(
                model_name="adaptive",
                version_tag=new_version_tag,
                sample_count=self.adaptive_model.total_samples_trained,
                accuracy=candidate_metrics["accuracy"],
                precision=candidate_metrics["precision"],
                recall=candidate_metrics["recall"],
                f1_score=candidate_metrics["f1_score"],
                fpr=candidate_metrics["fpr"],
                fnr=candidate_metrics["fnr"],
                status="active",
                description="Promoted candidate after verified validation holdout test.",
                metrics_json=json.dumps(candidate_metrics)
            )
            db.add(mv)

            # 5. Log audit
            audit = DBAuditLog(
                action="MODEL_PROMOTED",
                performed_by="AdaptiveLearningService",
                details=(
                    f"Promoted {new_version_tag}: Recall={candidate_metrics['recall']:.2%}, "
                    f"F1={candidate_metrics['f1_score']:.4f}, FPR={candidate_metrics['fpr']:.2%}. "
                    f"Previous: {self.last_stable_version_tag}"
                )
            )
            db.add(audit)
            db.commit()

            logger.info(f"Candidate model PROMOTED to active: {new_version_tag}")
            return {
                "action": "promoted",
                "promoted_version": new_version_tag,
                "previous_version": self.last_stable_version_tag,
                "candidate_metrics": candidate_metrics,
                "active_metrics": active_metrics
            }
        else:
            # Reject Candidate
            rejection_reasons = []
            if not recall_improved:
                rejection_reasons.append(f"Recall declined ({candidate_metrics['recall']:.2%} < {active_metrics['recall']:.2%})")
            if not f1_acceptable:
                rejection_reasons.append(f"F1 dropped ({candidate_metrics['f1_score']:.4f} < {active_metrics['f1_score']:.4f})")
            if not fpr_acceptable:
                rejection_reasons.append(f"FPR too high ({candidate_metrics['fpr']:.2%} > 8.0%)")

            reason_str = "; ".join(rejection_reasons)
            audit = DBAuditLog(
                action="CANDIDATE_REJECTED",
                performed_by="AdaptiveLearningService",
                details=f"Candidate rejected: {reason_str}"
            )
            db.add(audit)
            db.commit()

            logger.info(f"Candidate model REJECTED: {reason_str}")
            return {
                "action": "rejected",
                "active_version": self.adaptive_model.version_tag,
                "rejection_reasons": rejection_reasons,
                "candidate_metrics": candidate_metrics,
                "active_metrics": active_metrics
            }

    def rollback(self, db: Session) -> Dict[str, Any]:
        """
        Rollback the active adaptive model to the previous stable version.
        """
        if self.last_stable_model is None or self.last_stable_version_tag is None:
            return {
                "success": False,
                "message": "No previous stable model version is available for rollback.",
                "active_version": self.adaptive_model.version_tag if self.adaptive_model else "unknown"
            }

        rolled_version = self.adaptive_model.version_tag
        self.adaptive_model = copy.deepcopy(self.last_stable_model)
        self.adaptive_model.version_tag = f"{self.last_stable_version_tag}-restored"
        self.adaptive_model.save(self.adaptive_model_path)

        # Update SQLite
        db.query(DBModelVersion).filter(
            DBModelVersion.model_name == "adaptive",
            DBModelVersion.status == "active"
        ).update({"status": "rolled_back"})

        mv = DBModelVersion(
            model_name="adaptive",
            version_tag=self.adaptive_model.version_tag,
            sample_count=self.adaptive_model.total_samples_trained,
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            status="active",
            description=f"Restored stable model via operator rollback from {rolled_version}.",
            metrics_json="{}"
        )
        db.add(mv)

        audit = DBAuditLog(
            action="MODEL_ROLLED_BACK",
            performed_by="Operator/API",
            details=f"Rolled back model from {rolled_version} to {self.adaptive_model.version_tag}"
        )
        db.add(audit)
        db.commit()

        logger.info(f"Adaptive model rolled back to {self.adaptive_model.version_tag}")
        return {
            "success": True,
            "message": f"Successfully rolled back from {rolled_version} to {self.adaptive_model.version_tag}.",
            "active_version": self.adaptive_model.version_tag,
            "previous_version": rolled_version
        }

# Global service instance
adaptive_service = AdaptiveLearningService()

