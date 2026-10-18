import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from backend.app.config import settings

class EllipticDatasetAdapter:
    """
    Adapter for the Elliptic Bitcoin dataset.
    Provides memory-efficient chunked loading, temporal time-step splitting, and label mapping.
    Network: Bitcoin. Data Origin: elliptic_benchmark.
    """
    def __init__(self, data_dir: Path = settings.ELLIPTIC_DATA_DIR):
        self.data_dir = data_dir
        self.classes_path = data_dir / "elliptic_txs_classes.csv"
        self.features_path = data_dir / "elliptic_txs_features.csv"
        self.edgelist_path = data_dir / "elliptic_txs_edgelist.csv"
        self.cache_path = settings.DATA_DIR / "elliptic_labeled_cache.csv"

    def is_available(self) -> bool:
        return (
            self.classes_path.exists()
            and self.features_path.exists()
            and self.edgelist_path.exists()
        )

    def load_classes(self) -> pd.DataFrame:
        """
        Loads classes and maps:
        '1' -> 1 (illicit)
        '2' -> 0 (licit)
        'unknown' -> -1 (unlabelled)
        """
        if not self.classes_path.exists():
            raise FileNotFoundError(f"Classes file not found at {self.classes_path}")

        df = pd.read_csv(self.classes_path)
        if "txId" not in df.columns or "class" not in df.columns:
            raise ValueError("Invalid classes CSV schema: missing 'txId' or 'class'")

        label_map = {"1": 1, "2": 0, "unknown": -1}
        df["mapped_label"] = df["class"].astype(str).map(label_map)
        df["mapped_label"] = df["mapped_label"].fillna(-1).astype(int)
        return df

    def load_edgelist(self, max_edges: Optional[int] = None) -> pd.DataFrame:
        if not self.edgelist_path.exists():
            raise FileNotFoundError(f"Edgelist file not found at {self.edgelist_path}")
        return pd.read_csv(self.edgelist_path, nrows=max_edges)

    def load_features_and_labels(
        self,
        max_rows: Optional[int] = None,
        exclude_unknown: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Loads features joined with classes.
        Extracts across all 49 time steps and caches to avoid re-scanning the 689MB file.
        Returns:
            X (features DataFrame)
            y (labels Series: 1 for illicit, 0 for licit)
            time_steps (time_step Series: 1 to 49)
            tx_ids (txId Series)
        """
        if not self.is_available():
            raise FileNotFoundError(f"Elliptic dataset files missing in {self.data_dir}")

        # Check if cache exists
        if self.cache_path.exists():
            merged = pd.read_csv(self.cache_path)
        else:
            classes_df = self.load_classes()
            labeled_classes = classes_df[classes_df["mapped_label"] != -1]
            labeled_tx_ids = set(labeled_classes["txId"])

            feature_chunks = []
            chunk_size = 50000
            for chunk in pd.read_csv(self.features_path, header=None, chunksize=chunk_size):
                matching = chunk[chunk[0].isin(labeled_tx_ids)]
                if not matching.empty:
                    feature_chunks.append(matching)

            features_df = pd.concat(feature_chunks, ignore_index=True)
            features_df.rename(columns={0: "txId", 1: "time_step"}, inplace=True)

            merged = pd.merge(features_df, labeled_classes[["txId", "mapped_label"]], on="txId", how="inner")
            # Save cache for fast subsequent runs
            merged.to_csv(self.cache_path, index=False)

        if max_rows and len(merged) > max_rows:
            # Sample proportionately across all time steps
            merged = merged.groupby("time_step", group_keys=False).apply(
                lambda x: x.sample(frac=min(1.0, max_rows / len(merged)), random_state=42)
            )

        tx_ids = merged["txId"]
        time_steps = merged["time_step"]
        y = merged["mapped_label"]

        feature_cols = [c for c in merged.columns if str(c) not in ["txId", "time_step", "mapped_label", "class"]]
        X = merged[feature_cols].copy()
        X.fillna(0.0, inplace=True)

        return X, y, time_steps, tx_ids
