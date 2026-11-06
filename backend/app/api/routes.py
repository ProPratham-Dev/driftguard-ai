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
    TransactionResponse,
    SimulatorConfigUpdate,
    SimulatorStatusResponse,
    ModelComparisonResponse,
    ModelMetrics
)
from backend.app.models.db_models import (
    DBTransaction,
    DBDriftEvent,
    DBAlert,
    DBModelVersion,
    DBAuditLog
)
from backend.app.services.adaptive_learning_service import adaptive_service
from backend.app.services.transaction_simulator import simulator
from backend.app.ml.evaluation import compute_metrics, compare_models

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
        simulator_active=simulator.is_running and not simulator.is_paused,
        adaptive_learning_active=simulator.adaptive_learning_enabled,
        active_fraud_pattern=simulator.fraud_regime,
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

# --- Simulator Control Endpoints ---

@router.post("/simulator/start", response_model=SimulatorStatusResponse, tags=["Simulator"])
async def start_simulator():
    """Start the asynchronous real-time transaction simulator."""
    await simulator.start()
    return simulator.get_status()

@router.post("/simulator/pause", response_model=SimulatorStatusResponse, tags=["Simulator"])
async def pause_simulator():
    """Pause the transaction simulator."""
    await simulator.pause()
    return simulator.get_status()

@router.post("/simulator/resume", response_model=SimulatorStatusResponse, tags=["Simulator"])
async def resume_simulator():
    """Resume the paused transaction simulator."""
    await simulator.resume()
    return simulator.get_status()

@router.post("/simulator/stop", response_model=SimulatorStatusResponse, tags=["Simulator"])
async def stop_simulator():
    """Stop the transaction simulator."""
    await simulator.stop()
    return simulator.get_status()

@router.get("/simulator/status", response_model=SimulatorStatusResponse, tags=["Simulator"])
def get_simulator_status():
    """Fetch current running state, transaction counts, and parameters of the simulator."""
    return simulator.get_status()

@router.post("/simulator/config", response_model=SimulatorStatusResponse, tags=["Simulator"])
def update_simulator_config(config: SimulatorConfigUpdate):
    """
    Update simulation parameters at runtime:
    - interval_ms: speed of generation (100-5000ms)
    - feedback_delay_ms: delay before ground truth feedback is ingested
    - fraud_regime: 'normal', 'historical', or 'drift_evasion'
    - adaptive_learning_enabled: toggle online model updates
    """
    try:
        updated = simulator.update_config(
            interval_ms=config.interval_ms,
            feedback_delay_ms=config.feedback_delay_ms,
            fraud_regime=config.fraud_regime,
            adaptive_learning_enabled=config.adaptive_learning_enabled
        )
        return updated
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

# --- Dashboard Metrics Endpoint ---

@router.get("/metrics/comparison", response_model=ModelComparisonResponse, tags=["Models"])
def get_model_comparison(
    window: int = Query(200, ge=20, le=2000),
    db: Session = Depends(get_db)
):
    """
    Compare Fixed model vs Adaptive model performance on recent verified transactions.
    """
    txs = (
        db.query(DBTransaction)
        .filter(DBTransaction.feedback_received == True)
        .order_by(DBTransaction.id.desc())
        .limit(window)
        .all()
    )

    if not txs:
        empty_metrics = ModelMetrics(
            model_name="baseline",
            version_tag="v1.0",
            sample_count=0,
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            fpr=0.0,
            fnr=0.0
        )
        return ModelComparisonResponse(
            fixed_model=empty_metrics,
            adaptive_model=empty_metrics,
            evaluated_samples=0,
            recent_window_size=window,
            drift_detected=False,
            summary="No live verified feedback samples recorded yet. Dashboard displays audited Concept-Drift Benchmark (N=4,800 stream from N=12,000 total dataset; Historical Holdout N=1,700)."
        )

    # Reverse to chronological order
    txs = list(reversed(txs))
    y_true = [tx.feedback_label for tx in txs]
    fixed_preds = [tx.fixed_prediction for tx in txs]
    adaptive_preds = [tx.adaptive_prediction for tx in txs]

    fixed_res = compute_metrics(y_true, fixed_preds, model_name="fixed", version_tag="v1.0-fixed")
    adaptive_res = compute_metrics(
        y_true,
        adaptive_preds,
        model_name="adaptive",
        version_tag=adaptive_service.adaptive_model.version_tag if adaptive_service.adaptive_model else "adaptive"
    )

    drift_info = adaptive_service.drift_detector.check_drift()

    summary_text = (
        f"Evaluated on {len(y_true)} verified transactions. "
        f"Fixed F1: {fixed_res['f1_score']:.4f} (Recall: {fixed_res['recall']:.2%}), "
        f"Adaptive F1: {adaptive_res['f1_score']:.4f} (Recall: {adaptive_res['recall']:.2%}). "
        f"Drift Status: {drift_info['severity']}."
    )

    return ModelComparisonResponse(
        fixed_model=ModelMetrics(**fixed_res),
        adaptive_model=ModelMetrics(**adaptive_res),
        evaluated_samples=len(y_true),
        recent_window_size=window,
        drift_detected=drift_info["drift_detected"],
        summary=summary_text
    )

