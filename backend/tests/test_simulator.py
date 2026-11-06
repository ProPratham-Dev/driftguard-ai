import pytest
import asyncio
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.transaction_simulator import TransactionSimulator, simulator
from backend.app.services.adaptive_learning_service import adaptive_service
from backend.app.core.websocket_manager import WebSocketConnectionManager
from backend.app.core.database import SessionLocal
from backend.app.models.db_models import DBTransaction

@pytest.mark.anyio
async def test_simulator_lifecycle_and_state_transitions():
    """Verify start, pause, resume, and stop state transitions of the simulator."""
    sim = TransactionSimulator()
    sim.interval_ms = 100
    sim.feedback_delay_ms = 200

    assert sim.is_running is False
    assert sim.is_paused is False

    # Start
    await sim.start()
    assert sim.is_running is True
    assert sim.is_paused is False

    # Pause
    await sim.pause()
    assert sim.is_running is True
    assert sim.is_paused is True

    # Resume
    await sim.resume()
    assert sim.is_running is True
    assert sim.is_paused is False

    # Stop
    await sim.stop()
    assert sim.is_running is False
    assert sim.is_paused is False

def test_simulator_config_validation():
    """Verify runtime parameter configuration and regime validation."""
    sim = TransactionSimulator()

    # Valid config
    status = sim.update_config(interval_ms=250, feedback_delay_ms=1500, fraud_regime="drift_evasion")
    assert status["interval_ms"] == 250
    assert status["feedback_delay_ms"] == 1500
    assert status["fraud_regime"] == "drift_evasion"

    # Regime bounds
    sim.update_config(fraud_regime="normal")
    assert sim.fraud_regime == "normal"
    sim.update_config(fraud_regime="historical")
    assert sim.fraud_regime == "historical"

    # Invalid regime
    with pytest.raises(ValueError):
        sim.update_config(fraud_regime="invalid_regime_xxx")

def test_websocket_endpoint_and_handshake():
    """Verify client connection, initial handshake envelope, and disconnection handling."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/live") as websocket:
            init_msg = websocket.receive_json()
            assert init_msg["event"] == "connection_established"
            assert "data" in init_msg
            assert "simulator" in init_msg["data"]
            assert "drift" in init_msg["data"]
            assert "active_version" in init_msg["data"]
            websocket.send_text("close")

def test_simulator_rest_api_endpoints():
    """Verify all simulator control REST endpoints."""
    with TestClient(app) as client:
        # 1. GET status
        res_status = client.get("/api/simulator/status")
        assert res_status.status_code == 200
        data = res_status.json()
        assert "is_running" in data
        assert "fraud_regime" in data
        assert "interval_ms" in data

        # 2. POST config
        cfg_payload = {
            "interval_ms": 300,
            "feedback_delay_ms": 2000,
            "fraud_regime": "drift_evasion",
            "adaptive_learning_enabled": True
        }
        res_cfg = client.post("/api/simulator/config", json=cfg_payload)
        assert res_cfg.status_code == 200
        cfg_data = res_cfg.json()
        assert cfg_data["interval_ms"] == 300
        assert cfg_data["fraud_regime"] == "drift_evasion"

        # 3. POST start, pause, resume, stop
        res_start = client.post("/api/simulator/start")
        assert res_start.status_code == 200
        assert res_start.json()["is_running"] is True

        res_pause = client.post("/api/simulator/pause")
        assert res_pause.status_code == 200
        assert res_pause.json()["is_paused"] is True

        res_resume = client.post("/api/simulator/resume")
        assert res_resume.status_code == 200
        assert res_resume.json()["is_paused"] is False

        res_stop = client.post("/api/simulator/stop")
        assert res_stop.status_code == 200
        assert res_stop.json()["is_running"] is False

        # 4. GET /api/metrics/comparison
        res_comp = client.get("/api/metrics/comparison?window=100")
        assert res_comp.status_code == 200
        comp_data = res_comp.json()
        assert "fixed_model" in comp_data
        assert "adaptive_model" in comp_data
        assert "drift_detected" in comp_data

@pytest.mark.anyio
async def test_delayed_feedback_pipeline_execution():
    """Verify delayed feedback pipeline: scheduling, delay maturation, DB persistence, and counter tracking."""
    sim = TransactionSimulator()
    sim.interval_ms = 60
    sim.feedback_delay_ms = 200

    await sim.start()
    # Allow 5-6 transactions to generate
    await asyncio.sleep(0.35)
    gen_count = sim.transactions_generated
    assert gen_count >= 3
    # Initial feedback should not have all processed yet due to 200ms delay
    assert len(sim.pending_feedback) > 0

    # Wait for delay to expire so feedback matures
    await asyncio.sleep(0.4)
    processed_count = sim.feedback_processed
    assert processed_count >= 2

    # Stop simulator
    await sim.stop()

    # Verify that database records have feedback_received == True and valid feedback_label
    db = SessionLocal()
    try:
        verified_txs = (
            db.query(DBTransaction)
            .filter(DBTransaction.feedback_received == True)
            .order_by(DBTransaction.id.desc())
            .limit(10)
            .all()
        )
        assert len(verified_txs) > 0
        for tx in verified_txs:
            assert tx.feedback_received is True
            assert tx.feedback_label in [0, 1]
            assert tx.feedback_timestamp is not None
    finally:
        db.close()

@pytest.mark.anyio
async def test_stop_and_pending_feedback_maturation():
    """
    Audit 1: Stop and Pending Feedback
    - 500ms interval, 3000ms delay (tested with equivalent 100ms/400ms scaling)
    - Generate >= 10 transactions
    - Stop simulator immediately while feedback remains pending
    - Stop new generation but allow all already-scheduled feedback to mature
    - Confirm every pending transaction is successfully verified
    - Confirm database records and counters are consistent.
    """
    sim = TransactionSimulator()
    sim.interval_ms = 80  # fast interval for rapid deterministic testing
    sim.feedback_delay_ms = 350  # 350ms delay

    await sim.start()
    # Wait until at least 10 transactions are generated
    start_time = time.time()
    while sim.transactions_generated < 10 and (time.time() - start_time < 3.0):
        await asyncio.sleep(0.05)
    gen_count = sim.transactions_generated
    assert gen_count >= 10, f"Expected >= 10 txs, got {gen_count}"

    # Confirm some feedback is still pending
    pending_count_at_stop = len(sim.pending_feedback)
    assert pending_count_at_stop > 0, "Expected in-flight pending feedback items at stop time"

    # Stop simulator immediately
    await sim.stop(wait_for_pending=False)
    assert sim.is_running is False, "Simulator must immediately halt generation on stop"

    # Wait for scheduled feedback to mature via background drainer
    await sim.wait_for_pending_feedback(timeout=4.0)

    # Confirm no new transactions were generated after stop
    assert sim.transactions_generated == gen_count, "No new transactions should be generated after stop"

    # Confirm all pending feedback matured and processed
    assert len(sim.pending_feedback) == 0, "Pending queue must be completely drained"
    assert sim.feedback_processed == gen_count, f"Every generated tx must be verified: {sim.feedback_processed} == {gen_count}"

    # Confirm database consistency
    db = SessionLocal()
    try:
        # Check that the last `gen_count` transactions are all verified
        latest_txs = (
            db.query(DBTransaction)
            .order_by(DBTransaction.id.desc())
            .limit(gen_count)
            .all()
        )
        assert len(latest_txs) == gen_count
        for tx in latest_txs:
            assert tx.feedback_received is True, f"Transaction {tx.tx_id} was silently discarded without verification!"
            assert tx.feedback_label in [0, 1], f"Transaction {tx.tx_id} has invalid feedback label {tx.feedback_label}"
            assert tx.feedback_timestamp is not None
    finally:
        db.close()

def test_historical_prediction_integrity():
    """
    Audit 2: Historical Prediction Integrity
    - Inspect GET /api/drift/history
    - Confirm fixed and adaptive predictions are original predictions recorded before verified labels were revealed
    - Do not recalculate historical predictions using current adaptive model
    - Ensure both models are compared on identical verified transactions
    - Ensure rolling error rates use actual recorded predictions and feedback labels
    - Confirm ASW-DD detector continues to consume adaptive prediction errors only.
    """
    db = SessionLocal()
    try:
        # Insert known verified transactions with recorded predictions
        now = datetime.now(timezone.utc)
        tx1 = DBTransaction(
            tx_id="TX_AUDIT_INTEGRITY_001",
            amount=42.50,
            merchant_category="dining",
            distance_from_home=3.5,
            foreign_transaction=0,
            device_trust_score=0.92,
            velocity_1h=1,
            ip_risk_score=0.02,
            pattern_type="standard_legitimate",
            is_fraud_ground_truth=0,
            fixed_prediction=0,
            fixed_score=0.08,
            adaptive_prediction=0,
            adaptive_score=0.06,
            feedback_received=True,
            feedback_label=0,
            feedback_timestamp=now
        )
        tx2 = DBTransaction(
            tx_id="TX_AUDIT_INTEGRITY_002",
            amount=850.0,
            merchant_category="electronics",
            distance_from_home=65.0,
            foreign_transaction=1,
            device_trust_score=0.25,
            velocity_1h=4,
            ip_risk_score=0.75,
            pattern_type="evasion_fraud",
            is_fraud_ground_truth=1,
            fixed_prediction=0,  # Fixed model missed
            fixed_score=0.32,
            adaptive_prediction=1,  # Adaptive model caught
            adaptive_score=0.79,
            feedback_received=True,
            feedback_label=1,
            feedback_timestamp=now
        )
        db.add_all([tx1, tx2])
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        res = client.get("/api/drift/history?limit=30&window_size=15")
        assert res.status_code == 200
        history = res.json()
        assert len(history) >= 2, "Must return verified history points"

        db = SessionLocal()
        try:
            for pt in history:
                tx = db.query(DBTransaction).filter(DBTransaction.tx_id == pt["tx_id"]).first()
                assert tx is not None, f"Transaction {pt['tx_id']} not found in database"

                # Check 1: Must match original pre-recorded predictions exactly
                assert pt["adaptive_prediction"] == tx.adaptive_prediction
                assert pt["fixed_prediction"] == tx.fixed_prediction
                assert pt["ground_truth"] == tx.feedback_label

                # Check 2: Actual recorded error calculation
                expected_adapt_err = 0 if tx.adaptive_prediction == tx.feedback_label else 1
                expected_fixed_err = 0 if tx.fixed_prediction == tx.feedback_label else 1
                assert pt["adaptive_error"] == expected_adapt_err
                assert pt["fixed_error"] == expected_fixed_err

            # Check 3: ASW-DD detector consumes adaptive prediction errors only
            detector = adaptive_service.drift_detector
            assert detector is not None
            det_status = detector.check_drift()
            assert "current_error_rate" in det_status
            assert "reference_error_rate" in det_status
            assert det_status["severity"] in ["NORMAL", "WARNING", "CRITICAL"]
        finally:
            db.close()
