import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.app.schemas import TransactionRecord, OSINTIndicator, NetworkType, DataOrigin
from backend.app.config import settings

class SyntheticAttackAdapter:
    """
    Adapter for deterministic synthetic Ghost Attacks forensic scenario.
    All data is strictly marked as simulated and synthetic.
    """
    def __init__(self, file_path: Path = settings.SYNTHETIC_ATTACK_FILE):
        self.file_path = file_path

    def load_scenario(self) -> Dict[str, Any]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Synthetic scenario fixture not found at {self.file_path}")
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_transactions(self) -> Tuple[List[TransactionRecord], List[str]]:
        """
        Parses and validates all synthetic transactions.
        Returns (valid_transactions, error_logs).
        """
        data = self.load_scenario()
        raw_txs = data.get("transactions", [])
        valid_txs: List[TransactionRecord] = []
        errors: List[str] = []

        seen_tx_ids = set()
        for idx, item in enumerate(raw_txs):
            try:
                tx_id = item.get("tx_id")
                if not tx_id:
                    errors.append(f"Row {idx}: missing required tx_id")
                    continue
                if tx_id in seen_tx_ids:
                    errors.append(f"Row {idx}: duplicate tx_id '{tx_id}' skipped")
                    continue
                seen_tx_ids.add(tx_id)

                tx = TransactionRecord(
                    tx_id=str(tx_id),
                    network=NetworkType.SIMULATED,
                    data_origin=DataOrigin.SYNTHETIC,
                    timestamp=item.get("timestamp", "2026-10-10T08:00:00Z"),
                    from_address=str(item.get("from_address")).strip(),
                    to_address=str(item.get("to_address")).strip(),
                    amount=float(item.get("amount", 0.0)),
                    asset=item.get("asset", "SIM-ETH"),
                    block_number=item.get("block_number"),
                    tx_hash=item.get("tx_hash"),
                    fee=float(item.get("fee", 0.0)),
                    extra_metadata=item.get("extra_metadata", {"simulated": True})
                )
                valid_txs.append(tx)
            except Exception as e:
                errors.append(f"Row {idx} validation error: {str(e)}")

        return valid_txs, errors

    def get_planted_osint(self) -> List[OSINTIndicator]:
        """
        Returns planted OSINT indicators linked to the simulated scenario.
        """
        data = self.load_scenario()
        raw_indicators = data.get("planted_osint", [])
        indicators: List[OSINTIndicator] = []

        for item in raw_indicators:
            try:
                ind = OSINTIndicator(
                    indicator_id=item["indicator_id"],
                    indicator_type=item["indicator_type"],
                    indicator_value=item["indicator_value"],
                    network=item.get("network", "simulated"),
                    category=item.get("category", "Simulated Threat"),
                    subcategory=item.get("subcategory"),
                    description=item.get("description"),
                    source_name=item.get("source_name", "Simulated Intelligence"),
                    source_url=item.get("source_url"),
                    first_seen=item.get("first_seen"),
                    last_seen=item.get("last_seen"),
                    retrieved_at=item.get("retrieved_at", "2026-10-10T08:00:00Z"),
                    provenance="Synthetic Benchmark Fixture"
                )
                indicators.append(ind)
            except Exception:
                continue

        return indicators
