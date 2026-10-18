import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from backend.app.mongodb import get_database, get_db as get_mongo_db, mongo_manager

class CaseModel:
    """Document model for Investigation Cases in MongoDB."""
    def __init__(
        self,
        case_id: str = "",
        case_name: str = "",
        description: Optional[str] = None,
        network: str = "simulated",
        data_source: str = "synthetic_ghost_attack",
        status: str = "created",
        seed_addresses: Optional[List[str]] = None,
        seed_addresses_json: Optional[str] = None,
        tx_count: int = 0,
        evidence_count: int = 0,
        summary: Optional[Dict[str, Any]] = None,
        summary_json: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        _id: Optional[str] = None,
        **kwargs
    ):
        self._id = _id or case_id
        self.case_id = case_id or str(self._id)
        self.case_name = case_name
        self.description = description
        self.network = network.value if hasattr(network, "value") else str(network)
        self.data_source = data_source
        self.status = status
        self.tx_count = tx_count
        self.evidence_count = evidence_count
        now_iso = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now_iso
        self.updated_at = updated_at or now_iso

        # Handle seed addresses list & json string
        if seed_addresses is not None:
            self.seed_addresses = seed_addresses
        elif seed_addresses_json:
            try:
                self.seed_addresses = json.loads(seed_addresses_json)
            except Exception:
                self.seed_addresses = []
        else:
            self.seed_addresses = []

        # Handle summary dict & json string
        if summary is not None:
            self.summary = summary
        elif summary_json:
            try:
                self.summary = json.loads(summary_json)
            except Exception:
                self.summary = None
        else:
            self.summary = None

    @property
    def seed_addresses_json(self) -> str:
        return json.dumps(self.seed_addresses)

    @seed_addresses_json.setter
    def seed_addresses_json(self, val: str):
        try:
            self.seed_addresses = json.loads(val) if val else []
        except Exception:
            self.seed_addresses = []

    @property
    def summary_json(self) -> Optional[str]:
        return json.dumps(self.summary) if self.summary is not None else None

    @summary_json.setter
    def summary_json(self, val: Optional[str]):
        try:
            self.summary = json.loads(val) if val else None
        except Exception:
            self.summary = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.case_id,
            "case_id": self.case_id,
            "case_name": self.case_name,
            "description": self.description,
            "network": self.network,
            "data_source": self.data_source,
            "status": self.status,
            "seed_addresses": self.seed_addresses,
            "tx_count": self.tx_count,
            "evidence_count": self.evidence_count,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class TransactionModel:
    """Document model for Normalized Transactions in MongoDB."""
    def __init__(
        self,
        tx_id: str = "",
        case_id: str = "",
        network: str = "simulated",
        data_origin: str = "synthetic",
        timestamp: str = "",
        from_address: str = "",
        to_address: str = "",
        amount: float = 0.0,
        asset: str = "SIM-ETH",
        block_number: Optional[int] = None,
        tx_hash: Optional[str] = None,
        fee: float = 0.0,
        log_index: Optional[int] = None,
        is_reorg_removed: bool = False,
        extra_metadata: Optional[Dict[str, Any]] = None,
        extra_metadata_json: Optional[str] = None,
        _id: Optional[str] = None,
        **kwargs
    ):
        self._id = _id or f"{case_id}:{tx_id}"
        self.tx_id = tx_id
        self.case_id = case_id
        self.network = network.value if hasattr(network, "value") else str(network)
        self.data_origin = data_origin.value if hasattr(data_origin, "value") else str(data_origin)
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.from_address = from_address
        self.to_address = to_address
        self.amount = float(amount)
        self.asset = asset
        self.block_number = block_number
        self.tx_hash = tx_hash
        self.fee = float(fee or 0.0)
        self.log_index = log_index
        self.is_reorg_removed = bool(is_reorg_removed)

        if extra_metadata is not None:
            self.extra_metadata = extra_metadata
        elif extra_metadata_json:
            try:
                self.extra_metadata = json.loads(extra_metadata_json)
            except Exception:
                self.extra_metadata = {}
        else:
            self.extra_metadata = {}

    @property
    def extra_metadata_json(self) -> str:
        return json.dumps(self.extra_metadata)

    @extra_metadata_json.setter
    def extra_metadata_json(self, val: str):
        try:
            self.extra_metadata = json.loads(val) if val else {}
        except Exception:
            self.extra_metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": f"{self.case_id}:{self.tx_id}",
            "tx_id": self.tx_id,
            "case_id": self.case_id,
            "network": self.network,
            "data_origin": self.data_origin,
            "timestamp": self.timestamp,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "amount": self.amount,
            "asset": self.asset,
            "block_number": self.block_number,
            "tx_hash": self.tx_hash,
            "fee": self.fee,
            "log_index": self.log_index,
            "is_reorg_removed": self.is_reorg_removed,
            "extra_metadata": self.extra_metadata
        }

class EvidenceModel:
    """Document model for Forensic Evidence items in MongoDB."""
    def __init__(
        self,
        evidence_id: str = "",
        case_id: str = "",
        indicator_type: str = "",
        indicator_value: str = "",
        category: str = "",
        subcategory: Optional[str] = None,
        description: Optional[str] = None,
        source_name: str = "",
        source_url: Optional[str] = None,
        provenance: str = "",
        created_at: Optional[str] = None,
        _id: Optional[str] = None,
        **kwargs
    ):
        self._id = _id or f"{case_id}:{evidence_id}"
        self.evidence_id = evidence_id
        self.case_id = case_id
        self.indicator_type = indicator_type
        self.indicator_value = indicator_value
        self.category = category
        self.subcategory = subcategory
        self.description = description
        self.source_name = source_name
        self.source_url = source_url
        self.provenance = provenance
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": f"{self.case_id}:{self.evidence_id}",
            "evidence_id": self.evidence_id,
            "case_id": self.case_id,
            "indicator_type": self.indicator_type,
            "indicator_value": self.indicator_value,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "provenance": self.provenance,
            "created_at": self.created_at
        }

class TraceChainBlockModel:
    """Document model for TraceChain Blocks in MongoDB."""
    def __init__(
        self,
        block_index: int = 0,
        block_timestamp: str = "",
        previous_hash: str = "",
        nonce: int = 0,
        difficulty: int = 2,
        block_hash: str = "",
        event_type: str = "",
        case_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        payload_json: Optional[str] = None,
        _id: Optional[int] = None,
        **kwargs
    ):
        self._id = _id if _id is not None else block_index
        self.block_index = block_index
        self.block_timestamp = block_timestamp or datetime.now(timezone.utc).isoformat()
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.difficulty = difficulty
        self.block_hash = block_hash
        self.event_type = event_type
        self.case_id = case_id

        if payload is not None:
            self.payload = payload
        elif payload_json:
            try:
                self.payload = json.loads(payload_json)
            except Exception:
                self.payload = {}
        else:
            self.payload = {}

    @property
    def payload_json(self) -> str:
        return json.dumps(self.payload)

    @payload_json.setter
    def payload_json(self, val: str):
        try:
            self.payload = json.loads(val) if val else {}
        except Exception:
            self.payload = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.block_index,
            "block_index": self.block_index,
            "block_timestamp": self.block_timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "block_hash": self.block_hash,
            "event_type": self.event_type,
            "case_id": self.case_id,
            "payload": self.payload
        }

class BlockCursorModel:
    """Document model for Ingestion Checkpoints (Block Cursors) in MongoDB."""
    def __init__(
        self,
        network: str = "",
        last_processed_block: int = 0,
        last_processed_block_hash: Optional[str] = None,
        updated_at: Optional[str] = None,
        _id: Optional[str] = None,
        **kwargs
    ):
        self._id = _id or network
        self.network = network or str(self._id)
        self.last_processed_block = last_processed_block
        self.last_processed_block_hash = last_processed_block_hash
        self.updated_at = updated_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.network,
            "network": self.network,
            "last_processed_block": self.last_processed_block,
            "last_processed_block_hash": self.last_processed_block_hash,
            "updated_at": self.updated_at
        }

class RawBlockchainEventModel:
    """Document model for Raw Ingested Events in MongoDB."""
    def __init__(
        self,
        event_id: str = "",
        chain_id: int = 1,
        network: str = "ethereum",
        event_type: str = "native_transaction",
        block_number: Optional[int] = None,
        block_hash: Optional[str] = None,
        tx_hash: Optional[str] = None,
        log_index: Optional[int] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
        raw_payload_json: Optional[str] = None,
        received_at: Optional[str] = None,
        _id: Optional[str] = None,
        **kwargs
    ):
        self._id = _id or event_id
        self.event_id = event_id or str(self._id)
        self.chain_id = chain_id
        self.network = network
        self.event_type = event_type
        self.block_number = block_number
        self.block_hash = block_hash
        self.tx_hash = tx_hash
        self.log_index = log_index
        self.received_at = received_at or datetime.now(timezone.utc).isoformat()

        if raw_payload is not None:
            self.raw_payload = raw_payload
        elif raw_payload_json:
            try:
                self.raw_payload = json.loads(raw_payload_json)
            except Exception:
                self.raw_payload = {}
        else:
            self.raw_payload = {}

    @property
    def raw_payload_json(self) -> str:
        return json.dumps(self.raw_payload)

    @raw_payload_json.setter
    def raw_payload_json(self, val: str):
        try:
            self.raw_payload = json.loads(val) if val else {}
        except Exception:
            self.raw_payload = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.event_id,
            "event_id": self.event_id,
            "chain_id": self.chain_id,
            "network": self.network,
            "event_type": self.event_type,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "tx_hash": self.tx_hash,
            "log_index": self.log_index,
            "raw_payload": self.raw_payload,
            "received_at": self.received_at
        }

class OSINTSourceRecordModel:
    """Document model for OSINT Sources in MongoDB."""
    def __init__(
        self,
        source_id: str = "",
        source_name: str = "",
        source_url: Optional[str] = None,
        content_hash: Optional[str] = None,
        last_collected_at: Optional[str] = None,
        status: str = "cached",
        records_count: int = 0,
        cache_payload: Optional[Dict[str, Any]] = None,
        cache_payload_json: Optional[str] = None,
        _id: Optional[str] = None,
        **kwargs
    ):
        self._id = _id or source_id
        self.source_id = source_id or str(self._id)
        self.source_name = source_name
        self.source_url = source_url
        self.content_hash = content_hash
        self.last_collected_at = last_collected_at
        self.status = status
        self.records_count = records_count

        if cache_payload is not None:
            self.cache_payload = cache_payload
        elif cache_payload_json:
            try:
                self.cache_payload = json.loads(cache_payload_json)
            except Exception:
                self.cache_payload = None
        else:
            self.cache_payload = None

    @property
    def cache_payload_json(self) -> Optional[str]:
        return json.dumps(self.cache_payload) if self.cache_payload is not None else None

    @cache_payload_json.setter
    def cache_payload_json(self, val: Optional[str]):
        try:
            self.cache_payload = json.loads(val) if val else None
        except Exception:
            self.cache_payload = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.source_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "content_hash": self.content_hash,
            "last_collected_at": self.last_collected_at,
            "status": self.status,
            "records_count": self.records_count,
            "cache_payload": self.cache_payload
        }

class MLModelRecordModel:
    """Document model for ML Model Registry in MongoDB."""
    def __init__(
        self,
        model_id: str = "",
        model_name: str = "",
        version: str = "",
        network: str = "",
        algorithm: str = "",
        trained_at: str = "",
        metrics: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        file_path: str = "",
        is_active: bool = True,
        _id: Optional[str] = None,
        **kwargs
    ):
        self._id = _id or model_id
        self.model_id = model_id or str(self._id)
        self.model_name = model_name
        self.version = version
        self.network = network
        self.algorithm = algorithm
        self.trained_at = trained_at
        self.metrics = metrics or {}
        self.parameters = parameters or {}
        self.file_path = file_path
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.model_id,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "version": self.version,
            "network": self.network,
            "algorithm": self.algorithm,
            "trained_at": self.trained_at,
            "metrics": self.metrics,
            "parameters": self.parameters,
            "file_path": self.file_path,
            "is_active": self.is_active
        }

class DatabaseSessionWrapper:
    """
    Backward-compatibility wrapper around a MongoDB Database instance.
    Provides .add(), .commit(), .close(), and .query() helpers so existing test fixtures
    and scripts transition to MongoDB seamlessly.
    """
    def __init__(self, db=None):
        self._db = db if db is not None else get_database()

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __getitem__(self, item):
        return self._db[item]

    def add(self, model):
        doc = model.to_dict() if hasattr(model, "to_dict") else dict(model)
        doc_id = doc.get("_id")
        if isinstance(model, CaseModel):
            self._db.cases.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
        elif isinstance(model, TransactionModel):
            self._db.transactions.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
        elif isinstance(model, EvidenceModel):
            self._db.evidence.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
        elif isinstance(model, TraceChainBlockModel):
            self._db.tracechain_blocks.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
        elif isinstance(model, BlockCursorModel):
            self._db.block_cursors.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
        elif isinstance(model, RawBlockchainEventModel):
            self._db.raw_blockchain_events.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
        elif isinstance(model, OSINTSourceRecordModel):
            self._db.osint_sources.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)

    def commit(self):
        pass

    def close(self):
        pass

    def query(self, model_cls):
        class QueryHelper:
            def __init__(self, db, cls):
                self._db = db
                self._cls = cls
                self._filter = {}
                name_map = {
                    "CaseModel": "cases",
                    "TransactionModel": "transactions",
                    "EvidenceModel": "evidence",
                    "TraceChainBlockModel": "tracechain_blocks",
                    "BlockCursorModel": "block_cursors",
                    "RawBlockchainEventModel": "raw_blockchain_events",
                    "OSINTSourceRecordModel": "osint_sources"
                }
                self._coll_name = name_map.get(cls.__name__, cls.__name__.lower())

            def filter_by(self, **kwargs):
                self._filter = kwargs
                return self

            def first(self):
                doc = self._db[self._coll_name].find_one(self._filter)
                return self._cls(**doc) if doc else None

            def all(self):
                cursor = self._db[self._coll_name].find(self._filter)
                return [self._cls(**d) for d in cursor]

        return QueryHelper(self._db, model_cls)

def SessionLocal():
    """Compatibility factory returning active MongoDB DatabaseSessionWrapper."""
    return DatabaseSessionWrapper()

def init_db():
    """Initializes MongoDB database and ensures collections and indexes exist."""
    mongo_manager.create_indexes()

def get_db():
    """FastAPI dependency yielding MongoDB database handle."""
    yield get_database()
