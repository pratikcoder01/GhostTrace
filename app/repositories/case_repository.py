import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from backend.app.database import CaseModel, TransactionModel, EvidenceModel
from backend.app.schemas import CaseCreate

class CaseRepository:
    """
    Data access repository for cases, transactions, and evidence backed by MongoDB.
    """
    def __init__(self, db):
        # db can be a MongoDB Database instance or DatabaseSessionWrapper
        self.db = db

    def create_case(self, case_id: str, case_in: CaseCreate) -> CaseModel:
        now_iso = datetime.now(timezone.utc).isoformat()
        doc = {
            "_id": case_id,
            "case_id": case_id,
            "case_name": case_in.case_name,
            "description": case_in.description,
            "network": case_in.network.value if hasattr(case_in.network, "value") else str(case_in.network),
            "data_source": case_in.data_source,
            "status": "created",
            "seed_addresses": case_in.seed_addresses,
            "tx_count": 0,
            "evidence_count": 0,
            "summary": None,
            "created_at": now_iso,
            "updated_at": now_iso
        }
        self.db.cases.update_one({"_id": case_id}, {"$set": doc}, upsert=True)
        return CaseModel(**doc)

    def get_case(self, case_id: str) -> Optional[CaseModel]:
        doc = self.db.cases.find_one({"$or": [{"_id": case_id}, {"case_id": case_id}]})
        if not doc:
            return None
        return CaseModel(**doc)

    def list_cases(self, limit: int = 100, skip: int = 0) -> List[CaseModel]:
        cursor = self.db.cases.find().sort("created_at", -1).skip(skip).limit(limit)
        return [CaseModel(**doc) for doc in cursor]

    def update_status(
        self,
        case_id: str,
        status: str,
        tx_count: Optional[int] = None,
        evidence_count: Optional[int] = None,
        summary: Optional[Dict[str, Any]] = None
    ) -> Optional[CaseModel]:
        now_iso = datetime.now(timezone.utc).isoformat()
        update_fields: Dict[str, Any] = {
            "status": status,
            "updated_at": now_iso
        }
        if tx_count is not None:
            update_fields["tx_count"] = tx_count
        if evidence_count is not None:
            update_fields["evidence_count"] = evidence_count
        if summary is not None:
            update_fields["summary"] = summary

        res = self.db.cases.update_one(
            {"$or": [{"_id": case_id}, {"case_id": case_id}]},
            {"$set": update_fields}
        )
        return self.get_case(case_id)

    def get_transactions(self, case_id: str) -> List[TransactionModel]:
        cursor = self.db.transactions.find({"case_id": case_id}).sort("timestamp", 1)
        return [TransactionModel(**doc) for doc in cursor]

    def get_evidence(self, case_id: str) -> List[EvidenceModel]:
        cursor = self.db.evidence.find({"case_id": case_id})
        return [EvidenceModel(**doc) for doc in cursor]
