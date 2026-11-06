import os
import tempfile
import numpy as np
import pandas as pd
import pytest

from backend.app.ml.dataset_generator import SyntheticDatasetGenerator, CATEGORIES
from backend.app.ml.preprocessor import FraudFeaturePipeline, NUMERICAL_FEATURES, TARGET_COLUMNS
from backend.app.ml.fixed_model import FixedFraudModel
from backend.app.ml.adaptive_model import AdaptiveFraudModel
from backend.app.ml.evaluation import compute_metrics, compare_models

def test_dataset_generator():
    """Verify synthetic dataset generator produces valid transactions across both regimes."""
    generator = SyntheticDatasetGenerator(seed=123)
    df = generator.generate_dataset(
        total_samples=1000,
        historical_ratio=0.6,
        historical_fraud_rate=0.1,
        drift_fraud_rate=0.2
    )

    assert len(df) == 1000
    assert not df.isna().any().any(), "Generated dataset should contain no NaN values"
    
    # Required columns
    required_cols = [
        "tx_id", "customer_id", "timestamp", "amount", "tx_hour", "velocity_1h",
        "distance_from_prev", "new_device", "merchant_category", "foreign_transaction",
        "device_trust_score", "ip_risk_score", "is_fraud", "fraud_regime", "pattern_type"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing expected column: {col}"

    # Verify both regimes exist
    assert "historical" in df["fraud_regime"].values
    assert "drift_evasion" in df["fraud_regime"].values
    assert set(df["is_fraud"].unique()).issubset({0, 1})

def test_preprocessor_and_target_leakage():
    """Verify feature extractor normalizes features and strictly prevents target leakage."""
    generator = SyntheticDatasetGenerator(seed=42)
    df = generator.generate_dataset(total_samples=300)

    pipeline = FraudFeaturePipeline()
    X = pipeline.fit_transform(df)

    # Verify dimensions
    expected_dim = len(NUMERICAL_FEATURES) + len(CATEGORIES)
    assert X.shape == (300, expected_dim)

    # Check that target columns were NOT included in feature names
    feature_names = pipeline.get_feature_names()
    assert len(feature_names) == expected_dim
    for target_col in TARGET_COLUMNS:
        assert target_col not in feature_names

    # Test single-record dictionary transformation
    single_record = {
        "amount": 95.0,
        "tx_hour": 14,
        "velocity_1h": 1,
        "distance_from_prev": 5.2,
        "foreign_transaction": 0,
        "new_device": 0,
        "device_trust_score": 0.9,
        "ip_risk_score": 0.05,
        "merchant_category": "grocery",
        "is_fraud": 1  # Should be safely ignored
    }
    x_single = pipeline.transform(single_record)
    assert x_single.shape == (1, expected_dim)

def test_fixed_model():
    """Verify fixed model training, predictions, and probability outputs."""
    np.random.seed(42)
    X = np.random.randn(200, 16)
    # Fraud correlated with feature 0 > 1.0
    y = (X[:, 0] > 0.5).astype(int)

    model = FixedFraudModel(random_state=42)
    assert not model.is_trained
    model.fit(X, y)
    assert model.is_trained

    # Batch prediction
    preds = model.predict(X)
    assert preds.shape == (200,)
    assert set(preds).issubset({0, 1})

    # Calibrated probabilities
    probs = model.predict_proba(X)
    assert probs.shape == (200, 2)
    assert np.allclose(probs.sum(axis=1), 1.0)

    # Single prediction
    pred, score = model.predict_single(X[0])
    assert pred in (0, 1)
    assert 0.0 <= score <= 1.0

def test_adaptive_model_partial_fit_and_rollback():
    """Verify adaptive model incremental updates, version tracking, and rollback."""
    np.random.seed(42)
    X_init = np.random.randn(200, 16)
    y_init = (X_init[:, 0] > 0.5).astype(int)

    model = AdaptiveFraudModel(random_state=42)
    model.fit(X_init, y_init, version_tag="v1.0-init")
    assert model.version_tag == "v1.0-init"
    initial_coef = model.model.coef_.copy()

    # Streaming update on new verified feedback
    X_new = np.random.randn(50, 16)
    # Drift: now feature 1 indicates fraud
    y_new = (X_new[:, 1] > 0.2).astype(int)
    
    model.partial_fit(X_new, y_new)
    assert model.version_tag == "v1.2-adaptive"
    assert model.total_samples_trained == 250
    # Coefficients must have shifted
    assert not np.allclose(initial_coef, model.model.coef_)

    # Rollback test
    success = model.rollback()
    assert success is True
    assert "rolled_back" in model.version_tag
    assert np.allclose(initial_coef, model.model.coef_)

def test_model_persistence():
    """Verify saving and reloading preprocessor, fixed model, and adaptive model."""
    generator = SyntheticDatasetGenerator(seed=42)
    df = generator.generate_dataset(total_samples=200)

    pipeline = FraudFeaturePipeline()
    X = pipeline.fit_transform(df)
    y = df["is_fraud"].values

    fixed_model = FixedFraudModel(random_state=42).fit(X, y)
    adaptive_model = AdaptiveFraudModel(random_state=42).fit(X, y, version_tag="v1.0-test")

    with tempfile.TemporaryDirectory() as tmpdir:
        pipe_path = os.path.join(tmpdir, "pipe.joblib")
        fixed_path = os.path.join(tmpdir, "fixed.joblib")
        adapt_path = os.path.join(tmpdir, "adapt.joblib")

        pipeline.save(pipe_path)
        fixed_model.save(fixed_path)
        adaptive_model.save(adapt_path)

        loaded_pipe = FraudFeaturePipeline.load(pipe_path)
        loaded_fixed = FixedFraudModel.load(fixed_path)
        loaded_adapt = AdaptiveFraudModel.load(adapt_path)

        # Check identical output on new test sample
        test_df = generator.generate_dataset(total_samples=10)
        X_orig = pipeline.transform(test_df)
        X_loaded = loaded_pipe.transform(test_df)
        assert np.allclose(X_orig, X_loaded)

        assert np.allclose(fixed_model.predict_proba(X_orig), loaded_fixed.predict_proba(X_loaded))
        assert np.allclose(adaptive_model.predict_proba(X_orig), loaded_adapt.predict_proba(X_loaded))
        assert loaded_adapt.version_tag == "v1.0-test"

def test_evaluation_metrics():
    """Verify calculation of accuracy, precision, recall, F1, FPR, FNR, confusion matrix."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_pred = np.array([0, 0, 0, 1, 0, 1, 1, 1])
    # TN=3, FP=1, FN=1, TP=3

    metrics = compute_metrics(y_true, y_pred, model_name="test_model", version_tag="v1.0")
    assert metrics["accuracy"] == 0.75
    assert metrics["precision"] == 0.75  # TP / (TP+FP) = 3/4
    assert metrics["recall"] == 0.75     # TP / (TP+FN) = 3/4
    assert metrics["f1_score"] == 0.75
    assert metrics["fpr"] == 0.25        # FP / (FP+TN) = 1/4
    assert metrics["fnr"] == 0.25        # FN / (FN+TP) = 1/4
    assert metrics["confusion_matrix"] == {"tn": 3, "fp": 1, "fn": 1, "tp": 3}

    # Model comparison
    comp = compare_models(y_true, y_pred, y_pred)
    assert comp["evaluated_samples"] == 8
    assert comp["deltas"]["f1_score_gain"] == 0.0
