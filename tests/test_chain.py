import pytest
from backend.app.blockchain.block import TraceChainBlock
from backend.app.blockchain.chain import TraceChain

def test_genesis_block():
    chain = TraceChain(difficulty=1)
    assert len(chain.chain) == 1
    genesis = chain.chain[0]
    assert genesis.index == 0
    assert genesis.previous_hash == "0" * 64
    assert genesis.event_type == "GENESIS"
    assert genesis.hash.startswith("0")
    assert genesis.compute_hash() == genesis.hash

def test_mine_and_add_block():
    chain = TraceChain(difficulty=2)
    b1 = chain.mine_and_add_block("TEST_EVENT_1", {"key": "value1"}, case_id="CASE_TEST")
    assert b1.index == 1
    assert b1.previous_hash == chain.chain[0].hash
    assert b1.hash.startswith("00")
    assert len(chain.chain) == 2

    is_valid, msg, tampered_idx = chain.verify_chain()
    assert is_valid is True
    assert tampered_idx is None

def test_tamper_detection_payload():
    chain = TraceChain(difficulty=2)
    chain.mine_and_add_block("EVENT_1", {"data": "authentic"}, case_id="C1")
    chain.mine_and_add_block("EVENT_2", {"data": "authentic"}, case_id="C1")
    
    # Tamper with block 1 payload
    chain.tamper_block_for_test(1, "payload", {"data": "tampered_by_adversary"})
    is_valid, msg, tampered_idx = chain.verify_chain()
    assert is_valid is False
    assert tampered_idx == 1
    assert "Hash mismatch" in msg

def test_tamper_detection_link():
    chain = TraceChain(difficulty=2)
    chain.mine_and_add_block("EVENT_1", {"data": "step1"}, case_id="C2")
    chain.mine_and_add_block("EVENT_2", {"data": "step2"}, case_id="C2")
    
    # Tamper with block 2's previous_hash link
    chain.tamper_block_for_test(2, "previous_hash", "f" * 64)
    is_valid, msg, tampered_idx = chain.verify_chain()
    assert is_valid is False
    assert tampered_idx == 2
    assert "Link integrity failed" in msg
