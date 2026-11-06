import os
import copy
import joblib
import numpy as np
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional, List
from sklearn.linear_model import SGDClassifier

class AdaptiveFraudModel:
    """
    Adaptive Online Fraud Detection Model.
    Employs incremental learning via SGDClassifier.partial_fit().
    Learns continuously from newly verified transaction feedback,
    monitors model health, supports version promotion and rollbacks.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = SGDClassifier(
            loss="log_loss",  # Logistic regression yields calibrated probabilities
            penalty="l2",
            alpha=1e-4,
            max_iter=1000,
            tol=1e-3,
            learning_rate="optimal",
            random_state=random_state,
            warm_start=True
        )
        self.is_trained: bool = False
        self.classes_ = np.array([0, 1])
        self.version_tag: str = "v1.0-adaptive-init"
        self.version_counter: int = 0
        self.total_samples_trained: int = 0
        self.incremental_batches_count: int = 0
        self.history: List[Dict[str, Any]] = []
        self._previous_state: Optional[Dict[str, Any]] = None

    def fit(self, X: np.ndarray, y: np.ndarray, version_tag: str = "v1.0-adaptive-baseline") -> "AdaptiveFraudModel":
        """Train baseline model on historical baseline data."""
        self.model.fit(X, y)
        self.is_trained = True
        self.classes_ = self.model.classes_
        self.version_tag = version_tag
        self.version_counter = 1
        self.total_samples_trained = len(y)
        self._record_history("initial_baseline_fit", len(y))
        return self

    def partial_fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        promote_version: bool = True
    ) -> "AdaptiveFraudModel":
        """
        Incrementally update the adaptive model with newly verified transaction feedback.
        Never called before predictions are recorded.
        """
        if not self.is_trained:
            raise RuntimeError("AdaptiveFraudModel must be initially fitted before calling partial_fit.")
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if np.isscalar(y):
            y = np.array([y])

        # Save previous state to allow rollback
        self._backup_state()

        # Update model weights online
        self.model.partial_fit(X, y, classes=self.classes_, sample_weight=sample_weight)
        
        self.total_samples_trained += len(y)
        self.incremental_batches_count += 1
        
        if promote_version:
            self.version_counter += 1
            self.version_tag = f"v1.{self.version_counter}-adaptive"

        self._record_history("partial_fit_update", len(y))
        return self

    def _backup_state(self):
        """Store copy of current model parameters and intercept for rollback."""
        if hasattr(self.model, "coef_"):
            self._previous_state = {
                "coef_": copy.deepcopy(self.model.coef_),
                "intercept_": copy.deepcopy(self.model.intercept_),
                "version_tag": self.version_tag,
                "version_counter": self.version_counter,
                "total_samples_trained": self.total_samples_trained,
                "incremental_batches_count": self.incremental_batches_count
            }

    def rollback(self) -> bool:
        """Rollback to the previous version if available."""
        if self._previous_state is None:
            return False
        
        self.model.coef_ = copy.deepcopy(self._previous_state["coef_"])
        self.model.intercept_ = copy.deepcopy(self._previous_state["intercept_"])
        self.version_tag = f"{self._previous_state['version_tag']}-rolled_back"
        self.version_counter = self._previous_state["version_counter"]
        self.total_samples_trained = self._previous_state["total_samples_trained"]
        self.incremental_batches_count = self._previous_state["incremental_batches_count"]
        
        self._record_history("rollback", 0)
        return True

    def _record_history(self, event_type: str, sample_count: int):
        self.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "version": self.version_tag,
            "samples_added": sample_count,
            "total_samples": self.total_samples_trained
        })

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Predict binary fraud label."""
        proba = self.predict_proba(X)
        return (proba[:, 1] >= threshold).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict calibrated probabilities [P(legit), P(fraud)]."""
        if not self.is_trained:
            raise RuntimeError("AdaptiveFraudModel is not trained.")
        if X.ndim == 1:
            X = X.reshape(1, -1)
        return self.model.predict_proba(X)

    def predict_single(self, feature_vector: np.ndarray, threshold: float = 0.5) -> Tuple[int, float]:
        """Convenience method for single-transaction inference."""
        proba = self.predict_proba(feature_vector)[0, 1]
        prediction = 1 if proba >= threshold else 0
        return prediction, float(proba)

    def save(self, filepath: str) -> str:
        """Persist adaptive model state, version tag, and history to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        payload = {
            "model": self.model,
            "version_tag": self.version_tag,
            "version_counter": self.version_counter,
            "total_samples_trained": self.total_samples_trained,
            "incremental_batches_count": self.incremental_batches_count,
            "is_trained": self.is_trained,
            "history": self.history
        }
        joblib.dump(payload, filepath)
        return filepath

    @classmethod
    def load(cls, filepath: str) -> "AdaptiveFraudModel":
        """Load adaptive model artifact from disk."""
        data = joblib.load(filepath)
        instance = cls()
        instance.model = data["model"]
        instance.version_tag = data["version_tag"]
        instance.version_counter = data["version_counter"]
        instance.total_samples_trained = data["total_samples_trained"]
        instance.incremental_batches_count = data["incremental_batches_count"]
        instance.is_trained = data["is_trained"]
        instance.classes_ = instance.model.classes_
        instance.history = data.get("history", [])
        return instance

