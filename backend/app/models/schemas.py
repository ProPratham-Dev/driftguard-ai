from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount in USD")
    merchant_category: str = Field(..., description="Category: retail, grocery, luxury, electronics, crypto, travel, food")
    distance_from_home: float = Field(..., ge=0, description="Distance from cardholder's home in miles")
    foreign_transaction: int = Field(0, ge=0, le=1, description="1 if international transaction, 0 if domestic")
    device_trust_score: float = Field(..., ge=0.0, le=1.0, description="Device reputation score (0.0=untrusted, 1.0=fully trusted)")
    velocity_1h: int = Field(1, ge=1, description="Number of transactions initiated in the last 1 hour")
    ip_risk_score: float = Field(0.0, ge=0.0, le=1.0, description="IP reputation score (0.0=safe, 1.0=known bot/VPN)")

class TransactionCreate(TransactionBase):
    tx_id: Optional[str] = None
    pattern_type: Optional[str] = "standard_legitimate"
    is_fraud_ground_truth: Optional[int] = Field(None, ge=0, le=1)

class TransactionResponse(TransactionBase):
    id: int
    tx_id: str
    timestamp: datetime
    pattern_type: str
    is_fraud_ground_truth: Optional[int] = None
    fixed_prediction: Optional[int] = None
    fixed_score: Optional[float] = None
    adaptive_prediction: Optional[int] = None
    adaptive_score: Optional[float] = None
    feedback_received: bool = False
    feedback_timestamp: Optional[datetime] = None
    feedback_label: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class FeedbackSubmit(BaseModel):
    tx_id: str = Field(..., description="Transaction ID to provide verified label for")
    ground_truth: int = Field(..., ge=0, le=1, description="Verified fraud status: 1=fraud, 0=legitimate")
    verifier: Optional[str] = "fraud_ops_analyst"

class SimulationControl(BaseModel):
    action: str = Field(..., description="Action: start, stop, introduce_drift, reset, switch_pattern, set_adaptive")
    fraud_pattern: Optional[str] = Field("standard", description="standard, micro_burst, geo_impossible, low_velocity_sleeper")
    adaptive_learning_enabled: Optional[bool] = None
    interval_ms: Optional[int] = Field(500, ge=100, le=5000)
    feedback_delay_ms: Optional[int] = Field(3000, ge=500, le=15000)

class ModelMetrics(BaseModel):
    model_name: str
    version_tag: str
    sample_count: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    fpr: float  # False Positive Rate
    fnr: float  # False Negative Rate
    detection_delay_avg_ms: float = 0.0
    adaptation_time_sec: float = 0.0

class ModelComparisonResponse(BaseModel):
    fixed_model: ModelMetrics
    adaptive_model: ModelMetrics
    evaluated_samples: int
    recent_window_size: int
    drift_detected: bool
    summary: str

class DriftEventResponse(BaseModel):
    id: int
    timestamp: datetime
    detector_name: str
    metric_tracked: str
    pre_drift_mean: float
    post_drift_mean: float
    delta_or_stat: float
    window_size: int
    severity: str
    action_taken: str
    details: str

    model_config = ConfigDict(from_attributes=True)

class AlertResponse(BaseModel):
    id: int
    timestamp: datetime
    tx_id: Optional[str]
    alert_type: str
    severity: str
    message: str
    details_json: str
    is_resolved: bool

    model_config = ConfigDict(from_attributes=True)

class SystemStatusResponse(BaseModel):
    app_name: str
    status: str
    simulator_active: bool
    adaptive_learning_active: bool
    active_fraud_pattern: str
    total_transactions: int
    total_feedback_received: int
    total_drift_events: int
    active_alerts_count: int
    active_adaptive_version: str

