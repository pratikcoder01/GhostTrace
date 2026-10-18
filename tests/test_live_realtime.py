import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import mongomock
from fastapi.testclient import TestClient

from backend.app.database import (
    CaseModel,
    TransactionModel,
    BlockCursorModel,
    RawBlockchainEventModel,
    OSINTSourceRecordModel,
    DatabaseSessionWrapper,
)
from backend.app.schemas import (
    NormalizedBlockchainEvent,
    BlockchainEventType,
    NetworkType,
)
from backend.app.blockchain.providers.base import (
    decode_hex_int,
    format_address,
    decode_erc20_log,
    normalize_native_transaction,
    ERC20_TRANSFER_TOPIC,
)
from backend.app.blockchain.providers.simulator_provider import SimulatorProvider
from backend.app.blockchain.providers.provider_manager import ProviderManager
from backend.app.services.event_pipeline import EventPipeline
from backend.app.services.live_analysis_service import LiveAnalysisService
from backend.app.services.live_osint_collector import LiveOSINTCollector
from backend.app.main import app

@pytest.fixture
def memory_db():
    mock_client = mongomock.MongoClient()
    db = mock_client["ghosttrace_realtime_test"]
    yield DatabaseSessionWrapper(db)

# ----------------- 1. Normalized Event Parsing & ERC-20 Log Decoding -----------------

def test_decode_hex_and_format_address():
    assert decode_hex_int("0x10") == 16
    assert decode_hex_int(100) == 100
    assert decode_hex_int(None) == 0

    # Padded 32-byte topic to 20-byte address
    topic_addr = "0x00000000000000000000000071c7656ec7ab88b098defb751b7401b5f6d8976f"
    formatted = format_address(topic_addr)
    assert formatted == "0x71c7656ec7ab88b098defb751b7401b5f6d8976f"

def test_erc20_log_decoding_success():
    log = {
        "address": "0xdac17f958d2ee523a2206206994597c13d831ec7", # USDT contract (6 decimals)
        "topics": [
            ERC20_TRANSFER_TOPIC,
            "0x0000000000000000000000001111111111111111111111111111111111111111",
            "0x0000000000000000000000002222222222222222222222222222222222222222"
        ],
        "data": hex(5000 * 10**6), # 5,000 USDT
        "blockNumber": "0x1406f40", # 21000000
        "blockHash": "0xblockhash123",
        "transactionHash": "0xtxhash456",
        "logIndex": "0x3",
        "timeStamp": "0x68f40000",
        "removed": False
    }

    event = decode_erc20_log(log, chain_id=1, network="ethereum")
    assert event is not None
    assert event.asset == "USDT"
    assert event.amount == 5000.0
    assert event.from_address == "0x1111111111111111111111111111111111111111"
    assert event.to_address == "0x2222222222222222222222222222222222222222"
    assert event.block_number == 21000000
    assert event.event_type == BlockchainEventType.ERC20_TRANSFER
    assert not event.is_removed

def test_native_transaction_normalization():
    tx = {
        "hash": "0xnative_tx_hash",
        "from": "0xaaaa1111aaaa1111aaaa1111aaaa1111aaaa1111",
        "to": "0xbbbb2222bbbb2222bbbb2222bbbb2222bbbb2222",
        "value": hex(int(2.5 * 1e18)), # 2.5 ETH in wei
        "gas": "0x5208", # 21000
        "gasPrice": hex(int(20 * 1e9)), # 20 gwei
        "blockNumber": "0x1406f40"
    }
    block = {
        "number": "0x1406f40",
        "hash": "0xblockhash_nat",
        "timestamp": "0x68f40000"
    }

    event = normalize_native_transaction(tx, block, chain_id=1, network="ethereum")
    assert event.asset == "ETH"
    assert event.amount == 2.5
    assert event.from_address == "0xaaaa1111aaaa1111aaaa1111aaaa1111aaaa1111"
    assert event.to_address == "0xbbbb2222bbbb2222bbbb2222bbbb2222bbbb2222"
    assert event.event_type == BlockchainEventType.NATIVE_TRANSFER
    assert event.fee > 0

# ----------------- 2. Reorganization and Removed-Log Handling -----------------

def test_reorg_removed_log_decoding():
    log = {
        "address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "topics": [
            ERC20_TRANSFER_TOPIC,
            "0x0000000000000000000000001111111111111111111111111111111111111111",
            "0x0000000000000000000000002222222222222222222222222222222222222222"
        ],
        "data": hex(100 * 10**6),
        "blockNumber": "0x1406f40",
        "blockHash": "0xorphaned_block",
        "transactionHash": "0xreorg_tx",
        "logIndex": "0x1",
        "removed": True # Log was reverted in chain reorg
    }

    event = decode_erc20_log(log, chain_id=1, network="ethereum")
    assert event is not None
    assert event.is_removed is True
    assert event.event_type == BlockchainEventType.REORG_REMOVED

# ----------------- 3. Block Cursor Persistence & Recovery -----------------

def test_cursor_persistence_and_recovery(memory_db):
    pm = ProviderManager()
    cursor = pm.get_or_create_cursor("ethereum", memory_db)
    assert cursor.last_processed_block == 0

    # Advance cursor using the proper MongoDB persistence path
    # Use direct MongoDB update to simulate what update_cursor does
    memory_db.block_cursors.update_one(
        {"_id": "ethereum"},
        {"$set": {"last_processed_block": 21000500, "last_processed_block_hash": "0xhash500"}},
        upsert=True
    )

    # Recovery check
    retrieved = memory_db.query(BlockCursorModel).filter_by(network="ethereum").first()
    assert retrieved.last_processed_block == 21000500
    assert retrieved.last_processed_block_hash == "0xhash500"

# ----------------- 4. Duplicate Event Suppression -----------------

def test_duplicate_event_suppression_in_pipeline():
    async def _run():
        pipeline = EventPipeline(queue_maxsize=10)
        
        event = NormalizedBlockchainEvent(
            event_id="eth_1_21000001_0xdup123_tx",
            chain_id=1,
            network="ethereum",
            event_type=BlockchainEventType.NATIVE_TRANSFER,
            block_number=21000001,
            block_hash="0xblockhash_dup",
            tx_hash="0xdup123",
            log_index=None,
            timestamp="2026-10-18T00:00:00+00:00",
            from_address="0x71c7656ec7ab88b098defb751b7401b5f6d8976f",
            to_address="0x28c6c06298d514db089934071355e5743bf21d60",
            amount=1.5,
            asset="ETH",
            fee=0.001,
            is_removed=False,
            raw_provenance={"test": "dup"}
        )

        # First event ingestion
        await pipeline.process_blockchain_event(event)
        initial_persisted = pipeline.total_persisted

        # Re-ingest exact same event
        await pipeline.process_blockchain_event(event)

        # Should be deduplicated; total_persisted count should not double
        assert pipeline.total_persisted == initial_persisted

    asyncio.run(_run())

# ----------------- 5. Feature Schema Validation & ML Threshold 0.42 -----------------

def test_live_analysis_explicit_unavailable_on_insufficient_features(memory_db):
    service = LiveAnalysisService()
    
    # Create test case and transaction lacking 165 features
    case = CaseModel(
        case_id="CASE-ML-TEST",
        case_name="ML Schema Test Case",
        network="ethereum",
        data_source="live_test",
        status="created",
        seed_addresses_json=json.dumps(["0xseed_victim"]),
        tx_count=1,
        created_at="2026-10-18T00:00:00+00:00",
        updated_at="2026-10-18T00:00:00+00:00"
    )
    tx = TransactionModel(
        case_id="CASE-ML-TEST",
        tx_id="tx_test_no_165",
        network="ethereum",
        data_origin="live_provider",
        timestamp="2026-10-18T00:00:00+00:00",
        from_address="0xseed_victim",
        to_address="0xmule_dest",
        amount=5.0,
        asset="ETH",
        extra_metadata_json="{}" # No 165-feature vector
    )
    memory_db.add(case)
    memory_db.add(tx)
    memory_db.commit()

    res = service._evaluate_ml_inference([tx], "ethereum", "tx_test_no_165")
    
    # Must return explicit unavailable result, NEVER fabricate arbitrary features
    assert res["status"] == "unavailable"
    assert res["threshold_applied"] == 0.42
    assert "lacks calibrated 165-feature vector" in res["reason"]
    assert res["model_risk_score"] is None
    assert res["verified_threat_label"] is None

def test_live_analysis_runs_model_when_165_features_validated(memory_db):
    service = LiveAnalysisService()
    
    # Provide valid 165-feature vector
    vec_165 = [0.0] * 165
    vec_165[48] = 3.5 # elevated anomaly feature
    
    tx = TransactionModel(
        case_id="CASE-ML-VALID",
        tx_id="tx_valid_165",
        network="bitcoin",
        data_origin="elliptic_benchmark",
        timestamp="2026-10-18T00:00:00+00:00",
        from_address="addr1",
        to_address="addr2",
        amount=1.0,
        asset="BTC",
        extra_metadata_json=json.dumps({"feature_vector": vec_165})
    )
    
    res = service._evaluate_ml_inference([tx], "bitcoin", "tx_valid_165")
    
    assert res["status"] == "evaluated"
    assert res["threshold_applied"] == 0.42
    assert res["model_version"] == "v1.1.0"
    assert res["feature_count_validated"] == 165
    assert 0.0 <= res["model_risk_score"] <= 1.0
    assert res["is_statistical_risk_score"] is True
    # Model risk score must be distinct from verified threat label
    assert res["verified_threat_label"] is None

# ----------------- 6. OSINT Caching & Source Fallback -----------------

def test_osint_collector_caching_and_fallback(memory_db):
    async def _run():
        collector = LiveOSINTCollector()
        source_info = {
            "source_id": "test_mock_osint",
            "name": "Mock Test Source",
            "url": "https://threat-feed.invalid/unavailable_endpoint",
            "fallback_file": None,
            "polling_interval_minutes": 60,
            "terms": "Mock source terms"
        }

        res = await collector.collect_source(source_info, memory_db)
        assert res["source_id"] == "test_mock_osint"
        assert res["is_live"] is False
        assert res["status"] in ["pending", "cached"]

    asyncio.run(_run())

# ----------------- 7. Synthetic vs Live Labeling Verification -----------------

def test_synthetic_vs_live_evidence_labeling():
    sim = SimulatorProvider()
    status = sim.get_status()
    assert status.is_simulated is True
    assert "SIMULATION ONLY" in status.provider_name

# ----------------- 8. API & Observability Endpoints -----------------

def test_api_live_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/live/status")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "queue_size" in data
    assert "osint_sources" in data
    assert data["model_version"] == "v1.1.0"
    assert data["active_threshold"] == 0.42

def test_api_health_includes_live_ingestion():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "live_ingestion" in data
    assert "connection_state" in data["live_ingestion"]

def test_simulate_event_injection_endpoint():
    client = TestClient(app)
    response = client.post("/api/live/simulate-event", json={
        "amount": 3.75,
        "asset": "ETH",
        "tx_type": "native"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["amount"] == 3.75
    assert data["is_simulated"] is True

# ----------------- 9. Opt-in Live Smoke Test -----------------

@pytest.mark.skipif(
    not os.getenv("ALCHEMY_API_KEY") or os.getenv("ALCHEMY_API_KEY") == "YOUR_ALCHEMY_API_KEY",
    reason="Opt-in test: Requires real ALCHEMY_API_KEY environment variable."
)
def test_live_alchemy_provider_smoke():
    async def _run():
        from backend.app.blockchain.providers.alchemy_provider import AlchemyWebSocketProvider
        provider = AlchemyWebSocketProvider(api_key=os.getenv("ALCHEMY_API_KEY"))
        assert provider.is_configured()
        # Smoke test block query over HTTP
        block = await provider.fetch_block_by_number(21000000)
        assert block is not None
        assert "number" in block

    asyncio.run(_run())
