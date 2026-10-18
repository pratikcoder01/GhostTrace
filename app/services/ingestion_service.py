import json
import logging
from typing import List, Dict, Any, Tuple

from backend.app.schemas import (
    TransactionRecord, NetworkType, DataOrigin, OSINTIndicator
)
from backend.app.database import TransactionModel, EvidenceModel
from backend.app.adapters.synthetic import SyntheticAttackAdapter
from backend.app.adapters.elliptic import EllipticDatasetAdapter
from backend.app.adapters.ethereum import EthereumAdapter
from backend.app.services.osint_service import osint_service

logger = logging.getLogger(__name__)

class IngestionService:
    """
    Ingestion service responsible for bounded loading, schema validation,
    duplicate suppression, network boundary enforcement, and database persistence.
    """
    def __init__(self):
        self.synthetic_adapter = SyntheticAttackAdapter()
        self.elliptic_adapter = EllipticDatasetAdapter()
        self.ethereum_adapter = EthereumAdapter()

    def ingest_case_data(
        self,
        case_id: str,
        network: NetworkType,
        data_source: str,
        seed_addresses: List[str],
        db: Any
    ) -> Tuple[int, int, List[str]]:
        """
        Ingests transactions and correlating evidence for a specific case.
        Returns: (inserted_tx_count, inserted_evidence_count, error_log)
        """
        error_log: List[str] = []
        raw_txs: List[TransactionRecord] = []
        planted_indicators: List[OSINTIndicator] = []

        # 1. Route by data_source while enforcing network compatibility
        if data_source == "synthetic_ghost_attack":
            if network != NetworkType.SIMULATED:
                error_log.append(f"Network mismatch: synthetic_ghost_attack is strictly for 'simulated' network, not '{network.value}'")
            txs, errs = self.synthetic_adapter.get_transactions()
            raw_txs.extend(txs)
            error_log.extend(errs)
            planted_indicators.extend(self.synthetic_adapter.get_planted_osint())

        elif data_source == "elliptic":
            if network != NetworkType.BITCOIN:
                error_log.append(f"Network mismatch: Elliptic benchmark is strictly for 'bitcoin', not '{network.value}'")
            if not self.elliptic_adapter.is_available():
                error_log.append("Elliptic dataset files not found on disk.")
            else:
                try:
                    edgelist = self.elliptic_adapter.load_edgelist(max_edges=500)
                    for idx, row in edgelist.iterrows():
                        raw_txs.append(
                            TransactionRecord(
                                tx_id=f"btc_edge_{row['txId1']}_{row['txId2']}",
                                network=NetworkType.BITCOIN,
                                data_origin=DataOrigin.ELLIPTIC_BENCHMARK,
                                timestamp="2026-01-01T00:00:00Z",
                                from_address=str(row["txId1"]),
                                to_address=str(row["txId2"]),
                                amount=1.0,
                                asset="BTC",
                                block_number=1,
                                extra_metadata={"dataset": "elliptic"}
                            )
                        )
                except Exception as e:
                    error_log.append(f"Error reading Elliptic edgelist: {str(e)}")

        elif data_source == "ethereum_etherscan":
            if network != NetworkType.ETHEREUM:
                error_log.append(f"Network mismatch: Etherscan adapter is strictly for 'ethereum', not '{network.value}'")
            # Note: asynchronous live fetching is performed via async adapter when configured
            error_log.append("Live Ethereum ingestion mode initialized (read-only).")

        else:
            error_log.append(f"Unknown data_source '{data_source}'")

        # 2. Duplicate Detection and DB Persistence
        existing_tx_ids = set(db.transactions.distinct("tx_id", {"case_id": case_id}))

        inserted_tx_count = 0
        for tx in raw_txs:
            # Enforce network isolation: Never store mismatched networks in a single case
            if tx.network != network:
                error_log.append(f"Network separation violation: skipping tx '{tx.tx_id}' on '{tx.network}' for case on '{network}'")
                continue

            if tx.tx_id in existing_tx_ids:
                error_log.append(f"Duplicate transaction skipped: {tx.tx_id}")
                continue

            existing_tx_ids.add(tx.tx_id)
            doc = {
                "_id": f"{case_id}:{tx.tx_id}",
                "tx_id": tx.tx_id,
                "case_id": case_id,
                "network": tx.network.value if hasattr(tx.network, "value") else str(tx.network),
                "data_origin": tx.data_origin.value if hasattr(tx.data_origin, "value") else str(tx.data_origin),
                "timestamp": tx.timestamp,
                "from_address": tx.from_address,
                "to_address": tx.to_address,
                "amount": float(tx.amount),
                "asset": tx.asset,
                "block_number": tx.block_number,
                "tx_hash": tx.tx_hash,
                "fee": float(tx.fee or 0.0),
                "extra_metadata": tx.extra_metadata or {}
            }
            db.transactions.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
            inserted_tx_count += 1

        # 3. Correlate and Persist Evidence
        inserted_evidence_count = 0
        existing_evidence_ids = set(db.evidence.distinct("evidence_id", {"case_id": case_id}))

        # Correlate all involved addresses with OSINT
        involved_addresses = set(seed_addresses)
        for tx in raw_txs:
            involved_addresses.add(tx.from_address)
            involved_addresses.add(tx.to_address)

        for addr in involved_addresses:
            matches = osint_service.correlate_address(addr)
            for m in matches:
                evid_item = osint_service.create_evidence_item(case_id, m)
                if evid_item.evidence_id not in existing_evidence_ids:
                    existing_evidence_ids.add(evid_item.evidence_id)
                    ev_doc = {
                        "_id": f"{case_id}:{evid_item.evidence_id}",
                        "evidence_id": evid_item.evidence_id,
                        "case_id": case_id,
                        "indicator_type": evid_item.indicator_type,
                        "indicator_value": evid_item.indicator_value,
                        "category": evid_item.category,
                        "subcategory": evid_item.subcategory,
                        "description": evid_item.description,
                        "source_name": evid_item.source_name,
                        "source_url": evid_item.source_url,
                        "provenance": evid_item.provenance,
                        "created_at": evid_item.created_at
                    }
                    db.evidence.update_one({"_id": ev_doc["_id"]}, {"$set": ev_doc}, upsert=True)
                    inserted_evidence_count += 1

        return inserted_tx_count, inserted_evidence_count, error_log

ingestion_service = IngestionService()
