import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str = "model",
    version_tag: str = "v1.0"
) -> Dict[str, Any]:
    """
    Compute rigorous binary classification metrics:
    Accuracy, Precision, Recall, F1, FPR, FNR, Confusion Matrix.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    sample_count = len(y_true)

    if sample_count == 0:
        return {
            "model_name": model_name,
            "version_tag": version_tag,
            "sample_count": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "fpr": 0.0,
            "fnr": 0.0,
            "confusion_matrix": {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
        }

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Confusion matrix extraction
    # tn, fp, fn, tp
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Rates
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    return {
        "model_name": model_name,
        "version_tag": version_tag,
        "sample_count": sample_count,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "fpr": round(fpr, 4),
        "fnr": round(fnr, 4),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp)
        }
    }

def compare_models(
    y_true: np.ndarray,
    fixed_pred: np.ndarray,
    adaptive_pred: np.ndarray,
    fixed_version: str = "v1.0-fixed",
    adaptive_version: str = "v1.0-adaptive"
) -> Dict[str, Any]:
    """
    Evaluates both models on identical chronological ground-truth records.
    Returns side-by-side comparison and metrics diff.
    """
    fixed_metrics = compute_metrics(y_true, fixed_pred, model_name="fixed", version_tag=fixed_version)
    adaptive_metrics = compute_metrics(y_true, adaptive_pred, model_name="adaptive", version_tag=adaptive_version)

    f1_delta = round(adaptive_metrics["f1_score"] - fixed_metrics["f1_score"], 4)
    recall_delta = round(adaptive_metrics["recall"] - fixed_metrics["recall"], 4)
    fnr_delta = round(adaptive_metrics["fnr"] - fixed_metrics["fnr"], 4)

    return {
        "fixed_model": fixed_metrics,
        "adaptive_model": adaptive_metrics,
        "deltas": {
            "f1_score_gain": f1_delta,
            "recall_gain": recall_delta,
            "fnr_reduction": fnr_delta
        },
        "evaluated_samples": len(y_true)
    }

