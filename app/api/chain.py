from typing import List, Optional
from fastapi import APIRouter
from backend.app.schemas import (
    TraceChainBlockResponse, TraceChainVerifyResponse,
    DemoTamperResponse, DemoResetResponse
)
from backend.app.blockchain.storage import global_chain
from backend.app.blockchain.chain import TraceChain

router = APIRouter(prefix="/chain", tags=["TraceChain Ledger"])

def _init_demo_chain() -> TraceChain:
    c = TraceChain(difficulty=1)
    c.mine_and_add_block("DEMO_EVIDENCE_REGISTERED", {"evidence_id": "EV-DEMO-01", "type": "Victim Wallet Ingestion"}, case_id="CASE-DEMO")
    c.mine_and_add_block("DEMO_FORENSIC_ANALYSIS", {"analysis_type": "NetworkX Path Extraction", "leads_found": 3}, case_id="CASE-DEMO")
    return c

_demo_chain: TraceChain = _init_demo_chain()

@router.get("/blocks", response_model=List[TraceChainBlockResponse])
def get_blocks():
    """
    Returns the complete list of immutable, hash-linked audit blocks in TraceChain.
    """
    return [
        TraceChainBlockResponse(
            index=b.index,
            timestamp=b.timestamp,
            previous_hash=b.previous_hash,
            nonce=b.nonce,
            difficulty=b.difficulty,
            hash=b.hash,
            event_type=b.event_type,
            case_id=b.case_id,
            payload=b.payload
        )
        for b in global_chain.chain
    ]

@router.get("/verify", response_model=TraceChainVerifyResponse)
def verify_chain():
    """
    Performs cryptographic validation of the entire TraceChain audit ledger:
    - Verifies genesis block.
    - Validates SHA-256 hash continuity between blocks.
    - Recomputes canonical hashes to detect tampering.
    - Verifies proof-of-work difficulty.
    """
    is_valid, msg, tampered_idx = global_chain.verify_chain()

    return TraceChainVerifyResponse(
        is_valid=is_valid,
        total_blocks=len(global_chain.chain),
        genesis_valid=len(global_chain.chain) > 0 and global_chain.chain[0].index == 0,
        link_integrity_valid=is_valid,
        pow_valid=is_valid,
        details=msg,
        tampered_block_index=tampered_idx
    )

@router.post("/demo-tamper", response_model=DemoTamperResponse)
def demo_tamper():
    """
    Demonstrates tamper-detection capability. Modifies the payload of block #1
    in an isolated demonstration chain without updating cryptographic hashes.
    Verifies that hash continuity check fails immediately.
    """
    global _demo_chain
    if len(_demo_chain.chain) < 2:
        _demo_chain = _init_demo_chain()

    _demo_chain.chain[1].payload["_tampered_flag"] = True
    _demo_chain.chain[1].payload["injected_illicit_amount"] = 9999999.99

    is_valid, msg, tampered_idx = _demo_chain.verify_chain()
    return DemoTamperResponse(
        message=f"Block #{tampered_idx or 1} payload tampered in isolated demonstration chain.",
        tampered_block_index=tampered_idx if tampered_idx is not None else 1,
        is_valid=is_valid,
        details=msg
    )

@router.post("/demo-reset", response_model=DemoResetResponse)
def demo_reset():
    """
    Resets the isolated demonstration chain to an un-tampered, cryptographically verified state.
    """
    global _demo_chain
    _demo_chain = _init_demo_chain()
    is_valid, msg, _ = _demo_chain.verify_chain()
    return DemoResetResponse(
        message="Isolated demonstration chain reset to pristine verified state.",
        block_count=len(_demo_chain.chain),
        is_valid=is_valid,
        details=msg
    )

@router.get("/demo-verify", response_model=TraceChainVerifyResponse)
def verify_demo_chain():
    """Verifies the isolated demonstration chain."""
    global _demo_chain
    is_valid, msg, tampered_idx = _demo_chain.verify_chain()
    return TraceChainVerifyResponse(
        is_valid=is_valid,
        total_blocks=len(_demo_chain.chain),
        genesis_valid=len(_demo_chain.chain) > 0 and _demo_chain.chain[0].index == 0,
        link_integrity_valid=is_valid,
        pow_valid=is_valid,
        details=msg,
        tampered_block_index=tampered_idx
    )

