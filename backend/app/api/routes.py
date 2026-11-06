from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.schemas import (
    SystemStatusResponse,
    DriftStatusResponse,
    DriftEventResponse,
    ModelVersionResponse,
    FeedbackSubmit,
    FeedbackResponse,
    RollbackResponse,
    TransactionCreate,
    TransactionResponse
)
from backend.app.models.db_models import (
    DBTransaction,
    DBDriftEvent,
    DBAlert,
    DBModelVersion,
    DBAuditLog
)
from backend.app.services.adaptive_learning_service import adaptive_service

router = APIRouter()

# --- System Endpoints ---

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
    active_version = latest_adaptive.version_tag if latest_adaptive else adaptive_service.adaptive_model.version_tag

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

# --- Transactions & Inference Endpoints ---

@router.post("/transactions/predict", response_model=TransactionResponse, tags=["Transactions"])
def predict_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    """
    Score incoming transaction without exposing ground truth to model weights.
    Records predictions for both fixed and adaptive models.
    """
    try:
        result = adaptive_service.predict_transaction(tx.model_dump(), db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failure: {str(e)}"
        )

# --- Concept Drift Endpoints ---

@router.get("/drift/status", response_model=DriftStatusResponse, tags=["Concept Drift"])
def get_drift_status():
    """
    Get current concept drift detector status, error rates across sliding windows,
    and severity classification (NORMAL, WARNING, CRITICAL).
    """
    status_info = adaptive_service.drift_detector.check_drift()
    return DriftStatusResponse(**status_info)

@router.get("/drift/events", response_model=List[DriftEventResponse], tags=["Concept Drift"])
def get_drift_events(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Fetch chronological list of detected concept drift events."""
    events = (
        db.query(DBDriftEvent)
        .order_by(DBDriftEvent.id.desc())
        .limit(limit)
        .all()
    )
    return events

# --- Model Versions & History Endpoints ---

@router.get("/models/versions", response_model=List[ModelVersionResponse], tags=["Models"])
def get_model_versions(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Fetch complete model version history with benchmark metrics and active status."""
    versions = (
        db.query(DBModelVersion)
        .order_by(DBModelVersion.id.desc())
        .limit(limit)
        .all()
    )
    return versions

# --- Adaptive Learning & Feedback Endpoints ---

@router.post("/learning/feedback", response_model=FeedbackResponse, tags=["Adaptive Learning"])
def submit_verified_feedback(feedback: FeedbackSubmit, db: Session = Depends(get_db)):
    """
    Submit verified feedback for a previously scored transaction.
    Compares prediction with verified ground truth, feeds error signal to drift detector,
    and initiates candidate model training if retraining conditions are satisfied.
    """
    try:
        res = adaptive_service.process_verified_feedback(
            tx_id=feedback.tx_id,
            ground_truth=feedback.ground_truth,
            db=db
        )
        return FeedbackResponse(
            tx_id=res["tx_id"],
            feedback_recorded=res["feedback_recorded"],
            prediction=res["prediction"],
            ground_truth=res["ground_truth"],
            prediction_correct=res["prediction_correct"],
            drift_status=DriftStatusResponse(**res["drift_status"]),
            learning_action_triggered=res["learning_action_triggered"]
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback processing error: {str(e)}"
        )

@router.post("/learning/rollback", response_model=RollbackResponse, tags=["Adaptive Learning"])
def rollback_model(db: Session = Depends(get_db)):
    """
    Rollback active adaptive model to previous stable version.
    Restores stable parameters and updates version audit log.
    """
    try:
        res = adaptive_service.rollback(db)
        return RollbackResponse(**res)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback error: {str(e)}"
        )
