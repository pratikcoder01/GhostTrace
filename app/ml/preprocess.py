from typing import Tuple, Dict, Any, Optional, List
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from backend.app.adapters.elliptic import EllipticDatasetAdapter
from backend.app.config import settings

class MLPreprocessor:
    """
    Reproducible preprocessing pipeline for blockchain illicit transaction detection.
    Enforces strict chronological train/validation/test splitting and fits transformations
    strictly on the training partition to eliminate target leakage.
    """
    def __init__(self, train_cutoff: int = 28, val_cutoff: int = 34):
        self.train_cutoff = train_cutoff
        self.val_cutoff = val_cutoff
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_fitted = False

    def load_full_dataset(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """Loads all labeled transactions (46,564) without row truncation."""
        adapter = EllipticDatasetAdapter()
        X_df, y_ser, time_steps, tx_ids = adapter.load_features_and_labels(
            max_rows=None,
            exclude_unknown=True
        )
        self.feature_names = [f"feature_{col}" for col in X_df.columns]
        return X_df, y_ser, time_steps, tx_ids

    def load_and_split_3way(
        self
    ) -> Dict[str, Any]:
        """
        Splits data chronologically into 3 distinct, non-overlapping partitions:
        - Train:      time_step <= 28 (Steps 1–28)
        - Validation: 28 < time_step <= 34 (Steps 29–34)
        - Test:       time_step > 34 (Steps 35–49, official benchmark test split)
        
        Scaler is fitted strictly on the Train partition.
        """
        X_df, y_ser, time_steps, tx_ids = self.load_full_dataset()

        train_mask = time_steps <= self.train_cutoff
        val_mask = (time_steps > self.train_cutoff) & (time_steps <= self.val_cutoff)
        test_mask = time_steps > self.val_cutoff

        X_train_raw = X_df[train_mask].to_numpy()
        y_train = y_ser[train_mask].to_numpy()

        X_val_raw = X_df[val_mask].to_numpy()
        y_val = y_ser[val_mask].to_numpy()

        X_test_raw = X_df[test_mask].to_numpy()
        y_test = y_ser[test_mask].to_numpy()

        # Fit scaler ONLY on train
        X_train = self.scaler.fit_transform(X_train_raw)
        X_val = self.scaler.transform(X_val_raw)
        X_test = self.scaler.transform(X_test_raw)
        self.is_fitted = True

        return {
            "X_train": X_train,
            "y_train": y_train,
            "tx_ids_train": tx_ids[train_mask],
            "time_steps_train": time_steps[train_mask],
            "X_val": X_val,
            "y_val": y_val,
            "tx_ids_val": tx_ids[val_mask],
            "time_steps_val": time_steps[val_mask],
            "X_test": X_test,
            "y_test": y_test,
            "tx_ids_test": tx_ids[test_mask],
            "time_steps_test": time_steps[test_mask],
            "feature_names": self.feature_names
        }

    def load_and_split_elliptic(
        self,
        max_rows: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.Series, pd.Series]:
        """
        Standard 2-way chronological split:
        Train: time_step <= 34 (Steps 1–34)
        Test:  time_step > 34  (Steps 35–49)
        Preserves backward compatibility with existing tests.
        """
        adapter = EllipticDatasetAdapter()
        X_df, y_ser, time_steps, tx_ids = adapter.load_features_and_labels(
            max_rows=max_rows,
            exclude_unknown=True
        )
        self.feature_names = [f"feature_{col}" for col in X_df.columns]

        train_mask = time_steps <= self.val_cutoff
        test_mask = time_steps > self.val_cutoff

        X_train_df = X_df[train_mask]
        y_train = y_ser[train_mask].to_numpy()

        X_test_df = X_df[test_mask]
        y_test = y_ser[test_mask].to_numpy()

        X_train = self.scaler.fit_transform(X_train_df.to_numpy())
        X_test = self.scaler.transform(X_test_df.to_numpy())
        self.is_fitted = True

        return X_train, y_train, X_test, y_test, tx_ids[train_mask], tx_ids[test_mask]

    def transform_single(self, raw_features: list) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Preprocessor has not been fitted.")
        arr = np.array(raw_features, dtype=float).reshape(1, -1)
        return self.scaler.transform(arr)
