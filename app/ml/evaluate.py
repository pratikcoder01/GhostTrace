from typing import Dict, Any, Optional
import numpy as np
from sklearn.metrics import (
    precision_score, recall_score, f1_score, confusion_matrix,
    precision_recall_curve, auc, roc_auc_score, accuracy_score,
    balanced_accuracy_score, average_precision_score, classification_report
)

def evaluate_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Computes rigorous evaluation metrics focusing on the illicit class (Class 1).
    Accuracy alone is deceptive for heavily imbalanced forensic datasets.
    
    Uses average_precision_score (rectangular step-wise integral) as the authoritative
    PR-AUC metric, while also reporting trapezoidal PR-AUC to document baseline differences.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)

    # Class 1 (illicit) metrics
    prec = precision_score(y_true, y_pred, pos_label=1, zero_division=0)
    rec = recall_score(y_true, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_true, y_pred, pos_label=1, zero_division=0)

    # Class 0 (licit) metrics
    prec_licit = precision_score(y_true, y_pred, pos_label=0, zero_division=0)
    rec_licit = recall_score(y_true, y_pred, pos_label=0, zero_division=0)
    f1_licit = f1_score(y_true, y_pred, pos_label=0, zero_division=0)

    # Global metrics
    acc = accuracy_score(y_true, y_pred)
    b_acc = balanced_accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)

    illicit_count = int(np.sum(y_true == 1))
    licit_count = int(np.sum(y_true == 0))
    total_samples = len(y_true)
    prevalence = float(illicit_count / total_samples) if total_samples > 0 else 0.0

    metrics: Dict[str, Any] = {
        "threshold_applied": round(float(threshold), 4),
        "illicit_precision": round(float(prec), 4),
        "illicit_recall": round(float(rec), 4),
        "illicit_f1": round(float(f1), 4),
        "licit_precision": round(float(prec_licit), 4),
        "licit_recall": round(float(rec_licit), 4),
        "licit_f1": round(float(f1_licit), 4),
        "accuracy": round(float(acc), 4),
        "balanced_accuracy": round(float(b_acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        },
        "class_distribution": {
            "total_samples": total_samples,
            "illicit_count": illicit_count,
            "licit_count": licit_count,
            "positive_prevalence": round(prevalence, 4)
        }
    }

    if y_proba is not None:
        y_proba = np.asarray(y_proba, dtype=float)
        try:
            # Authoritative PR-AUC: average_precision_score (step-function integral)
            ap = average_precision_score(y_true, y_proba)
            metrics["average_precision"] = round(float(ap), 4)

            # Historical / trapezoidal PR-AUC via auc(r, p)
            p_curve, r_curve, _ = precision_recall_curve(y_true, y_proba)
            pr_auc_trap = auc(r_curve, p_curve)
            metrics["pr_auc_trapezoidal"] = round(float(pr_auc_trap), 4)

            # ROC-AUC
            roc = roc_auc_score(y_true, y_proba)
            metrics["roc_auc"] = round(float(roc), 4)
        except Exception:
            metrics["average_precision"] = None
            metrics["pr_auc_trapezoidal"] = None
            metrics["roc_auc"] = None

    return metrics
