import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Union, Optional
from sklearn.preprocessing import StandardScaler
from backend.app.ml.dataset_generator import CATEGORIES

NUMERICAL_FEATURES = [
    "amount",
    "tx_hour",
    "velocity_1h",
    "distance_from_prev",
    "foreign_transaction",
    "new_device",
    "device_trust_score",
    "ip_risk_score",
]

TARGET_COLUMNS = ["is_fraud", "fraud_regime", "pattern_type", "tx_id", "customer_id", "timestamp"]

class FraudFeaturePipeline:
    """
    Standardized preprocessing pipeline for both training batches and single-transaction inference.
    Guarantees strict target leakage prevention: target columns and IDs are stripped.
    Provides identical transformations for fixed and adaptive models.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.categories: List[str] = list(CATEGORIES)
        self.numerical_cols: List[str] = list(NUMERICAL_FEATURES)
        self.is_fitted: bool = False
        self._feature_names: List[str] = []

    def _build_feature_names(self) -> List[str]:
        names = list(self.numerical_cols)
        for cat in self.categories:
            names.append(f"cat_{cat}")
        return names

    def get_feature_names(self) -> List[str]:
        if not self._feature_names:
            self._feature_names = self._build_feature_names()
        return self._feature_names

    def _prepare_df(self, data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> pd.DataFrame:
        """Converts diverse input types into a standardized DataFrame without leakage."""
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Drop any leakage/id columns if present
        cols_to_drop = [c for c in TARGET_COLUMNS if c in df.columns]
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)

        # Handle missing columns if any
        for num_col in self.numerical_cols:
            if num_col not in df.columns:
                df[num_col] = 0.0

        if "merchant_category" not in df.columns:
            df["merchant_category"] = "retail"

        return df

    def fit(self, data: Union[pd.DataFrame, List[Dict[str, Any]]]) -> "FraudFeaturePipeline":
        """Fit scaler on numerical features of the training set."""
        df = self._prepare_df(data)
        num_vals = df[self.numerical_cols].values.astype(np.float64)
        self.scaler.fit(num_vals)
        self.is_fitted = True
        self._feature_names = self._build_feature_names()
        return self

    def transform(self, data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> np.ndarray:
        """Transform numerical features and one-hot encode categorical features."""
        if not self.is_fitted:
            raise RuntimeError("FraudFeaturePipeline must be fitted before calling transform.")

        df = self._prepare_df(data)
        
        # Scale numerical features
        num_vals = df[self.numerical_cols].values.astype(np.float64)
        scaled_nums = self.scaler.transform(num_vals)

        # One-hot encode category across fixed known categories
        cat_series = df["merchant_category"].astype(str)
        cat_one_hot = np.zeros((len(df), len(self.categories)), dtype=np.float64)
        for idx, cat_val in enumerate(cat_series):
            if cat_val in self.categories:
                cat_idx = self.categories.index(cat_val)
                cat_one_hot[idx, cat_idx] = 1.0
            # Unseen categories remain all zeros (safe OOD handling)

        return np.hstack([scaled_nums, cat_one_hot])

    def fit_transform(self, data: Union[pd.DataFrame, List[Dict[str, Any]]]) -> np.ndarray:
        return self.fit(data).transform(data)

    def save(self, filepath: str) -> str:
        """Persist preprocessor to disk."""
        joblib.dump(self, filepath)
        return filepath

    @classmethod
    def load(cls, filepath: str) -> "FraudFeaturePipeline":
        """Load preprocessor from disk."""
        obj = joblib.load(filepath)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not an instance of {cls.__name__}")
        return obj
