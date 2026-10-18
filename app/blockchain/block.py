import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class TraceChainBlock:
    """
    A single immutable block in the TraceChain audit ledger.
    Uses canonical JSON serialization (sorted keys, compact delimiters) and SHA-256.
    """
    def __init__(
        self,
        index: int,
        timestamp: str,
        previous_hash: str,
        event_type: str,
        payload: Dict[str, Any],
        nonce: int = 0,
        difficulty: int = 2,
        case_id: Optional[str] = None,
        block_hash: Optional[str] = None
    ):
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.event_type = event_type
        self.payload = payload
        self.nonce = nonce
        self.difficulty = difficulty
        self.case_id = case_id
        self.hash = block_hash or self.compute_hash()

    def get_canonical_payload(self) -> str:
        """
        Produces deterministic, canonical JSON representation of block contents.
        """
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "event_type": self.event_type,
            "case_id": self.case_id,
            "payload": self.payload,
            "nonce": self.nonce,
            "difficulty": self.difficulty
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        """Computes SHA-256 hash over canonical payload."""
        canonical_str = self.get_canonical_payload()
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def mine(self) -> str:
        """
        Executes proof-of-work mining until hash meets target difficulty.
        Target difficulty: hash must start with '0' * difficulty.
        """
        target_prefix = "0" * self.difficulty
        while True:
            candidate_hash = self.compute_hash()
            if candidate_hash.startswith(target_prefix):
                self.hash = candidate_hash
                return self.hash
            self.nonce += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "event_type": self.event_type,
            "case_id": self.case_id,
            "payload": self.payload,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceChainBlock":
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            previous_hash=data["previous_hash"],
            event_type=data["event_type"],
            payload=data["payload"],
            nonce=data["nonce"],
            difficulty=data["difficulty"],
            case_id=data.get("case_id"),
            block_hash=data.get("hash")
        )
