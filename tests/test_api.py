import pytest
import mongomock
from fastapi.testclient import TestClient
from backend.app.database import get_db, DatabaseSessionWrapper
from backend.app.blockchain.storage import TraceChainStorage, global_chain
from backend.app.blockchain.chain import TraceChain
from backend.app.config import settings
from backend.app.mongodb import mongo_manager
from backend.app.main import app

mock_test_client = mongomock.MongoClient()
test_db_instance = mock_test_client["ghosttrace_api_test"]

@pytest.fixture(autouse=True, scope="module")
def setup_isolated_test_database():
    # 1. Configure mongo_manager to use isolated test DB
    mongo_manager.client = mock_test_client
    mongo_manager.db_name = "ghosttrace_api_test"
    mongo_manager._is_mock = True
    mongo_manager._connected = True
    mongo_manager.create_indexes()

    # 2. Reset global_chain singleton to fresh genesis
    fresh_chain = TraceChain(difficulty=settings.TRACECHAIN_DIFFICULTY)
    global_chain.chain = fresh_chain.chain
    global_chain.difficulty = fresh_chain.difficulty

    # 3. Persist genesis block into test DB
    TraceChainStorage.load_or_init_chain(test_db_instance)

    # 4. Override FastAPI get_db dependency
    def override_get_db():
        yield test_db_instance

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "tracechain" in data
    assert data["tracechain"]["integrity_valid"] is True


def test_api_data_sources():
    res = client.get("/api/data-sources")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["data_sources"]) >= 4


def test_api_case_lifecycle_and_forensic_endpoints():
    # 1. Create Case
    payload = {
        "case_name": "API Forensic Investigation Test",
        "description": "Integration test via REST API",
        "network": "simulated",
        "seed_addresses": ["0xSIM_VICTIM_VAULT_01"],
        "data_source": "synthetic_ghost_attack",
    }
    create_res = client.post("/api/cases", json=payload)
    assert create_res.status_code == 201
    case_data = create_res.json()
    case_id = case_data["case_id"]
    assert case_data["status"] == "ingested"
    assert case_data["tx_count"] > 0

    # 2. Get Single Case
    get_res = client.get(f"/api/cases/{case_id}")
    assert get_res.status_code == 200
    assert get_res.json()["case_id"] == case_id

    # 3. List Cases
    list_res = client.get("/api/cases")
    assert list_res.status_code == 200
    assert any(c["case_id"] == case_id for c in list_res.json())

    # 4. Trigger Analysis
    analyze_res = client.post(f"/api/cases/{case_id}/analyze")
    assert analyze_res.status_code == 200
    an_data = analyze_res.json()
    assert an_data["status"] == "analyzed"
    assert "ranked_leads" in an_data

    # 5. Get Graph Data
    graph_res = client.get(f"/api/cases/{case_id}/graph")
    assert graph_res.status_code == 200
    g_data = graph_res.json()
    assert g_data["node_count"] > 0
    assert g_data["edge_count"] > 0

    # 6. Get Evidence
    ev_res = client.get(f"/api/cases/{case_id}/evidence")
    assert ev_res.status_code == 200
    assert len(ev_res.json()) > 0

    # 7. Get Timeline
    time_res = client.get(f"/api/cases/{case_id}/timeline")
    assert time_res.status_code == 200
    assert len(time_res.json()) > 0

    # 8. Get Forensic Report
    rep_res = client.get(f"/api/cases/{case_id}/report")
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["case_id"] == case_id
    assert "tracechain_audit" in rep_data


def test_api_tracechain_endpoints():
    # Blocks
    blocks_res = client.get("/api/chain/blocks")
    assert blocks_res.status_code == 200
    blocks = blocks_res.json()
    assert len(blocks) >= 1
    assert blocks[0]["index"] == 0

    # Verify — chain must be valid after all previous test writes
    verify_res = client.get("/api/chain/verify")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["is_valid"] is True, (
        f"Chain verification failed: {v_data.get('details')}. "
        f"tampered_block_index={v_data.get('tampered_block_index')}"
    )
    assert v_data["tampered_block_index"] is None


def test_api_ml_endpoints():
    # Status
    status_res = client.get("/api/ml/status")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["model_loaded"] is True
    assert st_data["features_count"] == 165

    # Predict
    pred_payload = {
        "tx_id": "test_api_tx_001",
        "features": [0.0] * 165,
        "network": "bitcoin",
    }
    pred_res = client.post("/api/ml/predict", json=pred_payload)
    assert pred_res.status_code == 200
    p_data = pred_res.json()
    assert p_data["prediction_label"] in ["illicit", "licit"]
    assert 0.0 <= p_data["risk_score"] <= 1.0


def test_api_nonexistent_case_404():
    res = client.get("/api/cases/CASE-NONEXISTENT")
    assert res.status_code == 404
