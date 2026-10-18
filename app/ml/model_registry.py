import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import joblib
from backend.app.config import settings

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Manages saving, loading, versioning, and provenance of trained forensic models.
    """
    def __init__(self, models_dir: Path = settings.MODELS_DIR):
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.active_bundle: Optional[Dict[str, Any]] = None

    def save_model(
        self,
        model: Any,
        scaler: Any,
        feature_names: list,
        algorithm: str,
        version: str,
        metrics: Dict[str, Any],
        parameters: Dict[str, Any],
        optimal_threshold: float = 0.5,
        split_details: Optional[Dict[str, Any]] = None,
        feature_importances: Optional[List[Dict[str, Any]]] = None,
        network: str = "bitcoin",
        dataset_name: str = "elliptic"
    ) -> Path:
        """
        Saves model bundle with fitted scaler, optimal threshold, split details, and metadata.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        artifact_filename = f"model_{algorithm.lower()}_{version}.joblib"
        artifact_path = self.models_dir / artifact_filename

        bundle = {
            "model": model,
            "scaler": scaler,
            "feature_names": feature_names,
            "features_count": len(feature_names),
            "algorithm": algorithm,
            "version": version,
            "optimal_threshold": float(optimal_threshold),
            "split_details": split_details or {},
            "feature_importances": feature_importances or [],
            "network": network,
            "dataset": dataset_name,
            "metrics": metrics,
            "parameters": parameters,
            "trained_at": timestamp,
            "limitations": (
                "Supervised benchmark model trained on Bitcoin Elliptic graph features. "
                "Scores represent model-derived statistical anomaly priority, NOT definitive criminal proof. "
                "Must NOT be directly applied to Ethereum or cross-chain state without validated calibration."
            )
        }

        # Save binary artifact
        joblib.dump(bundle, artifact_path)

        # Save human-readable metadata JSON sidecar
        metadata_path = self.models_dir / f"model_{algorithm.lower()}_{version}_metadata.json"
        metadata = {
            "artifact_path": str(artifact_path),
            "algorithm": algorithm,
            "version": version,
            "optimal_threshold": float(optimal_threshold),
            "network": network,
            "dataset": dataset_name,
            "features_count": len(feature_names),
            "split_details": split_details or {},
            "metrics": metrics,
            "top_features": (feature_importances or [])[:10],
            "parameters": parameters,
            "trained_at": timestamp,
            "limitations": bundle["limitations"]
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Update active bundle in memory
        self.active_bundle = bundle
        return artifact_path

    def load_active_model(self, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        Loads the most recently modified valid model bundle from disk.
        """
        if self.active_bundle is not None and not force_reload:
            return self.active_bundle

        joblib_files = list(self.models_dir.glob("*.joblib"))
        if not joblib_files:
            return None

        # Sort by modification time (most recent first)
        joblib_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        latest_file = joblib_files[0]
        try:
            bundle = joblib.load(latest_file)
            self.active_bundle = bundle
            return bundle
        except Exception as e:
            logger.error(f"Failed to load model from {latest_file}: {e}")
            return None

model_registry = ModelRegistry()
