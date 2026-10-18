from typing import List, Dict, Any, Optional
import numpy as np
from backend.app.ml.model_registry import model_registry
from backend.app.schemas import MLPredictResponse, NetworkType

class MLInferenceService:
    """
    Inference service for real-time model scoring, forensic assessment, and schema validation.
    """
    def __init__(self):
        self.registry = model_registry

    def predict(
        self,
        features: List[float],
        tx_id: str = "custom_tx",
        network: NetworkType = NetworkType.BITCOIN,
        custom_threshold: Optional[float] = None
    ) -> MLPredictResponse:
        bundle = self.registry.load_active_model()
        if bundle is None:
            raise RuntimeError("No active ML model found in registry. Please run training first.")

        # Check network compatibility warning
        network_str = network.value if hasattr(network, "value") else str(network)
        if network_str != bundle.get("network", "bitcoin"):
            limitation_note = (
                f"CAUTION: Input network '{network_str}' does not match model training network '{bundle.get('network')}'. "
                "Cross-network generalization is not empirically calibrated."
            )
        else:
            limitation_note = bundle.get("limitations", "")

        expected_dim = bundle.get("features_count", 165)
        if len(features) != expected_dim:
            raise ValueError(
                f"Feature dimension mismatch: received {len(features)} features, "
                f"expected {expected_dim} features matching '{bundle.get('algorithm')}' schema."
            )

        model = bundle["model"]
        scaler = bundle["scaler"]
        threshold = custom_threshold if custom_threshold is not None else bundle.get("optimal_threshold", 0.5)

        # Scale features
        arr = np.array(features, dtype=float).reshape(1, -1)
        scaled_arr = scaler.transform(arr)

        # Risk score / probability
        if hasattr(model, "predict_proba"):
            risk_score = float(model.predict_proba(scaled_arr)[0, 1])
        else:
            risk_score = float(model.predict(scaled_arr)[0])

        # Binary decision using threshold
        pred_class = 1 if risk_score >= threshold else 0
        pred_label = "illicit" if pred_class == 1 else "licit"

        explanation = (
            f"Model {bundle.get('algorithm')} ({bundle.get('version')}) assigned risk score {risk_score:.4f} "
            f"(decision threshold: {threshold:.2f}). Classified as '{pred_label}' based on graph structural and transaction features."
        )

        return MLPredictResponse(
            tx_id=tx_id,
            prediction_label=pred_label,
            prediction_class=pred_class,
            risk_score=round(risk_score, 4),
            model_version=bundle.get("version", "v1.0.0"),
            network=bundle.get("network", "bitcoin"),
            confidence_explanation=explanation,
            limitations=limitation_note
        )

    def get_status(self) -> Dict[str, Any]:
        bundle = self.registry.load_active_model()
        if bundle is None:
            return {
                "model_loaded": False,
                "model_name": None,
                "version": None,
                "network": None,
                "algorithm": None,
                "features_count": 0,
                "metrics": None,
                "evaluation_limitations": "No trained model available on disk. Model training required.",
                "training_timestamp": None
            }
        return {
            "model_loaded": True,
            "model_name": f"{bundle.get('algorithm')}_{bundle.get('version')}",
            "version": bundle.get("version"),
            "network": bundle.get("network"),
            "algorithm": bundle.get("algorithm"),
            "features_count": bundle.get("features_count", 0),
            "optimal_threshold": bundle.get("optimal_threshold", 0.5),
            "metrics": bundle.get("metrics"),
            "evaluation_limitations": bundle.get("limitations", ""),
            "training_timestamp": bundle.get("trained_at")
        }

inference_service = MLInferenceService()
