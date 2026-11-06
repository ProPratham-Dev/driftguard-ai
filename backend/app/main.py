from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.routes import router as api_router

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
    logger.info("DriftGuard AI shutting down.")

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
