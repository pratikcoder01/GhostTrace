from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from backend.app.blockchain.block import TraceChainBlock
from backend.app.config import settings

class TraceChain:
    """
    Custom audit-integrity blockchain for forensic chain-of-custody tracking.
    Guarantees tamper-evidence and sequential verification for investigation events.
    """
    def __init__(self, difficulty: Optional[int] = None):
        self.difficulty = difficulty if difficulty is not None else settings.TRACECHAIN_DIFFICULTY
        self.chain: List[TraceChainBlock] = []
        if not self.chain:
            self._create_genesis_block()

    def _create_genesis_block(self):
        """Creates and mines the canonical genesis block."""
        genesis_timestamp = "2026-01-01T00:00:00Z"
        genesis_payload = {
            "title": "GhostTrace Genesis Block",
            "message": "Forensic audit chain initialized. Zero-trust chain-of-custody ledger.",
            "version": settings.VERSION,
            "disclaimer": "TraceChain is a custom forensic audit mechanism, not public Ethereum."
        }
        genesis_block = TraceChainBlock(
            index=0,
            timestamp=genesis_timestamp,
            previous_hash="0" * 64,
            event_type="GENESIS",
            payload=genesis_payload,
            nonce=0,
            difficulty=self.difficulty,
            case_id=None
        )
        genesis_block.mine()
        self.chain.append(genesis_block)

    @property
    def latest_block(self) -> TraceChainBlock:
        return self.chain[-1]

    def mine_and_add_block(
        self,
        event_type: str,
        payload: Dict[str, Any],
        case_id: Optional[str] = None
    ) -> TraceChainBlock:
        """
        Creates, mines with PoW, and appends a new audit block.
        """
        new_index = len(self.chain)
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = self.latest_block.hash

        block = TraceChainBlock(
            index=new_index,
            timestamp=timestamp,
            previous_hash=previous_hash,
            event_type=event_type,
            payload=payload,
            nonce=0,
            difficulty=self.difficulty,
            case_id=case_id
        )
        block.mine()
        self.chain.append(block)
        return block

    def verify_chain(self) -> Tuple[bool, str, Optional[int]]:
        """
        Verifies the entire chain:
        1. Genesis block validity.
        2. Index continuity.
        3. Previous hash linking.
        4. Recomputed SHA-256 hash matching.
        5. Proof-of-work difficulty adherence.

        Returns (is_valid, reason, tampered_block_index).
        """
        if not self.chain:
            return False, "Chain is empty.", None

        # 1. Verify Genesis
        genesis = self.chain[0]
        if genesis.index != 0:
            return False, "Genesis block index is not 0.", 0
        if genesis.previous_hash != "0" * 64:
            return False, "Genesis block previous_hash is invalid.", 0
        if genesis.compute_hash() != genesis.hash:
            return False, "Genesis block hash mismatch (tampered payload).", 0
        if not genesis.hash.startswith("0" * genesis.difficulty):
            return False, "Genesis block failed proof-of-work difficulty.", 0

        # 2. Verify Subsequent Blocks
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]

            if current.index != prev.index + 1:
                return False, f"Broken index continuity at block {current.index} (expected {prev.index + 1}).", current.index

            if current.previous_hash != prev.hash:
                return False, f"Link integrity failed at block {current.index}: previous_hash does not match block {prev.index}.", current.index

            recomputed_hash = current.compute_hash()
            if current.hash != recomputed_hash:
                return False, f"Hash mismatch at block {current.index}: block payload was modified.", current.index

            if not current.hash.startswith("0" * current.difficulty):
                return False, f"Proof-of-work invalid at block {current.index}.", current.index

        return True, "TraceChain integrity fully verified. All blocks valid.", None

    def tamper_block_for_test(self, index: int, field: str, new_value: Any) -> bool:
        """
        Test helper to simulate unauthorized tampering with block data.
        """
        if 0 <= index < len(self.chain):
            if field == "payload":
                self.chain[index].payload = new_value
            elif field == "previous_hash":
                self.chain[index].previous_hash = new_value
            elif field == "timestamp":
                self.chain[index].timestamp = new_value
            return True
        return False
