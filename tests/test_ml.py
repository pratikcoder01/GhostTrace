import pytest
import numpy as np
from sklearn.dummy import DummyClassifier
from backend.app.ml.evaluate import evaluate_classification
from backend.app.ml.model_registry import model_registry
from backend.app.ml.predict import inference_service
from backend.app.schemas import NetworkType

def test_evaluation_metrics_calculation():
    # 8 samples: 4 licit (0), 4 illicit (1)
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_pred = np.array([0, 0, 0, 1, 0, 1, 1, 1]) # 1 FP, 1 FN, 3 TP, 3 TN
    y_proba = np.array([0.1, 0.2, 0.3, 0.8, 0.4, 0.9, 0.85, 0.95])

    metrics = evaluate_classification(y_true, y_pred, y_proba)

    assert metrics["confusion_matrix"]["true_positives"] == 3
    assert metrics["confusion_matrix"]["false_positives"] == 1
    assert metrics["confusion_matrix"]["false_negatives"] == 1
    assert metrics["confusion_matrix"]["true_negatives"] == 3
    assert metrics["illicit_precision"] == 0.75
    assert metrics["illicit_recall"] == 0.75
    assert metrics["illicit_f1"] == 0.75
    assert metrics["average_precision"] is not None
    assert metrics["roc_auc"] is not None
    assert metrics["balanced_accuracy"] == 0.75

def test_dummy_baseline_pr_auc_equals_prevalence():
    """
    Verifies that the DummyClassifier's Average Precision exactly matches
    the positive class prevalence, solving the historical trapezoidal 0.5325 inflation artifact.
    """
    # 100 samples with 10 positives (10% prevalence)
    y_true = np.array([1] * 10 + [0] * 90)
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(np.zeros((100, 1)), y_true)
    y_proba = dummy.predict_proba(np.zeros((100, 1)))[:, 1]
    y_pred = dummy.predict(np.zeros((100, 1)))

    metrics = evaluate_classification(y_true, y_pred, y_proba)
    # Average precision must equal prevalence (0.10)
    assert metrics["average_precision"] == 0.10
    # Trapezoidal PR-AUC connects (r=1, p=0.10) to (r=0, p=1.0) artificially yielding (0.1 + 1.0)/2 = 0.55
    assert metrics["pr_auc_trapezoidal"] == 0.55
    assert metrics["accuracy"] == 0.90
    assert metrics["illicit_f1"] == 0.0

def test_model_registry_and_active_model_loading():
    bundle = model_registry.load_active_model(force_reload=True)
    assert bundle is not None
    assert "model" in bundle
    assert "scaler" in bundle
    assert bundle["features_count"] == 165
    assert bundle["network"] == "bitcoin"
    assert bundle["algorithm"] in ["RandomForest", "XGBoost", "LogisticRegression"]
    assert bundle["version"] == "v1.1.0"
    assert "optimal_threshold" in bundle

def test_inference_service_prediction():
    bundle = model_registry.load_active_model()
    assert bundle is not None

    # Create dummy feature vector of correct dimension (165)
    dummy_features = [0.0] * bundle["features_count"]

    res = inference_service.predict(
        features=dummy_features,
        tx_id="tx_unit_test",
        network=NetworkType.BITCOIN
    )

    assert res.tx_id == "tx_unit_test"
    assert res.prediction_label in ["illicit", "licit"]
    assert res.prediction_class in [0, 1]
    assert 0.0 <= res.risk_score <= 1.0
    assert res.network == "bitcoin"
    assert len(res.limitations) > 0

def test_inference_dimension_mismatch_rejection():
    # Wrong dimension must raise ValueError
    with pytest.raises(ValueError) as excinfo:
        inference_service.predict(
            features=[0.1, 0.2], # only 2 features instead of 165
            tx_id="tx_bad_dim"
        )
    assert "Feature dimension mismatch" in str(excinfo.value)
