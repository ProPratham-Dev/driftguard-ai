from contextlib import asynccontextmanager
import json
import logging
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.routes import router as api_router
from backend.app.core.websocket_manager import ws_manager
from backend.app.services.transaction_simulator import simulator
from backend.app.services.adaptive_learning_service import adaptive_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("driftguard.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initialize SQLite DB tables and startup tasks."""
    logger.info("Initializing DriftGuard AI database and core systems...")
    init_db()
    logger.info("DriftGuard AI database initialized successfully.")
    yield
    logger.info("DriftGuard AI shutting down. Stopping simulator...")
    if simulator.is_running:
        await simulator.stop()
    logger.info("Shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="DriftGuard AI: Adaptive Real-Time Fraud Detection with Concept Drift Detection & Online Machine Learning",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(api_router, prefix="/api")

# WebSocket Live Telemetry Endpoint
@app.websocket("/ws/live")
async def websocket_live_telemetry(websocket: WebSocket):
    """
    Real-time streaming telemetry WebSocket endpoint.
    Broadcasts live transactions, delayed verified feedback, drift alerts,
    and model version updates to dashboard clients.
    """
    await ws_manager.connect(websocket)
    try:
        # Deliver initial state envelope upon handshake (json.dumps with default=str for datetime safety)
        init_envelope = {
            "event": "connection_established",
            "data": {
                "simulator": simulator.get_status(),
                "drift": adaptive_service.drift_detector.check_drift(),
                "active_version": adaptive_service.adaptive_model.version_tag if adaptive_service.adaptive_model else "unknown"
            }
        }
        await websocket.send_text(json.dumps(init_envelope, default=str))

        while True:
            try:
                data = await websocket.receive_text()
                if data in ("close", "exit"):
                    break
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
    finally:
        await ws_manager.disconnect(websocket)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Reliability safeguard: catch unhandled exceptions and format secure JSON responses."""
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. DriftGuard AI security team logged this event."}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

