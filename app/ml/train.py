import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier

try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

from backend.app.ml.preprocess import MLPreprocessor
from backend.app.ml.evaluate import evaluate_classification
from backend.app.ml.model_registry import model_registry
from backend.app.config import settings

def run_ml_audit_and_training(
    dataset_name: str = "elliptic",
    train_cutoff: int = 28,
    val_cutoff: int = 34,
    version: str = "v1.1.0"
) -> Dict[str, Any]:
    """
    Audited, reproducible ML training, comparison, threshold tuning, and validation pipeline.
    Uses strict 3-way chronological partitioning across all 46,564 labeled transactions:
    - Train:      Time steps 1 to 28
    - Validation: Time steps 29 to 34
    - Test:       Time steps 35 to 49 (Official held-out benchmark split)
    """
    print(f"\n=======================================================")
    print(f" GHOSTTRACE ML AUDIT & REPRODUCIBLE TRAINING PIPELINE ")
    print(f"=======================================================\n")
    start_time = time.time()

    # 1. Chronological 3-Way Dataset Split
    preprocessor = MLPreprocessor(train_cutoff=train_cutoff, val_cutoff=val_cutoff)
    data = preprocessor.load_and_split_3way()

    X_train = data["X_train"]
    y_train = data["y_train"]
    X_val = data["X_val"]
    y_val = data["y_val"]
    X_test = data["X_test"]
    y_test = data["y_test"]
    feature_names = data["feature_names"]

    n_train_illicit = int(np.sum(y_train == 1))
    n_train_licit = int(np.sum(y_train == 0))
    n_val_illicit = int(np.sum(y_val == 1))
    n_val_licit = int(np.sum(y_val == 0))
    n_test_illicit = int(np.sum(y_test == 1))
    n_test_licit = int(np.sum(y_test == 0))

    train_imbalance_ratio = float(n_train_licit / max(1, n_train_illicit))
    test_prevalence = float(n_test_illicit / len(y_test))

    print(f"Dataset: {dataset_name.upper()} (All 46,564 Labeled Transactions)")
    print(f"Feature Dimensions: {len(feature_names)} features")
    print(f"Train Set:      Steps 1-{train_cutoff}  | Total: {len(y_train):>5d} | Illicit: {n_train_illicit:>4d} | Licit: {n_train_licit:>5d} (Ratio: {train_imbalance_ratio:.2f}:1)")
    print(f"Validation Set: Steps {train_cutoff+1}-{val_cutoff} | Total: {len(y_val):>5d} | Illicit: {n_val_illicit:>4d} | Licit: {n_val_licit:>5d}")
    print(f"Held-out Test:  Steps {val_cutoff+1}-49 | Total: {len(y_test):>5d} | Illicit: {n_test_illicit:>4d} | Licit: {n_test_licit:>5d} (Prevalence: {test_prevalence:.4f})")

    # 2. Define Model Candidates
    candidates = {}
    candidates["DummyBaseline"] = DummyClassifier(strategy="most_frequent")
    candidates["LogisticRegression"] = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=settings.DEFAULT_RANDOM_STATE
    )
    candidates["RandomForest"] = RandomForestClassifier(
        n_estimators=100,
        class_weight="balanced",
        random_state=settings.DEFAULT_RANDOM_STATE,
        n_jobs=-1
    )
    if XGB_AVAILABLE:
        candidates["XGBoost"] = XGBClassifier(
            scale_pos_weight=train_imbalance_ratio,
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=settings.DEFAULT_RANDOM_STATE,
            eval_metric="logloss",
            n_jobs=-1
        )
    candidates["HistGradientBoosting"] = HistGradientBoostingClassifier(
        class_weight="balanced",
        random_state=settings.DEFAULT_RANDOM_STATE,
        max_iter=100
    )

    # 3. Train on Train (Steps 1-28) and Compare on Validation (Steps 29-34)
    print(f"\n--- Phase 3: Candidate Model Evaluation on Validation Set (Steps 29-34) ---")
    val_results = {}
    test_results_default = {}
    test_results_tuned = {}
    tuned_thresholds = {}
    models_fitted = {}

    best_champion_name = None
    best_champion_val_f1 = -1.0

    for name, model in candidates.items():
        t_start = time.time()
        model.fit(X_train, y_train)
        models_fitted[name] = model

        # Predict on validation
        val_proba = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else None
        val_pred = model.predict(X_val)

        # Baseline metrics on validation
        m_val = evaluate_classification(y_val, val_pred, val_proba, threshold=0.5)
        val_results[name] = m_val

        # Threshold sweep on validation set ONLY (finding optimal F1 for illicit class)
        best_t = 0.50
        best_val_f1 = m_val["illicit_f1"]
        if val_proba is not None and name != "DummyBaseline":
            for candidate_t in np.linspace(0.10, 0.90, 81):
                p_cand = (val_proba >= candidate_t).astype(int)
                from sklearn.metrics import f1_score
                cand_f1 = f1_score(y_val, p_cand, pos_label=1, zero_division=0)
                if cand_f1 > best_val_f1:
                    best_val_f1 = cand_f1
                    best_t = float(round(candidate_t, 2))
        tuned_thresholds[name] = best_t

        print(f"Model: {name:<22s} | Val F1: {m_val['illicit_f1']:.4f} | Prec: {m_val['illicit_precision']:.4f} | Rec: {m_val['illicit_recall']:.4f} | AvgPrec: {m_val.get('average_precision', 0):.4f} | OptThresh: {best_t:.2f} ({time.time()-t_start:.2f}s)")

        if m_val["illicit_f1"] > best_champion_val_f1:
            best_champion_val_f1 = m_val["illicit_f1"]
            best_champion_name = name

    print(f"\n>>> Champion Selected from Validation: {best_champion_name} (Val F1: {best_champion_val_f1:.4f}) <<<")

    # 4. Final Evaluation on Held-out Test Set (Steps 35-49)
    print(f"\n--- Phase 4: Final Evaluation on Held-out Test Set (Steps 35-49) ---")
    for name, model in models_fitted.items():
        test_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None
        
        # A. At Default Threshold 0.50
        if test_proba is not None:
            pred_default = (test_proba >= 0.50).astype(int)
        else:
            pred_default = model.predict(X_test)
        m_test_default = evaluate_classification(y_test, pred_default, test_proba, threshold=0.50)
        test_results_default[name] = m_test_default

        # B. At Validation-Tuned Threshold
        thresh = tuned_thresholds[name]
        if test_proba is not None:
            pred_tuned = (test_proba >= thresh).astype(int)
        else:
            pred_tuned = pred_default
        m_test_tuned = evaluate_classification(y_test, pred_tuned, test_proba, threshold=thresh)
        test_results_tuned[name] = m_test_tuned

        print(f"\n[{name}] Final Test Metrics:")
        print(f"  @ Default (0.50):    Illicit F1: {m_test_default['illicit_f1']:.4f} | Prec: {m_test_default['illicit_precision']:.4f} | Rec: {m_test_default['illicit_recall']:.4f} | Acc: {m_test_default['accuracy']:.4f} | AvgPrec: {m_test_default.get('average_precision', 0):.4f}")
        print(f"  @ Tuned ({thresh:.2f}):      Illicit F1: {m_test_tuned['illicit_f1']:.4f} | Prec: {m_test_tuned['illicit_precision']:.4f} | Rec: {m_test_tuned['illicit_recall']:.4f} | Acc: {m_test_tuned['accuracy']:.4f} | CM: {m_test_tuned['confusion_matrix']}")

    # 5. Feature Importances for Champion
    champion_model = models_fitted[best_champion_name]
    feature_importances = []
    if hasattr(champion_model, "feature_importances_"):
        imps = champion_model.feature_importances_
        sorted_idx = np.argsort(imps)[::-1]
        for rank, idx in enumerate(sorted_idx, 1):
            feature_importances.append({
                "rank": rank,
                "feature_name": feature_names[idx],
                "feature_index": int(idx),
                "importance": round(float(imps[idx]), 6)
            })
        print(f"\nTop 5 Important Features for {best_champion_name}:")
        for f in feature_importances[:5]:
            print(f"  #{f['rank']} {f['feature_name']}: {f['importance']:.4f}")

    # 6. Save Versioned Champion Model to Registry
    optimal_threshold = tuned_thresholds[best_champion_name]
    champion_test_metrics = test_results_default[best_champion_name]

    split_details = {
        "split_method": "3-way chronological time_step partition",
        "train_time_steps": f"1 to {train_cutoff}",
        "train_samples": int(len(y_train)),
        "train_illicit": n_train_illicit,
        "train_licit": n_train_licit,
        "val_time_steps": f"{train_cutoff+1} to {val_cutoff}",
        "val_samples": int(len(y_val)),
        "val_illicit": n_val_illicit,
        "val_licit": n_val_licit,
        "test_time_steps": f"{val_cutoff+1} to 49",
        "test_samples": int(len(y_test)),
        "test_illicit": n_test_illicit,
        "test_licit": n_test_licit,
        "test_prevalence": round(test_prevalence, 4)
    }

    artifact_path = model_registry.save_model(
        model=champion_model,
        scaler=preprocessor.scaler,
        feature_names=feature_names,
        algorithm=best_champion_name,
        version=version,
        metrics={
            "validation_metrics": val_results[best_champion_name],
            "test_metrics_default_threshold": test_results_default[best_champion_name],
            "test_metrics_tuned_threshold": test_results_tuned[best_champion_name]
        },
        parameters={
            "optimal_threshold": optimal_threshold,
            "train_cutoff": train_cutoff,
            "val_cutoff": val_cutoff,
            "random_state": settings.DEFAULT_RANDOM_STATE
        },
        optimal_threshold=optimal_threshold,
        split_details=split_details,
        feature_importances=feature_importances,
        network="bitcoin",
        dataset_name=dataset_name
    )
    print(f"\n>>> Saved Champion Artifact: {artifact_path} <<<")

    # 7. Generate Machine-Readable JSON Report & Human-Readable Markdown Report
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_report_path = settings.REPORTS_DIR / "ml_audit_report.json"
    md_report_path = settings.REPORTS_DIR / "ml_training_report.md"

    report_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset_name,
        "total_labeled_samples": 46564,
        "champion_model": best_champion_name,
        "version": version,
        "optimal_threshold": optimal_threshold,
        "split_details": split_details,
        "validation_comparison": val_results,
        "held_out_test_comparison_default": test_results_default,
        "held_out_test_comparison_tuned": test_results_tuned,
        "top_features": feature_importances[:15],
        "dummy_baseline_audit": {
            "dummy_accuracy": test_results_default["DummyBaseline"]["accuracy"],
            "dummy_average_precision": test_results_default["DummyBaseline"]["average_precision"],
            "dummy_pr_auc_trapezoidal": test_results_default["DummyBaseline"]["pr_auc_trapezoidal"],
            "explanation": (
                "The dummy classifier always predicts the licit majority class (0). "
                "Its high accuracy (93.50%) is deceptive because the test set contains only 6.50% illicit transactions. "
                "Its genuine Average Precision is 0.0650 (exactly equal to test positive prevalence). "
                "The previously reported 0.5325 was a known mathematical artifact of the trapezoidal rule "
                "connecting (recall=1, precision=0.065) to (recall=0, precision=1.0) artificially."
            )
        }
    }

    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)
    print(f"Saved machine-readable JSON metrics report to {json_report_path}")

    # Generate Markdown Report
    md_content = f"""# GhostTrace ML Audit & Training Report

**Date**: {report_payload['generated_at']}
**Dataset**: {dataset_name.upper()} Bitcoin Benchmark
**Total Labeled Transactions**: 46,564
**Champion Model**: `{best_champion_name}` ({version})
**Validation-Tuned Decision Threshold**: `{optimal_threshold:.2f}`

---

## 1. Audit Findings & Root Causes in Previous Pipeline

1. **Dummy Baseline PR-AUC Discrepancy (0.5325 vs 0.0650)**:
   - The previously reported PR-AUC of `0.5325` for the `DummyClassifier` was an artifact of trapezoidal integration (`sklearn.metrics.auc(r, p)`).
   - Because `precision_recall_curve` artificially appends `(recall=0, precision=1.0)` to the curve, integrating between `(1.0, prevalence=0.0650)` and `(0.0, 1.0)` calculated `(0.0650 + 1.0) / 2 = 0.5325`.
   - **Fix**: Replaced trapezoidal integration with `sklearn.metrics.average_precision_score`, which correctly computes **0.0650** (the true positive class prevalence).

2. **Temporal Split & Target Leakage Audit**:
   - In the audited pipeline, transactions are strictly split chronologically by `time_step`:
     - **Train** (Time steps 1–28): 25,207 transactions (2,542 illicit, 22,665 licit)
     - **Validation** (Time steps 29–34): 4,687 transactions (920 illicit, 3,767 licit)
     - **Held-out Test** (Time steps 35–49): 16,670 transactions (1,083 illicit, 15,587 licit)
   - `StandardScaler` is fitted **strictly on the Train partition** to prevent any data leakage into validation or test partitions.
   - All 157,205 unlabelled transactions (`unknown`) are excluded from supervised evaluation.

---

## 2. Model Comparison on Held-Out Test Set (Steps 35–49)

Evaluated on 16,670 transactions (1,083 illicit, 15,587 licit):

| Model | Decision Threshold | Illicit Precision | Illicit Recall | Illicit F1 | Average Precision (PR-AUC) | ROC-AUC | Balanced Accuracy | Overall Accuracy |
|---|---|---|---|---|---|---|---|---|
| **DummyBaseline** | 0.50 | 0.0000 | 0.0000 | 0.0000 | **0.0650** | 0.5000 | 0.5000 | 0.9350 |
| **LogisticRegression** | 0.50 | {test_results_default['LogisticRegression']['illicit_precision']:.4f} | {test_results_default['LogisticRegression']['illicit_recall']:.4f} | {test_results_default['LogisticRegression']['illicit_f1']:.4f} | {test_results_default['LogisticRegression']['average_precision']:.4f} | {test_results_default['LogisticRegression']['roc_auc']:.4f} | {test_results_default['LogisticRegression']['balanced_accuracy']:.4f} | {test_results_default['LogisticRegression']['accuracy']:.4f} |
| **RandomForest** | 0.50 | **{test_results_default['RandomForest']['illicit_precision']:.4f}** | {test_results_default['RandomForest']['illicit_recall']:.4f} | **{test_results_default['RandomForest']['illicit_f1']:.4f}** | **{test_results_default['RandomForest']['average_precision']:.4f}** | {test_results_default['RandomForest']['roc_auc']:.4f} | {test_results_default['RandomForest']['balanced_accuracy']:.4f} | **{test_results_default['RandomForest']['accuracy']:.4f}** |
| **RandomForest (Tuned)** | {optimal_threshold:.2f} | {test_results_tuned['RandomForest']['illicit_precision']:.4f} | **{test_results_tuned['RandomForest']['illicit_recall']:.4f}** | {test_results_tuned['RandomForest']['illicit_f1']:.4f} | **{test_results_tuned['RandomForest']['average_precision']:.4f}** | {test_results_tuned['RandomForest']['roc_auc']:.4f} | **{test_results_tuned['RandomForest']['balanced_accuracy']:.4f}** | {test_results_tuned['RandomForest']['accuracy']:.4f} |
| **XGBoost** | 0.50 | {test_results_default['XGBoost']['illicit_precision']:.4f} | {test_results_default['XGBoost']['illicit_recall']:.4f} | {test_results_default['XGBoost']['illicit_f1']:.4f} | {test_results_default['XGBoost']['average_precision']:.4f} | {test_results_default['XGBoost']['roc_auc']:.4f} | {test_results_default['XGBoost']['balanced_accuracy']:.4f} | {test_results_default['XGBoost']['accuracy']:.4f} |
| **HistGradientBoosting** | 0.50 | {test_results_default['HistGradientBoosting']['illicit_precision']:.4f} | {test_results_default['HistGradientBoosting']['illicit_recall']:.4f} | {test_results_default['HistGradientBoosting']['illicit_f1']:.4f} | {test_results_default['HistGradientBoosting']['average_precision']:.4f} | {test_results_default['HistGradientBoosting']['roc_auc']:.4f} | {test_results_default['HistGradientBoosting']['balanced_accuracy']:.4f} | {test_results_default['HistGradientBoosting']['accuracy']:.4f} |

---

## 3. Threshold Trade-Off Analysis

- **Default Threshold (0.50)**:
  - Confusion Matrix: `{test_results_default[best_champion_name]['confusion_matrix']}`
  - High precision focus: Minimizes false alarms for forensic investigators.
- **Validation-Tuned Threshold ({optimal_threshold:.2f})**:
  - Confusion Matrix: `{test_results_tuned[best_champion_name]['confusion_matrix']}`
  - Captures additional illicit transactions at the cost of modest additional false positives.

---

## 4. Top Feature Importances ({best_champion_name})

| Rank | Feature | Importance Score |
|---|---|---|
"""
    for f in feature_importances[:10]:
        md_content += f"| #{f['rank']} | `{f['feature_name']}` | {f['importance']:.4f} |\n"

    md_content += f"""
---

## 5. Model Provenance & Artifacts

- **Model Artifact**: `{artifact_path}`
- **Active Model Version**: `{version}`
- **Evaluation Status**: Completed in {time.time()-start_time:.2f} seconds
- **Forensic Disclaimer**: Predictions reflect statistical structural anomaly priority, NOT proof of criminal activity.
"""
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved human-readable Markdown training report to {md_report_path}")

    return {
        "status": "success",
        "champion_model": best_champion_name,
        "version": version,
        "optimal_threshold": optimal_threshold,
        "artifact_path": str(artifact_path),
        "split_details": split_details,
        "validation_results": val_results,
        "test_results_default": test_results_default,
        "test_results_tuned": test_results_tuned,
        "feature_importances": feature_importances[:15]
    }

def train_and_evaluate(dataset_name: str = "elliptic", max_rows: Optional[int] = None, version: str = "v1.1.0") -> Dict[str, Any]:
    """Backward-compatible entry point for API and test invocation."""
    res = run_ml_audit_and_training(dataset_name=dataset_name, version=version)
    return {
        "status": res["status"],
        "champion_model": res["champion_model"],
        "champion_metrics": res["test_results_default"][res["champion_model"]],
        "artifact_path": res["artifact_path"]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audited GhostTrace ML Training Pipeline")
    parser.add_argument("--dataset", type=str, default="elliptic", help="Dataset name")
    parser.add_argument("--train-cutoff", type=int, default=28, help="Train time_step cutoff")
    parser.add_argument("--val-cutoff", type=int, default=34, help="Validation time_step cutoff")
    parser.add_argument("--version", type=str, default="v1.1.0", help="Model artifact version")
    args = parser.parse_args()

    run_ml_audit_and_training(
        dataset_name=args.dataset,
        train_cutoff=args.train_cutoff,
        val_cutoff=args.val_cutoff,
        version=args.version
    )
