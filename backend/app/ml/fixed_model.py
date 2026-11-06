import os
import joblib
import numpy as np
from typing import Tuple, Dict, Any, Optional
from sklearn.linear_model import SGDClassifier

class FixedFraudModel:
    """
    Traditional Fixed Fraud Detection Model.
    Trained on historical transaction baseline data and never updated after deployment.
    Demonstrates model decay when fraud patterns drift.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = SGDClassifier(
            loss="log_loss",  # Logistic regression yields well-calibrated probabilities
            penalty="l2",
            alpha=1e-4,
            max_iter=1000,
            tol=1e-3,
            random_state=random_state,
            warm_start=False
        )
        self.is_trained: bool = False
        self.classes_ = np.array([0, 1])
        self.metadata: Dict[str, Any] = {
            "model_type": "fixed_sgd_logistic",
            "version": "v1.0-fixed-baseline",
            "samples_trained": 0
        }

    def fit(self, X: np.ndarray, y: np.ndarray) -> "FixedFraudModel":
        """Train model strictly on historical baseline data."""
        self.model.fit(X, y)
        self.is_trained = True
        self.classes_ = self.model.classes_
        self.metadata["samples_trained"] = len(y)
        return self

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Predict binary fraud label (0 = legitimate, 1 = fraud)."""
        proba = self.predict_proba(X)
        return (proba[:, 1] >= threshold).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict calibrated probabilities [P(legit), P(fraud)]."""
        if not self.is_trained:
            raise RuntimeError("FixedFraudModel is not trained.")
        if X.ndim == 1:
            X = X.reshape(1, -1)
        return self.model.predict_proba(X)

    def predict_single(self, feature_vector: np.ndarray, threshold: float = 0.5) -> Tuple[int, float]:
        """Convenience method for single-transaction inference returning (prediction, fraud_probability)."""
        proba = self.predict_proba(feature_vector)[0, 1]
        prediction = 1 if proba >= threshold else 0
        return prediction, float(proba)

    def save(self, filepath: str) -> str:
        """Persist fixed model to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({"model": self.model, "metadata": self.metadata, "is_trained": self.is_trained}, filepath)
        return filepath

    @classmethod
    def load(cls, filepath: str) -> "FixedFraudModel":
        """Load fixed model artifact from disk."""
        data = joblib.load(filepath)
        instance = cls()
        instance.model = data["model"]
        instance.metadata = data["metadata"]
        instance.is_trained = data["is_trained"]
        instance.classes_ = instance.model.classes_
        return instance

