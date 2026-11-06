import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.core.database import init_db, SessionLocal, engine
from backend.app.models.db_models import (
    Base, DBTransaction, DBModelVersion, DBDriftEvent, DBAlert, DBAuditLog
)
from backend.app.main import app

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Initialize DB schema
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown
    Base.metadata.drop_all(bind=engine)

def test_settings_configuration():
    """Verify application configuration loads cleanly with proper types."""
    assert settings.APP_NAME == "DriftGuard AI"
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0
    assert settings.PORT == 8000

def test_db_session_and_tables_creation():
    """Verify database schema creation and basic model persistence."""
    db = SessionLocal()
    try:
        # 1. Insert a transaction
        tx = DBTransaction(
            tx_id="TX_TEST_001",
            amount=150.50,
            merchant_category="retail",
            distance_from_home=12.5,
            foreign_transaction=0,
            device_trust_score=0.95,
            velocity_1h=1,
            ip_risk_score=0.05,
            is_fraud_ground_truth=0,
            pattern_type="standard_legitimate",
            fixed_prediction=0,
            fixed_score=0.08,
            adaptive_prediction=0,
            adaptive_score=0.07,
            feedback_received=False
        )
        db.add(tx)
        
        # 2. Insert a model version
        mv = DBModelVersion(
            model_name="adaptive",
            version_tag="v1.0-test",
            accuracy=0.98,
            precision=0.95,
            recall=0.92,
            f1_score=0.935,
            fpr=0.01,
            fnr=0.08,
            sample_count=1000,
            status="active"
        )
        db.add(mv)

        # 3. Insert a drift event
        drift = DBDriftEvent(
            detector_name="AdaptiveWindowDetector",
            metric_tracked="prediction_error_rate",
            pre_drift_mean=0.02,
            post_drift_mean=0.18,
            delta_or_stat=0.16,
            window_size=200,
            severity="CRITICAL",
            action_taken="Retraining candidate initiated"
        )
        db.add(drift)

        # 4. Insert an alert
        alert = DBAlert(
            tx_id="TX_TEST_001",
            alert_type="CONCEPT_DRIFT",
            severity="WARNING",
            message="Error rate spike detected: 0.02 -> 0.18"
        )
        db.add(alert)

        # 5. Insert an audit log
        audit = DBAuditLog(
            action="MODEL_RETRAINED",
            performed_by="AdaptiveLearnerService",
            details="Retrained on 200 recent verified transactions."
        )
        db.add(audit)

        db.commit()

        # Query and verify
        saved_tx = db.query(DBTransaction).filter_by(tx_id="TX_TEST_001").first()
        assert saved_tx is not None
        assert saved_tx.amount == 150.50
        assert saved_tx.fixed_score == 0.08

        saved_mv = db.query(DBModelVersion).filter_by(version_tag="v1.0-test").first()
        assert saved_mv is not None
        assert saved_mv.f1_score == 0.935

        saved_drift = db.query(DBDriftEvent).first()
        assert saved_drift.metric_tracked == "prediction_error_rate"

        saved_alert = db.query(DBAlert).first()
        assert saved_alert.alert_type == "CONCEPT_DRIFT"

        saved_audit = db.query(DBAuditLog).first()
        assert saved_audit.action == "MODEL_RETRAINED"

    finally:
        db.close()

def test_duplicate_transaction_prevention():
    """Ensure duplicate transaction IDs violate unique constraint."""
    db = SessionLocal()
    try:
        dup_tx = DBTransaction(
            tx_id="TX_TEST_001",  # Same tx_id as previous
            amount=99.99,
            merchant_category="crypto",
            distance_from_home=500.0,
            device_trust_score=0.1,
            is_fraud_ground_truth=1
        )
        db.add(dup_tx)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()

def test_fastapi_endpoints():
    """Verify REST health check and status endpoints via TestClient."""
    with TestClient(app) as client:
        # Health check
        res_health = client.get("/api/health")
        assert res_health.status_code == 200
        health_data = res_health.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "DriftGuard AI"

        # Status check
        res_status = client.get("/api/status")
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["app_name"] == "DriftGuard AI"
        assert status_data["status"] == "operational"

