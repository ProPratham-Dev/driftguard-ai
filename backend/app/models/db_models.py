from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DBTransaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_id = Column(String(64), unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Transaction Features
    amount = Column(Float, nullable=False)
    merchant_category = Column(String(50), nullable=False)
    distance_from_home = Column(Float, nullable=False)
    foreign_transaction = Column(Integer, default=0)
    device_trust_score = Column(Float, nullable=False)
    velocity_1h = Column(Integer, default=1)
    ip_risk_score = Column(Float, default=0.0)
    
    # Pattern label assigned during generation (for simulation ground truth)
    pattern_type = Column(String(50), default="standard_legitimate")
    is_fraud_ground_truth = Column(Integer, nullable=False)
    
    # Model Predictions (recorded at transaction time)
    fixed_prediction = Column(Integer, nullable=True)
    fixed_score = Column(Float, nullable=True)
    adaptive_prediction = Column(Integer, nullable=True)
    adaptive_score = Column(Float, nullable=True)
    
    # Feedback tracking (arrives delayed, never before prediction)
    feedback_received = Column(Boolean, default=False, index=True)
    feedback_timestamp = Column(DateTime, nullable=True)
    feedback_label = Column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_tx_timestamp", "timestamp"),
        Index("idx_tx_feedback", "feedback_received"),
    )


class DBModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(50), nullable=False)  # "fixed" or "adaptive"
    version_tag = Column(String(30), nullable=False, unique=True)
    trained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sample_count = Column(Integer, default=0)
    
    # Metrics
    accuracy = Column(Float, default=0.0)
    precision = Column(Float, default=0.0)
    recall = Column(Float, default=0.0)
    f1_score = Column(Float, default=0.0)
    fpr = Column(Float, default=0.0)
    fnr = Column(Float, default=0.0)
    
    status = Column(String(20), default="active")  # active, candidate, superseded, rolled_back
    description = Column(String(255), default="")
    metrics_json = Column(Text, default="{}")


class DBDriftEvent(Base):
    __tablename__ = "drift_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    detector_name = Column(String(50), nullable=False)
    metric_tracked = Column(String(50), nullable=False)
    pre_drift_mean = Column(Float, nullable=False)
    post_drift_mean = Column(Float, nullable=False)
    delta_or_stat = Column(Float, nullable=False)
    window_size = Column(Integer, default=0)
    severity = Column(String(20), default="WARNING")
    action_taken = Column(String(100), default="Retraining triggered")
    details = Column(Text, default="")


class DBAlert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    tx_id = Column(String(64), nullable=True)
    alert_type = Column(String(50), nullable=False)  # FRAUD_DETECTED, CONCEPT_DRIFT, MODEL_DEGRADATION, SYSTEM
    severity = Column(String(20), default="WARNING")  # INFO, WARNING, CRITICAL
    message = Column(String(255), nullable=False)
    details_json = Column(Text, default="{}")
    is_resolved = Column(Boolean, default=False)


class DBAuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    action = Column(String(100), nullable=False)
    performed_by = Column(String(50), default="system")
    details = Column(Text, default="")

