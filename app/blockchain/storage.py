import json
import logging
from typing import Optional, Any
from backend.app.blockchain.block import TraceChainBlock
from backend.app.blockchain.chain import TraceChain
from backend.app.mongodb import get_database
from backend.app.config import settings

logger = logging.getLogger(__name__)

class TraceChainStorage:
    """
    Persists TraceChain blocks to MongoDB Atlas and reconstructs the chain on application restart.

    CRITICAL DESIGN NOTE:
    load_or_init_chain() mutates the module-level global_chain singleton's .chain list
    in-place so that ALL references throughout the application (health endpoint, chain API,
    case_service, live_analysis_service, and test fixtures) see the same updated chain state
    without requiring individual re-imports or reassignment.
    """

    @staticmethod
    def load_or_init_chain(db: Optional[Any] = None) -> TraceChain:
        if db is None:
            db = get_database()

        # Build a local chain to reconstruct or initialize
        chain_instance = TraceChain(difficulty=settings.TRACECHAIN_DIFFICULTY)

        cursor = db.tracechain_blocks.find().sort("block_index", 1)
        records = list(cursor)

        if records:
            # Reconstruct chain from persisted MongoDB records
            chain_instance.chain = []
            for rec in records:
                b_idx = rec["block_index"]
                if b_idx != len(chain_instance.chain):
                    # Index gap detected — stop reconstruction here
                    logger.warning(f"TraceChain index gap detected at {b_idx} (expected {len(chain_instance.chain)}).")
                    break

                raw_payload = rec.get("payload")
                if raw_payload is None and "payload_json" in rec:
                    try:
                        raw_payload = json.loads(rec["payload_json"])
                    except Exception:
                        raw_payload = {}

                block = TraceChainBlock(
                    index=rec["block_index"],
                    timestamp=rec["block_timestamp"],
                    previous_hash=rec["previous_hash"],
                    event_type=rec["event_type"],
                    payload=raw_payload or {},
                    nonce=rec["nonce"],
                    difficulty=rec["difficulty"],
                    case_id=rec.get("case_id"),
                    block_hash=rec.get("block_hash") or rec.get("hash"),
                )
                chain_instance.chain.append(block)
        else:
            # No records yet — persist the newly-mined genesis block
            genesis = chain_instance.chain[0]
            doc = {
                "_id": genesis.index,
                "block_index": genesis.index,
                "block_timestamp": genesis.timestamp,
                "previous_hash": genesis.previous_hash,
                "nonce": genesis.nonce,
                "difficulty": genesis.difficulty,
                "block_hash": genesis.hash,
                "event_type": genesis.event_type,
                "case_id": genesis.case_id,
                "payload": genesis.payload,
                "payload_json": json.dumps(genesis.payload)
            }
            db.tracechain_blocks.update_one({"_id": genesis.index}, {"$set": doc}, upsert=True)

        # Mutate global_chain singleton in-place
        global_chain.chain = chain_instance.chain
        global_chain.difficulty = chain_instance.difficulty
        return global_chain

    @staticmethod
    def persist_block(block: TraceChainBlock, db: Optional[Any] = None) -> None:
        if db is None:
            db = get_database()

        doc = {
            "_id": block.index,
            "block_index": block.index,
            "block_timestamp": block.timestamp,
            "previous_hash": block.previous_hash,
            "nonce": block.nonce,
            "difficulty": block.difficulty,
            "block_hash": block.hash,
            "event_type": block.event_type,
            "case_id": block.case_id,
            "payload": block.payload,
            "payload_json": json.dumps(block.payload)
        }
        db.tracechain_blocks.update_one({"_id": block.index}, {"$set": doc}, upsert=True)


# ── Global Singleton ────────────────────────────────────────────────────────────
global_chain = TraceChain(difficulty=settings.TRACECHAIN_DIFFICULTY)
