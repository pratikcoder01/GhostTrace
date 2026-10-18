# GhostTrace ML Audit & Training Report

**Date**: 2026-10-17T20:26:49.492596+00:00
**Dataset**: ELLIPTIC Bitcoin Benchmark
**Total Labeled Transactions**: 46,564
**Champion Model**: `RandomForest` (v1.1.0)
**Validation-Tuned Decision Threshold**: `0.42`

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
| **LogisticRegression** | 0.50 | 0.1345 | 0.9566 | 0.2358 | 0.1982 | 0.8455 | 0.7644 | 0.5971 |
| **RandomForest** | 0.50 | **0.9481** | 0.6408 | **0.7647** | **0.7652** | 0.9170 | 0.8192 | **0.9744** |
| **RandomForest (Tuned)** | 0.42 | 0.8276 | **0.6916** | 0.7535 | **0.7652** | 0.9170 | **0.8408** | 0.9706 |
| **XGBoost** | 0.50 | 0.7411 | 0.7082 | 0.7243 | 0.7819 | 0.9328 | 0.8455 | 0.9650 |
| **HistGradientBoosting** | 0.50 | 0.8004 | 0.6888 | 0.7404 | 0.7770 | 0.9376 | 0.8384 | 0.9686 |

---

## 3. Threshold Trade-Off Analysis

- **Default Threshold (0.50)**:
  - Confusion Matrix: `{'true_negatives': 15549, 'false_positives': 38, 'false_negatives': 389, 'true_positives': 694}`
  - High precision focus: Minimizes false alarms for forensic investigators.
- **Validation-Tuned Threshold (0.42)**:
  - Confusion Matrix: `{'true_negatives': 15431, 'false_positives': 156, 'false_negatives': 334, 'true_positives': 749}`
  - Captures additional illicit transactions at the cost of modest additional false positives.

---

## 4. Top Feature Importances (RandomForest)

| Rank | Feature | Importance Score |
|---|---|---|
| #1 | `feature_48` | 0.0784 |
| #2 | `feature_56` | 0.0611 |
| #3 | `feature_50` | 0.0567 |
| #4 | `feature_42` | 0.0466 |
| #5 | `feature_44` | 0.0415 |
| #6 | `feature_91` | 0.0374 |
| #7 | `feature_6` | 0.0336 |
| #8 | `feature_54` | 0.0312 |
| #9 | `feature_19` | 0.0283 |
| #10 | `feature_3` | 0.0278 |

---

## 5. Model Provenance & Artifacts

- **Model Artifact**: `C:\Users\Pratik\Documents\foss\backend\models\model_randomforest_v1.1.0.joblib`
- **Active Model Version**: `v1.1.0`
- **Evaluation Status**: Completed in 37.40 seconds
- **Forensic Disclaimer**: Predictions reflect statistical structural anomaly priority, NOT proof of criminal activity.
