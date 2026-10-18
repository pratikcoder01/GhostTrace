import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.schemas import OSINTIndicator
from backend.app.config import settings

class CryptoScamDBAdapter:
    """
    Adapter for CryptoScamDB threat intelligence dataset.
    Provides address matching and scam categorization with source provenance.
    """
    def __init__(self, snapshot_file: Path = settings.CRYPTOSCAMDB_FILE):
        self.snapshot_file = snapshot_file
        self._indicators_cache: Optional[List[OSINTIndicator]] = None
        self._address_index: Dict[str, List[OSINTIndicator]] = {}

    def load_indicators(self, max_records: int = 10000) -> List[OSINTIndicator]:
        if self._indicators_cache is not None:
            return self._indicators_cache

        indicators: List[OSINTIndicator] = []
        if not self.snapshot_file.exists():
            return indicators

        with open(self.snapshot_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_addresses = data.get("addresses", [])
        for idx, item in enumerate(raw_addresses[:max_records]):
            val = str(item.get("value", "")).strip()
            if not val:
                continue
            
            indicator = OSINTIndicator(
                indicator_id=f"CSDB-{idx+1:06d}",
                indicator_type=item.get("type", "address"),
                indicator_value=val,
                network=item.get("network"),
                category=item.get("category", "Scam"),
                subcategory=item.get("subcategory"),
                description=item.get("description"),
                source_name="CryptoScamDB",
                source_url=f"https://cryptoscamdb.org/search?q={val}",
                first_seen=None,
                retrieved_at="2026-10-18T00:00:00Z",
                provenance="CryptoScamDB Local Verified Snapshot"
            )
            indicators.append(indicator)
            
            # Index for fast O(1) address lookup
            norm_key = val.lower() if val.startswith("0x") else val
            if norm_key not in self._address_index:
                self._address_index[norm_key] = []
            self._address_index[norm_key].append(indicator)

        self._indicators_cache = indicators
        return indicators

    def query_address(self, address: str) -> List[OSINTIndicator]:
        """Looks up an address in the CryptoScamDB index."""
        if self._indicators_cache is None:
            self.load_indicators()
        norm_key = address.lower() if address.startswith("0x") else address
        return self._address_index.get(norm_key, [])
