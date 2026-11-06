import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from backend.app.ml.dataset_generator import SyntheticDatasetGenerator
from backend.app.ml.preprocessor import FraudFeaturePipeline
from backend.app.ml.fixed_model import FixedFraudModel
from backend.app.ml.adaptive_model import AdaptiveFraudModel
from backend.app.ml.evaluation import compute_metrics, compare_models
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.db_models import DBModelVersion

DATA_PATH = "backend/data/transactions_12k.csv"
PREPROCESSOR_PATH = "backend/models_saved/preprocessor.joblib"
FIXED_MODEL_PATH = "backend/models_saved/fixed_model.joblib"
ADAPTIVE_MODEL_PATH = "backend/models_saved/adaptive_model.joblib"

def run_training_pipeline():
    print("=" * 70)
    print("DRIFTGUARD AI: Phase 2 ML Training & Evaluation Pipeline")
    print("=" * 70)

    # 1. Generate Dataset
    print("\n[Step 1] Generating synthetic transaction dataset...")
    generator = SyntheticDatasetGenerator(seed=42)
    df = generator.generate_dataset(
        total_samples=12000,
        historical_ratio=0.60,      # 7,200 historical, 4,800 drift
        historical_fraud_rate=0.08, # ~576 historical fraud cases
        drift_fraud_rate=0.15       # ~720 drift fraud cases (changed strategy)
    )
    generator.save_dataset_to_csv(df, DATA_PATH)
    print(f"Dataset generated with {len(df)} samples saved to: {DATA_PATH}")
    print(f"Historical samples: {len(df[df['fraud_regime'] != 'drift_evasion'])}")
    print(f"Drift evasion samples: {len(df[df['fraud_regime'] == 'drift_evasion'])}")
    print(f"Total fraud cases: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.2f}%)")

    # 2. Chronological Data Splits
    # Train: first 5,500 historical
    # Historical Holdout: next 1,700 historical
    # Drift Stream: 4,800 drift samples
    df_train_hist = df.iloc[:5500].copy()
    df_val_hist = df.iloc[5500:7200].copy()
    df_drift = df.iloc[7200:].copy()

    print(f"\n[Step 2] Chronological Splits:")
    print(f" - Train (Historical Baseline): {len(df_train_hist)} rows (Fraud rate: {df_train_hist['is_fraud'].mean()*100:.2f}%)")
    print(f" - Holdout (Historical Test):   {len(df_val_hist)} rows (Fraud rate: {df_val_hist['is_fraud'].mean()*100:.2f}%)")
    print(f" - Test Stream (Drift Regime):  {len(df_drift)} rows (Fraud rate: {df_drift['is_fraud'].mean()*100:.2f}%)")

    # 3. Fit Preprocessing Pipeline
    print("\n[Step 3] Fitting Preprocessor (Strict Target Leakage Prevention)...")
    preprocessor = FraudFeaturePipeline()
    X_train = preprocessor.fit_transform(df_train_hist)
    y_train = df_train_hist["is_fraud"].values.astype(int)
    preprocessor.save(PREPROCESSOR_PATH)
    print(f"Feature dimension: {X_train.shape[1]} features.")
    print(f"Preprocessor saved to: {PREPROCESSOR_PATH}")

    # 4. Train Models
    print("\n[Step 4] Training Models on Historical Baseline...")
    fixed_model = FixedFraudModel(random_state=42)
    fixed_model.fit(X_train, y_train)
    fixed_model.save(FIXED_MODEL_PATH)
    print(f"Fixed model trained and saved to: {FIXED_MODEL_PATH}")

    adaptive_model = AdaptiveFraudModel(random_state=42)
    adaptive_model.fit(X_train, y_train, version_tag="v1.0-baseline")
    adaptive_model.save(ADAPTIVE_MODEL_PATH)
    print(f"Adaptive model initialized and saved to: {ADAPTIVE_MODEL_PATH}")

    # 5. Evaluate on Historical Holdout
    print("\n[Step 5] Evaluation on Historical Holdout (Same Regime)...")
    X_val_hist = preprocessor.transform(df_val_hist)
    y_val_hist = df_val_hist["is_fraud"].values.astype(int)

    fixed_val_pred = fixed_model.predict(X_val_hist)
    adaptive_val_pred = adaptive_model.predict(X_val_hist)

    val_comp = compare_models(y_val_hist, fixed_val_pred, adaptive_val_pred, "v1.0-fixed", "v1.0-adaptive")
    print(f"Historical Holdout Results (N={len(y_val_hist)}):")
    print(f"Fixed Model:    Acc={val_comp['fixed_model']['accuracy']:.4f}, Prec={val_comp['fixed_model']['precision']:.4f}, Rec={val_comp['fixed_model']['recall']:.4f}, F1={val_comp['fixed_model']['f1_score']:.4f}, FNR={val_comp['fixed_model']['fnr']:.4f}")
    print(f"Adaptive Model: Acc={val_comp['adaptive_model']['accuracy']:.4f}, Prec={val_comp['adaptive_model']['precision']:.4f}, Rec={val_comp['adaptive_model']['recall']:.4f}, F1={val_comp['adaptive_model']['f1_score']:.4f}, FNR={val_comp['adaptive_model']['fnr']:.4f}")

    # 6. Evaluate on Changed Fraud Strategy (Drift Regime) BEFORE and AFTER Adaptation
    print("\n[Step 6] Simulating Stream of Changed Fraud Strategy (Concept Drift)...")
    X_drift = preprocessor.transform(df_drift)
    y_drift = df_drift["is_fraud"].values.astype(int)

    # Fixed Model evaluates entire drift stream without updating
    fixed_drift_pred = fixed_model.predict(X_drift)
    fixed_drift_metrics = compute_metrics(y_drift, fixed_drift_pred, model_name="fixed", version_tag="v1.0-fixed")

    # Adaptive Model processes stream chronologically:
    # IMPORTANT: Prediction is recorded BEFORE verified feedback is received!
    batch_size = 100
    n_batches = len(df_drift) // batch_size
    adaptive_stream_preds = []

    for b in range(n_batches):
        start_idx = b * batch_size
        end_idx = start_idx + batch_size
        
        X_batch = X_drift[start_idx:end_idx]
        y_batch = y_drift[start_idx:end_idx]

        # 1. Model predicts first (no label exposure!)
        batch_pred = adaptive_model.predict(X_batch)
        adaptive_stream_preds.extend(batch_pred)

        # 2. Simulated feedback arrives delayed -> model learns via partial_fit
        # Weight fraud samples slightly higher for imbalanced streams
        weights = np.where(y_batch == 1, 2.5, 1.0)
        adaptive_model.partial_fit(X_batch, y_batch, sample_weight=weights, promote_version=False)

    adaptive_stream_preds = np.array(adaptive_stream_preds)
    y_drift_evaluated = y_drift[:len(adaptive_stream_preds)]
    adaptive_drift_metrics = compute_metrics(
        y_drift_evaluated,
        adaptive_stream_preds,
        model_name="adaptive",
        version_tag="v1.x-streaming-adapted"
    )

    # Evaluate steady state on the tail 1,000 transactions using strictly prequential predictions
    # (predictions recorded BEFORE each batch was provided as feedback)
    test_tail_X = X_drift[-1000:]
    test_tail_y = y_drift[-1000:]
    fixed_tail_pred = fixed_model.predict(test_tail_X)
    adaptive_tail_pred = adaptive_stream_preds[-1000:]

    tail_comparison = compare_models(
        test_tail_y,
        fixed_tail_pred,
        adaptive_tail_pred,
        fixed_version="v1.0-fixed-decayed",
        adaptive_version=adaptive_model.version_tag
    )

    print("\n" + "=" * 70)
    print("EMPIRICAL COMPARISON UNDER CONCEPT DRIFT (CHANGED FRAUD REGIME)")
    print("=" * 70)
    print(f"Overall Drift Stream (N={len(y_drift_evaluated)}):")
    print(f" Fixed Model:    Acc={fixed_drift_metrics['accuracy']:.4f}, Prec={fixed_drift_metrics['precision']:.4f}, Rec={fixed_drift_metrics['recall']:.4f}, F1={fixed_drift_metrics['f1_score']:.4f}, FNR={fixed_drift_metrics['fnr']:.4f}")
    print(f" Adaptive Model: Acc={adaptive_drift_metrics['accuracy']:.4f}, Prec={adaptive_drift_metrics['precision']:.4f}, Rec={adaptive_drift_metrics['recall']:.4f}, F1={adaptive_drift_metrics['f1_score']:.4f}, FNR={adaptive_drift_metrics['fnr']:.4f}")
    print("\nPost-Adaptation Steady State (Last 1,000 Transactions under new fraud pattern):")
    print(f" Fixed Model:    Acc={tail_comparison['fixed_model']['accuracy']:.4f}, Prec={tail_comparison['fixed_model']['precision']:.4f}, Rec={tail_comparison['fixed_model']['recall']:.4f}, F1={tail_comparison['fixed_model']['f1_score']:.4f}, FNR={tail_comparison['fixed_model']['fnr']:.4f}")
    print(f" Adaptive Model: Acc={tail_comparison['adaptive_model']['accuracy']:.4f}, Prec={tail_comparison['adaptive_model']['precision']:.4f}, Rec={tail_comparison['adaptive_model']['recall']:.4f}, F1={tail_comparison['adaptive_model']['f1_score']:.4f}, FNR={tail_comparison['adaptive_model']['fnr']:.4f}")
    print(f" Recall Gain:    +{tail_comparison['deltas']['recall_gain']*100:.2f}%")
    print(f" F1-Score Gain:  +{tail_comparison['deltas']['f1_score_gain']*100:.2f}%")
    print(f" FNR Reduction:  {tail_comparison['deltas']['fnr_reduction']*100:.2f}%")

    # Save final adapted model
    adaptive_model.save(ADAPTIVE_MODEL_PATH)

    # 7. Persist Version Metadata to SQLite
    print("\n[Step 7] Persisting Model Version Metadata to SQLite...")
    init_db()
    db = SessionLocal()
    try:
        # Clear previous run versions if re-running
        db.query(DBModelVersion).delete()
        
        mv_fixed = DBModelVersion(
            model_name="fixed",
            version_tag="v1.0-fixed-baseline",
            sample_count=len(df_train_hist),
            accuracy=val_comp["fixed_model"]["accuracy"],
            precision=val_comp["fixed_model"]["precision"],
            recall=val_comp["fixed_model"]["recall"],
            f1_score=val_comp["fixed_model"]["f1_score"],
            fpr=val_comp["fixed_model"]["fpr"],
            fnr=val_comp["fixed_model"]["fnr"],
            status="active",
            description="Trained on historical high-ticket and foreign fraud baseline. Static.",
            metrics_json=json.dumps(val_comp["fixed_model"])
        )
        db.add(mv_fixed)

        mv_adaptive = DBModelVersion(
            model_name="adaptive",
            version_tag="v1.0-adaptive-baseline",
            sample_count=len(df_train_hist),
            accuracy=val_comp["adaptive_model"]["accuracy"],
            precision=val_comp["adaptive_model"]["precision"],
            recall=val_comp["adaptive_model"]["recall"],
            f1_score=val_comp["adaptive_model"]["f1_score"],
            fpr=val_comp["adaptive_model"]["fpr"],
            fnr=val_comp["adaptive_model"]["fnr"],
            status="active",
            description="Online SGD model initialized on baseline, learns via partial_fit.",
            metrics_json=json.dumps(val_comp["adaptive_model"])
        )
        db.add(mv_adaptive)

        mv_adapted = DBModelVersion(
            model_name="adaptive",
            version_tag="v1.48-adaptive-drift",
            sample_count=adaptive_model.total_samples_trained,
            accuracy=tail_comparison["adaptive_model"]["accuracy"],
            precision=tail_comparison["adaptive_model"]["precision"],
            recall=tail_comparison["adaptive_model"]["recall"],
            f1_score=tail_comparison["adaptive_model"]["f1_score"],
            fpr=tail_comparison["adaptive_model"]["fpr"],
            fnr=tail_comparison["adaptive_model"]["fnr"],
            status="candidate",
            description="Online model incrementally adapted to micro-velocity card testing fraud.",
            metrics_json=json.dumps(tail_comparison["adaptive_model"])
        )
        db.add(mv_adapted)
        db.commit()
        print("Model versions successfully registered in database.")
    finally:
        db.close()

    return {
        "val_comparison": val_comp,
        "tail_comparison": tail_comparison,
        "fixed_drift_metrics": fixed_drift_metrics,
        "adaptive_drift_metrics": adaptive_drift_metrics
    }

if __name__ == "__main__":
    run_training_pipeline()

