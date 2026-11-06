import asyncio
import time
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from collections import deque

from backend.app.ml.dataset_generator import SyntheticDatasetGenerator
from backend.app.services.adaptive_learning_service import adaptive_service
from backend.app.core.database import SessionLocal
from backend.app.core.websocket_manager import ws_manager

logger = logging.getLogger("driftguard.simulator")

class TransactionSimulator:
    """
    Asynchronous Real-Time Transaction Simulator.
    Generates time-ordered continuous financial transactions using SyntheticDatasetGenerator,
    records predictions before label revelation, queues realistic delayed feedback,
    and broadcasts events over WebSockets.
    """

    def __init__(self):
        self.generator = SyntheticDatasetGenerator(seed=int(time.time()))
        self.is_running: bool = False
        self.is_paused: bool = False
        self._task: Optional[asyncio.Task] = None

        # Configuration
        self.interval_ms: int = 500  # speed between transactions
        self.feedback_delay_ms: int = 3000  # delay before verified feedback arrives
        self.fraud_regime: str = "normal"  # "normal", "historical", "drift_evasion"
        self.adaptive_learning_enabled: bool = True

        # Statistics
        self.transactions_generated: int = 0
        self.feedback_processed: int = 0
        self.fraud_count_simulated: int = 0
        self.fraud_detected_fixed: int = 0
        self.fraud_detected_adaptive: int = 0
        self.fraud_missed_fixed: int = 0
        self.fraud_missed_adaptive: int = 0

        # Queue for delayed feedback: deque of (due_time_sec, tx_id, ground_truth)
        self.pending_feedback: deque = deque()
        self.processed_tx_ids: set = set()

    async def start(self):
        """Start the background simulator task if not running."""
        if self.is_running:
            if self.is_paused:
                self.is_paused = False
                logger.info("Simulator resumed from pause.")
                await ws_manager.broadcast("simulator_status", self.get_status())
            return

        self.is_running = True
        self.is_paused = False
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Transaction simulator started.")
        await ws_manager.broadcast("simulator_status", self.get_status())

    async def pause(self):
        """Pause transaction emission while preserving state."""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info("Transaction simulator paused.")
            await ws_manager.broadcast("simulator_status", self.get_status())

    async def resume(self):
        """Resume paused simulation."""
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info("Transaction simulator resumed.")
            await ws_manager.broadcast("simulator_status", self.get_status())

    async def stop(self):
        """Stop simulator and cancel background task."""
        self.is_running = False
        self.is_paused = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Transaction simulator stopped.")
        await ws_manager.broadcast("simulator_status", self.get_status())

    def update_config(
        self,
        interval_ms: Optional[int] = None,
        feedback_delay_ms: Optional[int] = None,
        fraud_regime: Optional[str] = None,
        adaptive_learning_enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update simulator operational parameters."""
        if interval_ms is not None:
            self.interval_ms = max(50, min(10000, interval_ms))
        if feedback_delay_ms is not None:
            self.feedback_delay_ms = max(200, min(30000, feedback_delay_ms))
        if fraud_regime is not None:
            if fraud_regime in ["normal", "historical", "drift_evasion"]:
                self.fraud_regime = fraud_regime
            else:
                raise ValueError(f"Unknown fraud regime: {fraud_regime}")
        if adaptive_learning_enabled is not None:
            self.adaptive_learning_enabled = adaptive_learning_enabled

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """Return live simulator status and counters."""
        can_rollback = False
        if adaptive_service.adaptive_model and adaptive_service.last_stable_model:
            if adaptive_service.last_stable_version_tag != adaptive_service.adaptive_model.version_tag:
                can_rollback = True

        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "fraud_regime": self.fraud_regime,
            "interval_ms": self.interval_ms,
            "feedback_delay_ms": self.feedback_delay_ms,
            "adaptive_learning_enabled": self.adaptive_learning_enabled,
            "transactions_generated": self.transactions_generated,
            "feedback_processed": self.feedback_processed,
            "pending_feedback_count": len(self.pending_feedback),
            "fraud_count_simulated": self.fraud_count_simulated,
            "fraud_detected_fixed": self.fraud_detected_fixed,
            "fraud_detected_adaptive": self.fraud_detected_adaptive,
            "fraud_missed_fixed": self.fraud_missed_fixed,
            "fraud_missed_adaptive": self.fraud_missed_adaptive,
            "active_adaptive_version": adaptive_service.adaptive_model.version_tag if adaptive_service.adaptive_model else "unknown",
            "can_rollback": can_rollback
        }

    async def _run_loop(self):
        """Continuous simulation loop."""
        cust_id_pool = [f"CUST_{i:04d}" for i in range(1, 201)]

        while self.is_running:
            if self.is_paused:
                await asyncio.sleep(0.2)
                continue

            try:
                db = SessionLocal()
                try:
                    now = datetime.now(timezone.utc)
                    cust_id = self.generator.rng.choice(cust_id_pool)

                    # 1. Generate Transaction based on current regime
                    if self.fraud_regime == "normal":
                        tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)
                    elif self.fraud_regime == "historical":
                        is_fraud = self.generator.rng.random() < 0.12
                        if is_fraud:
                            tx_dict = self.generator.generate_historical_fraud_transaction(cust_id, now)
                        else:
                            tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)
                    elif self.fraud_regime == "drift_evasion":
                        is_fraud = self.generator.rng.random() < 0.18
                        if is_fraud:
                            tx_dict = self.generator.generate_drift_fraud_transaction(cust_id, now)
                        else:
                            tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)
                    else:
                        tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)

                    tx_id = f"TX_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6].upper()}"
                    tx_dict["tx_id"] = tx_id
                    ground_truth = tx_dict["is_fraud"]

                    # 2. Score with ML Models (NO ground truth passed to model weights)
                    pred_res = adaptive_service.predict_transaction(tx_dict, db)
                    self.transactions_generated += 1

                    fixed_pred = pred_res["fixed_prediction"]
                    adaptive_pred = pred_res["adaptive_prediction"]

                    if ground_truth == 1:
                        self.fraud_count_simulated += 1
                        if fixed_pred == 1:
                            self.fraud_detected_fixed += 1
                        else:
                            self.fraud_missed_fixed += 1

                        if adaptive_pred == 1:
                            self.fraud_detected_adaptive += 1
                        else:
                            self.fraud_missed_adaptive += 1

                    # 3. Schedule Delayed Feedback (feedback arrives after configured delay)
                    due_timestamp = time.time() + (self.feedback_delay_ms / 1000.0)
                    self.pending_feedback.append((due_timestamp, tx_id, ground_truth))

                    # 4. Broadcast new transaction event over WebSocket (Ground-truth is HIDDEN!)
                    public_tx_event = {
                        "tx_id": pred_res["tx_id"],
                        "timestamp": pred_res["timestamp"].isoformat() if hasattr(pred_res["timestamp"], "isoformat") else str(pred_res["timestamp"]),
                        "amount": pred_res["amount"],
                        "merchant_category": pred_res["merchant_category"],
                        "distance_from_home": pred_res["distance_from_home"],
                        "foreign_transaction": pred_res["foreign_transaction"],
                        "velocity_1h": pred_res["velocity_1h"],
                        "device_trust_score": pred_res["device_trust_score"],
                        "fixed_prediction": fixed_pred,
                        "fixed_score": pred_res["fixed_score"],
                        "adaptive_prediction": adaptive_pred,
                        "adaptive_score": pred_res["adaptive_score"],
                        "adaptive_version": pred_res["adaptive_version"],
                        "feedback_status": "pending"
                        # Ground truth is intentionally NOT included
                    }
                    await ws_manager.broadcast("new_transaction", public_tx_event)

                    # 5. Process any mature feedback items whose delay expired
                    current_time = time.time()
                    while self.pending_feedback and self.pending_feedback[0][0] <= current_time:
                        _, mature_tx_id, mature_label = self.pending_feedback.popleft()
                        if mature_tx_id in self.processed_tx_ids:
                            continue
                        self.processed_tx_ids.add(mature_tx_id)

                        fb_res = adaptive_service.process_verified_feedback(
                            mature_tx_id,
                            mature_label,
                            db
                        )
                        self.feedback_processed += 1

                        mature_tx = db.query(DBTransaction).filter(DBTransaction.tx_id == mature_tx_id).first()
                        fixed_pred = mature_tx.fixed_prediction if mature_tx else 0
                        adaptive_err = 0 if fb_res["prediction"] == mature_label else 1
                        fixed_err = 0 if fixed_pred == mature_label else 1

                        # Broadcast verified feedback event (ground truth now revealed!)
                        await ws_manager.broadcast("verified_feedback", {
                            "tx_id": mature_tx_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "ground_truth": mature_label,
                            "adaptive_prediction": fb_res["prediction"],
                            "fixed_prediction": fixed_pred,
                            "adaptive_error": adaptive_err,
                            "fixed_error": fixed_err,
                            "prediction": fb_res["prediction"],
                            "prediction_correct": fb_res["prediction_correct"],
                            "drift_status": fb_res["drift_status"],
                            "learning_action": fb_res["learning_action_triggered"]
                        })

                        # If drift event detected, broadcast drift alert
                        if fb_res["drift_status"]["drift_detected"]:
                            await ws_manager.broadcast("drift_alert", fb_res["drift_status"])

                        # If model action occurred, broadcast model update
                        if fb_res["learning_action_triggered"] in ["promoted", "rejected"]:
                            await ws_manager.broadcast("model_update", {
                                "action": fb_res["learning_action_triggered"],
                                "active_version": adaptive_service.adaptive_model.version_tag
                            })

                except Exception as inner_e:
                    db.rollback()
                    raise inner_e
                finally:
                    db.close()

            except Exception as e:
                logger.error(f"Simulator error in loop: {e}", exc_info=True)

            await asyncio.sleep(self.interval_ms / 1000.0)

# Global simulator instance
simulator = TransactionSimulator()
