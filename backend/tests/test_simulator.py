import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.transaction_simulator import TransactionSimulator, simulator
from backend.app.core.websocket_manager import WebSocketConnectionManager

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
