import pytest
import mongomock
from backend.app.database import TransactionModel, EvidenceModel, DatabaseSessionWrapper
from backend.app.services.ingestion_service import IngestionService
from backend.app.schemas import NetworkType, DataOrigin, TransactionRecord

@pytest.fixture
def test_db():
    mock_client = mongomock.MongoClient()
    db = mock_client["ghosttrace_ingestion_test"]
    yield DatabaseSessionWrapper(db)

def test_synthetic_ingestion_success(test_db):
    service = IngestionService()
    inserted_tx, inserted_ev, errors = service.ingest_case_data(
        case_id="TEST_CASE_01",
        network=NetworkType.SIMULATED,
        data_source="synthetic_ghost_attack",
        seed_addresses=["0xSIM_VICTIM_VAULT_01"],
        db=test_db
    )
    assert inserted_tx > 0
    assert inserted_ev > 0
    assert len(errors) == 0

    # Verify DB records
    txs = test_db.query(TransactionModel).filter_by(case_id="TEST_CASE_01").all()
    assert len(txs) == inserted_tx
    for t in txs:
        assert t.network == "simulated"
        assert t.data_origin == "synthetic"
        assert t.amount > 0

def test_duplicate_transaction_suppression(test_db):
    service = IngestionService()
    # First ingestion
    service.ingest_case_data(
        case_id="TEST_CASE_DUP",
        network=NetworkType.SIMULATED,
        data_source="synthetic_ghost_attack",
        seed_addresses=["0xSIM_VICTIM_VAULT_01"],
        db=test_db
    )
    
    # Second ingestion with same case_id (should suppress duplicates)
    tx_count2, _, errors2 = service.ingest_case_data(
        case_id="TEST_CASE_DUP",
        network=NetworkType.SIMULATED,
        data_source="synthetic_ghost_attack",
        seed_addresses=["0xSIM_VICTIM_VAULT_01"],
        db=test_db
    )
    assert tx_count2 == 0
    assert any("Duplicate transaction skipped" in e for e in errors2)

def test_network_separation_enforcement(test_db):
    service = IngestionService()
    # Attempting to ingest synthetic simulated data into an Ethereum case must be flagged
    tx_count, _, errors = service.ingest_case_data(
        case_id="TEST_CASE_NET_SEP",
        network=NetworkType.ETHEREUM,
        data_source="synthetic_ghost_attack",
        seed_addresses=["0x123"],
        db=test_db
    )
    assert tx_count == 0
    assert any("Network mismatch" in e or "Network separation violation" in e for e in errors)
