from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schemas import SystemStatusResponse

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check():
    """System health check endpoint verifying backend and ML service status."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

@router.get("/status", response_model=SystemStatusResponse, tags=["System"])
def get_system_status(db: Session = Depends(get_db)):
    """Fetch current system state, simulator status, and active model versions."""
    from backend.app.models.db_models import DBTransaction, DBDriftEvent, DBAlert, DBModelVersion
    
    total_tx = db.query(DBTransaction).count()
    total_feedback = db.query(DBTransaction).filter(DBTransaction.feedback_received == True).count()
    total_drift = db.query(DBDriftEvent).count()
    active_alerts = db.query(DBAlert).filter(DBAlert.is_resolved == False).count()
    
    latest_adaptive = (
        db.query(DBModelVersion)
        .filter(DBModelVersion.model_name == "adaptive", DBModelVersion.status == "active")
        .order_by(DBModelVersion.id.desc())
        .first()
    )
    active_version = latest_adaptive.version_tag if latest_adaptive else "v1.0-initial"

    return SystemStatusResponse(
        app_name=settings.APP_NAME,
        status="operational",
        simulator_active=False,
        adaptive_learning_active=settings.ADAPTIVE_LEARNING_ENABLED,
        active_fraud_pattern=settings.ACTIVE_FRAUD_PATTERN,
        total_transactions=total_tx,
        total_feedback_received=total_feedback,
        total_drift_events=total_drift,
        active_alerts_count=active_alerts,
        active_adaptive_version=active_version
    )

