import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.schemas import OSINTIndicator, EvidenceItem
from backend.app.adapters.cryptoscamdb import CryptoScamDBAdapter
from backend.app.adapters.synthetic import SyntheticAttackAdapter
from backend.app.config import settings

class OSINTService:
    """
    OSINT intelligence aggregation and correlation service.
    Indexes indicators from CryptoScamDB, Pegasus IOC feeds, and simulated fixtures.
    Enforces exact matching, source validation, and clear evidence references.
    """
    def __init__(self):
        self.csdb_adapter = CryptoScamDBAdapter()
        self.synthetic_adapter = SyntheticAttackAdapter()
        self._indicators: List[OSINTIndicator] = []
        self._address_map: Dict[str, List[OSINTIndicator]] = {}
        self._domain_map: Dict[str, List[OSINTIndicator]] = {}
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        
        # 1. Load CryptoScamDB indicators
        csdb_inds = self.csdb_adapter.load_indicators(max_records=10000)
        self._indicators.extend(csdb_inds)

        # 2. Load Planted Synthetic indicators
        try:
            synthetic_inds = self.synthetic_adapter.get_planted_osint()
            self._indicators.extend(synthetic_inds)
        except Exception:
            pass

        # 3. Load Pegasus dataset IOC indicators if file exists
        self._load_pegasus_iocs()

        # Build lookup indices
        for ind in self._indicators:
            val = ind.indicator_value.strip()
            norm_addr = val.lower() if val.startswith("0x") else val
            if norm_addr not in self._address_map:
                self._address_map[norm_addr] = []
            self._address_map[norm_addr].append(ind)

            if ind.indicator_type in ("domain", "url"):
                domain_key = val.lower()
                if domain_key not in self._domain_map:
                    self._domain_map[domain_key] = []
                self._domain_map[domain_key].append(ind)

        self._initialized = True

    def _load_pegasus_iocs(self):
        pegasus_csv = settings.PEGASUS_CSV_FILE
        if not pegasus_csv.exists():
            return
        
        try:
            with open(pegasus_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                seen_iocs = set()
                for idx, row in enumerate(reader):
                    ioc = row.get("ioc", "").strip()
                    if ioc and ioc != "None" and ioc not in seen_iocs:
                        seen_iocs.add(ioc)
                        dest_ip = row.get("destination_ip", "").strip()
                        self._indicators.append(
                            OSINTIndicator(
                                indicator_id=f"PEG-IOC-{len(seen_iocs):03d}",
                                indicator_type="ioc_signature",
                                indicator_value=f"{ioc} (Target IP: {dest_ip})",
                                network=None,
                                category="Cyber Intrusion / Pegasus",
                                subcategory="Mobile Malware Telemetry",
                                description=f"Anomaly: {row.get('anomaly_detected')} during process: {row.get('process')}",
                                source_name="Synthetic Pegasus Threat Telemetry",
                                source_url="https://threat-intel.local/pegasus-dataset",
                                first_seen=row.get("timestamp"),
                                retrieved_at="2026-10-18T00:00:00Z",
                                provenance="Synthetic Pegasus Threat Telemetry Fixture"
                            )
                        )
        except Exception:
            pass

    def correlate_address(self, address: str) -> List[OSINTIndicator]:
        """Performs exact case-normalized address lookup against threat intelligence index."""
        self.initialize()
        val = address.strip()
        norm_key = val.lower() if val.startswith("0x") else val
        return self._address_map.get(norm_key, [])

    def correlate_domain(self, domain: str) -> List[OSINTIndicator]:
        self.initialize()
        return self._domain_map.get(domain.strip().lower(), [])

    def create_evidence_item(self, case_id: str, indicator: OSINTIndicator) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=f"EVID-{case_id}-{indicator.indicator_id}",
            case_id=case_id,
            indicator_type=indicator.indicator_type,
            indicator_value=indicator.indicator_value,
            category=indicator.category,
            subcategory=indicator.subcategory,
            description=indicator.description,
            source_name=indicator.source_name,
            source_url=indicator.source_url,
            provenance=indicator.provenance,
            created_at=indicator.retrieved_at
        )

# Global singleton
osint_service = OSINTService()
