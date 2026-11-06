import pytest
from datetime import datetime, timezone
import numpy as np
from fastapi.testclient import TestClient

from backend.app.ml.drift_detector import AdaptiveSlidingWindowDriftDetector
from backend.app.services.adaptive_learning_service import AdaptiveLearningService, adaptive_service
from backend.app.core.database import SessionLocal, init_db, engine
from backend.app.models.db_models import (
    Base, DBTransaction, DBDriftEvent, DBAlert, DBAuditLog, DBModelVersion
)
from backend.app.main import app

def test_drift_detector_normal_traffic_no_false_alarm():
    """Verify that steady, low-error normal traffic produces NORMAL severity and no drift alarm."""
    detector = AdaptiveSlidingWindowDriftDetector(
        recent_window_size=50,
        reference_window_size=200,
        min_samples_to_detect=30,
        warning_delta=0.06,
        critical_delta=0.12
    )

    # Stream 150 low-error observations (~2% error rate)
    for i in range(150):
        is_error = 1 if i % 50 == 0 else 0
        status = detector.add_element(is_error)

    assert status["drift_detected"] is False
    assert status["severity"] == "NORMAL"
    assert status["drift_score"] < 0.3
    assert status["current_error_rate"] <= 0.04

def test_drift_detector_single_isolated_error_resilience():
    """Verify that a single isolated spike in error does not immediately trigger CRITICAL drift."""
    detector = AdaptiveSlidingWindowDriftDetector(
        recent_window_size=50,
        reference_window_size=200,
        min_samples_to_detect=30,
        warning_delta=0.06,
        critical_delta=0.12
    )

    # Establish baseline with 100 accurate observations
    for _ in range(100):
        detector.add_element(0)

    # Single misclassification occurs
    status = detector.add_element(1)

    assert status["drift_detected"] is False
    assert status["severity"] == "NORMAL"
    assert status["current_error_rate"] < 0.05

def test_drift_detector_sustained_error_triggers_drift():
    """Verify that sustained high error rate triggers WARNING then CRITICAL concept drift."""
    detector = AdaptiveSlidingWindowDriftDetector(
        recent_window_size=40,
        reference_window_size=160,
        min_samples_to_detect=25,
        warning_delta=0.06,
        critical_delta=0.12
    )

    # Baseline: 120 observations with low error (~1.5%)
    for i in range(120):
        detector.add_element(1 if i % 70 == 0 else 0)

    base_status = detector.check_drift()
    assert base_status["severity"] == "NORMAL"
    ref_error = base_status["reference_error_rate"]

    # Onset of concept drift: sustained 35% error rate
    severities = []
    for _ in range(45):
        # 35% error
        err = 1 if np.random.random() < 0.35 else 0
        res = detector.add_element(err)
        severities.append(res["severity"])

    assert "CRITICAL" in severities or "WARNING" in severities
    final_status = detector.check_drift()
    assert final_status["drift_detected"] is True
    assert final_status["current_error_rate"] > ref_error

def test_delayed_feedback_sequencing_and_database_persistence():
    """
    Test exact operational sequence:
    1. Transaction arrives and predictions are recorded with NO ground truth exposure.
    2. Feedback arrives delayed, updates transaction record.
    3. Prediction error is evaluated and logged.
    """
    db = SessionLocal()
    service = AdaptiveLearningService()
    try:
        tx_payload = {
            "tx_id": "TX_SEQ_TEST_001",
            "amount": 28.50,
            "merchant_category": "dining",
            "distance_from_prev": 2.1,
            "foreign_transaction": 0,
            "device_trust_score": 0.88,
            "velocity_1h": 8,
            "ip_risk_score": 0.15,
            "tx_hour": 3,
            "new_device": 0,
            "pattern_type": "drift_micro_velocity_burst",
            "is_fraud_ground_truth": 1  # Ground truth is stored in DB for verification, but NOT given to model.predict
        }

        # Step 1: Predict
        pred_res = service.predict_transaction(tx_payload, db)
        assert pred_res["tx_id"] == "TX_SEQ_TEST_001"
        assert pred_res["fixed_prediction"] in (0, 1)
        assert pred_res["adaptive_prediction"] in (0, 1)

        saved_tx = db.query(DBTransaction).filter_by(tx_id="TX_SEQ_TEST_001").first()
        assert saved_tx.feedback_received is False
        assert saved_tx.feedback_label is None

        # Step 2: Delayed feedback arrives
        fb_res = service.process_verified_feedback("TX_SEQ_TEST_001", ground_truth=1, db=db)
        assert fb_res["feedback_recorded"] is True
        assert fb_res["ground_truth"] == 1

        db.refresh(saved_tx)
        assert saved_tx.feedback_received is True
        assert saved_tx.feedback_label == 1
        assert saved_tx.feedback_timestamp is not None
    finally:
        db.close()

def test_candidate_model_validation_and_promotion():
    """Verify candidate model validation against holdout data, promotion, and database versioning."""
    db = SessionLocal()
    service = AdaptiveLearningService()
    try:
        # Seed 50 verified transactions into the DB
        for i in range(50):
            is_fraud = 1 if i % 5 == 0 else 0
            tx = DBTransaction(
                tx_id=f"TX_VAL_TEST_{i:04d}",
                amount=25.0 if is_fraud else 50.0,
                merchant_category="dining" if is_fraud else "grocery",
                distance_from_home=3.0,
                foreign_transaction=0,
                device_trust_score=0.85,
                velocity_1h=9 if is_fraud else 1,
                ip_risk_score=0.15,
                pattern_type="test",
                is_fraud_ground_truth=is_fraud,
                fixed_prediction=0,
                fixed_score=0.1,
                adaptive_prediction=is_fraud,
                adaptive_score=0.8 if is_fraud else 0.1,
                feedback_received=True,
                feedback_label=is_fraud,
                feedback_timestamp=datetime.now(timezone.utc)
            )
            db.add(tx)
        db.commit()

        initial_version = service.adaptive_model.version_tag
        res = service.train_and_validate_candidate(db)

        assert res["action"] in ("promoted", "rejected")
        if res["action"] == "promoted":
            assert res["promoted_version"] != initial_version
            assert service.adaptive_model.version_tag == res["promoted_version"]

            # Verify DB version entry
            db_version = db.query(DBModelVersion).filter_by(version_tag=res["promoted_version"]).first()
            assert db_version is not None
            assert db_version.status == "active"
    finally:
        db.close()

def test_model_rollback():
    """Verify operator rollback restores previous model weights and registers rollback in database."""
    db = SessionLocal()
    service = AdaptiveLearningService()
    try:
        # Simulate an active version promotion
        service.last_stable_model = service.adaptive_model
        service.last_stable_version_tag = "v1.0-stable-test"

        res = service.rollback(db)
        assert res["success"] is True
        assert "restored" in res["active_version"]

        # Check audit log
        audit = db.query(DBAuditLog).filter_by(action="MODEL_ROLLED_BACK").order_by(DBAuditLog.id.desc()).first()
        assert audit is not None
        assert "restored" in audit.details
    finally:
        db.close()

def test_fastapi_endpoints():
    """Verify REST API endpoints for drift status, drift events, model versions, feedback, and rollback."""
    # Seed a model version for testing GET endpoint
    db = SessionLocal()
    try:
        db.add(DBModelVersion(
            model_name="adaptive",
            version_tag="v1.0-api-test",
            status="active",
            accuracy=0.99,
            precision=1.0,
            recall=0.98,
            f1_score=0.99,
            description="Initial test version"
        ))
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        # 1. GET /api/drift/status
        res = client.get("/api/drift/status")
        assert res.status_code == 200
        data = res.json()
        assert "drift_detected" in data
        assert "severity" in data
        assert data["severity"] in ["NORMAL", "WARNING", "CRITICAL"]

        # 2. GET /api/drift/events
        res = client.get("/api/drift/events")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

        # 3. GET /api/models/versions
        res = client.get("/api/models/versions")
        assert res.status_code == 200
        versions = res.json()
        assert isinstance(versions, list)
        assert len(versions) > 0
        assert versions[0]["version_tag"] == "v1.0-api-test"

        # 4. POST /api/transactions/predict
        tx_req = {
            "tx_id": "TX_API_TEST_001",
            "amount": 42.0,
            "merchant_category": "retail",
            "distance_from_home": 4.5,
            "foreign_transaction": 0,
            "device_trust_score": 0.92,
            "velocity_1h": 2,
            "ip_risk_score": 0.05,
            "is_fraud_ground_truth": 0
        }
        res_pred = client.post("/api/transactions/predict", json=tx_req)
        assert res_pred.status_code == 200
        pred_data = res_pred.json()
        assert pred_data["tx_id"] == "TX_API_TEST_001"
        assert "adaptive_prediction" in pred_data
        assert "fixed_prediction" in pred_data

        # 5. POST /api/learning/feedback (valid)
        fb_req = {
            "tx_id": "TX_API_TEST_001",
            "ground_truth": 0,
            "verifier": "qa_analyst"
        }
        res_fb = client.post("/api/learning/feedback", json=fb_req)
        assert res_fb.status_code == 200
        fb_data = res_fb.json()
        assert fb_data["tx_id"] == "TX_API_TEST_001"
        assert fb_data["feedback_recorded"] is True
        assert fb_data["prediction_correct"] is True

        # 6. POST /api/learning/feedback (404 on nonexistent tx_id)
        res_404 = client.post("/api/learning/feedback", json={"tx_id": "NON_EXISTENT_TX", "ground_truth": 1})
        assert res_404.status_code == 404

        # 7. POST /api/learning/rollback
        res_rb = client.post("/api/learning/rollback")
        assert res_rb.status_code == 200
        rb_data = res_rb.json()
        assert "success" in rb_data
