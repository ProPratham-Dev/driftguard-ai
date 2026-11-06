import math
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import numpy as np
from scipy import stats

class AdaptiveSlidingWindowDriftDetector:
    """
    Adaptive Sliding-Window Statistical Drift Detector (ASW-DD).
    
    Monitors streaming binary prediction errors (0 = correct, 1 = misclassification)
    from verified feedback. Partitions the streaming error buffer into a stable reference
    window (W_ref) and an adaptive recent window (W_recent). Evaluates statistical significance
    via two-sample proportion Z-test and absolute error rate difference to reliably detect
    concept drift while remaining robust against isolated, transient errors.
    """

    def __init__(
        self,
        recent_window_size: int = 80,
        reference_window_size: int = 400,
        min_samples_to_detect: int = 30,
        warning_delta: float = 0.06,
        critical_delta: float = 0.12,
        warning_z: float = 2.0,
        critical_z: float = 3.0
    ):
        self.recent_window_size = recent_window_size
        self.reference_window_size = reference_window_size
        self.min_samples_to_detect = min_samples_to_detect
        self.warning_delta = warning_delta
        self.critical_delta = critical_delta
        self.warning_z = warning_z
        self.critical_z = critical_z

        # Max buffer size holds reference + recent samples
        self.max_buffer_size = reference_window_size + recent_window_size
        self.error_buffer = deque(maxlen=self.max_buffer_size)
        self.total_feedback_observed: int = 0
        self.drift_count: int = 0
        self.last_drift_timestamp: Optional[datetime] = None

    def add_element(self, is_error: int) -> Dict[str, Any]:
        """
        Record a verified prediction error signal (0 = correct prediction, 1 = misclassification).
        Returns the instantaneous drift status.
        """
        self.error_buffer.append(int(is_error))
        self.total_feedback_observed += 1
        return self.check_drift()

    def check_drift(self) -> Dict[str, Any]:
        """
        Evaluate error rates across reference and recent sliding windows.
        Returns detailed drift diagnostic information.
        """
        n_total = len(self.error_buffer)
        now = datetime.now(timezone.utc)

        # Baseline case: insufficient data to make statistical claim
        if n_total < self.min_samples_to_detect:
            curr_rate = float(np.mean(self.error_buffer)) if n_total > 0 else 0.0
            return {
                "drift_detected": False,
                "severity": "NORMAL",
                "drift_score": 0.0,
                "current_error_rate": round(curr_rate, 4),
                "reference_error_rate": round(curr_rate, 4),
                "recent_samples_count": n_total,
                "reference_samples_count": 0,
                "p_value": 1.0,
                "z_score": 0.0,
                "detection_timestamp": now,
                "status_message": f"Warm-up: collecting verified feedback ({n_total}/{self.min_samples_to_detect} samples)."
            }

        # Divide buffer into recent and reference sub-windows
        n_recent = min(self.recent_window_size, max(self.min_samples_to_detect, n_total // 3))
        n_ref = n_total - n_recent

        buffer_list = list(self.error_buffer)
        recent_samples = buffer_list[-n_recent:]
        
        # If total buffer is still growing, reference window is the preceding samples
        ref_samples = buffer_list[:n_ref] if n_ref > 0 else recent_samples

        p_recent = float(np.mean(recent_samples))
        p_ref = float(np.mean(ref_samples))

        # Absolute error delta
        delta = p_recent - p_ref

        # Two-sample Z-test for proportions
        # SE calculation with floor to prevent division by zero
        p_pooled = (sum(recent_samples) + sum(ref_samples)) / (n_recent + max(1, n_ref))
        se_pooled = math.sqrt(max(1e-6, p_pooled * (1.0 - p_pooled) * ((1.0 / n_recent) + (1.0 / max(1, n_ref)))))
        z_stat = max(0.0, (p_recent - p_ref) / se_pooled) if n_ref >= 10 else 0.0

        # One-tailed p-value
        p_value = float(1.0 - stats.norm.cdf(z_stat)) if z_stat > 0 else 1.0

        # Normalized drift score (0.0 to 1.0 scale)
        drift_score = min(1.0, max(0.0, (delta / self.critical_delta) * 0.7 + (z_stat / self.critical_z) * 0.3))

        # Severity determination
        # Requirements: Must be sustained and statistically significant
        if delta >= self.critical_delta and z_stat >= self.critical_z and n_recent >= self.min_samples_to_detect:
            severity = "CRITICAL"
            drift_detected = True
            status_message = (
                f"CRITICAL CONCEPT DRIFT: Prediction error rate jumped from {p_ref:.2%} to {p_recent:.2%} "
                f"(Δ={delta:+.2%}, Z={z_stat:.2f}, p={p_value:.4f}). Immediate retraining recommended."
            )
        elif delta >= self.warning_delta and z_stat >= self.warning_z and n_recent >= self.min_samples_to_detect:
            severity = "WARNING"
            drift_detected = True
            status_message = (
                f"DRIFT WARNING: Elevated error rate detected ({p_ref:.2%} -> {p_recent:.2%}, "
                f"Δ={delta:+.2%}, Z={z_stat:.2f}). Monitoring candidate model."
            )
        else:
            severity = "NORMAL"
            drift_detected = False
            status_message = f"Normal performance: error rate stable at {p_recent:.2%} (reference: {p_ref:.2%})."

        if drift_detected:
            self.drift_count += 1
            self.last_drift_timestamp = now

        return {
            "drift_detected": drift_detected,
            "severity": severity,
            "drift_score": round(drift_score, 4),
            "current_error_rate": round(p_recent, 4),
            "reference_error_rate": round(p_ref, 4),
            "recent_samples_count": n_recent,
            "reference_samples_count": n_ref,
            "p_value": round(p_value, 4),
            "z_score": round(z_stat, 4),
            "detection_timestamp": now,
            "status_message": status_message
        }

    def reset(self):
        """Reset internal buffer and counters."""
        self.error_buffer.clear()
        self.total_feedback_observed = 0
        self.drift_count = 0
        self.last_drift_timestamp = None

