import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def sample_case():
    res = client.post(
        "/api/cases",
        json={
            "case_name": "Test Suite Investigation Case",
            "description": "Deterministic test case for new forensic endpoints",
            "network": "simulated",
            "seed_addresses": ["0xVictimVaultSeed1", "0xVictimVaultSeed2"],
            "data_source": "synthetic_ghost_attack"
        }
    )
    assert res.status_code == 201
    case_data = res.json()
    case_id = case_data["case_id"]

    # Run analysis
    res_ana = client.post(f"/api/cases/{case_id}/analyze")
    assert res_ana.status_code == 200
    return case_id

def test_get_case_leads(sample_case):
    res = client.get(f"/api/cases/{sample_case}/leads")
    assert res.status_code == 200
    data = res.json()
    assert "case_id" in data
    assert data["case_id"] == sample_case
    assert "total" in data
    assert "leads" in data
    assert isinstance(data["leads"], list)
    assert data["total"] == len(data["leads"])

def test_get_case_matrices(sample_case):
    res = client.get(f"/api/cases/{sample_case}/matrices")
    assert res.status_code == 200
    data = res.json()
    assert "flowMatrix" in data
    assert "activityMatrix" in data
    assert "bins" in data
    assert "walletIds" in data
    assert "featureMatrix" in data
    assert "wallets" in data
    assert isinstance(data["bins"], list)
    assert len(data["bins"]) == 6
    assert isinstance(data["wallets"], list)
    assert len(data["wallets"]) > 0

def test_get_case_exposure(sample_case):
    res = client.get(f"/api/cases/{sample_case}/exposure")
    assert res.status_code == 200
    data = res.json()
    assert "observedSourceOutflow" in data
    assert "observedSourceOutflowUSD" in data
    assert "candidateExits" in data
    assert "pathSummary" in data
    assert "doubleCountingWarning" in data
    assert "do NOT sum across hops" in data["doubleCountingWarning"]
    assert isinstance(data["pathSummary"], list)
    assert len(data["pathSummary"]) > 0

def test_get_case_cashout_forecast(sample_case):
    res = client.get(f"/api/cases/{sample_case}/cashout-forecast")
    assert res.status_code == 200
    data = res.json()
    assert "case_id" in data
    assert "total_initial_compromised" in data
    assert "forecast_by_day" in data
    assert "routes" in data
    assert isinstance(data["forecast_by_day"], list)
    assert len(data["forecast_by_day"]) == 8
    assert isinstance(data["routes"], list)
    assert len(data["routes"]) > 0
    assert "notice" in data

def test_chain_demo_tamper_and_reset():
    # 1. Reset demo chain first
    res_reset1 = client.post("/api/chain/demo-reset")
    assert res_reset1.status_code == 200
    data_r1 = res_reset1.json()
    assert data_r1["is_valid"] is True

    # 2. Tamper demo chain
    res_tamper = client.post("/api/chain/demo-tamper")
    assert res_tamper.status_code == 200
    data_t = res_tamper.json()
    assert data_t["is_valid"] is False
    assert data_t["tampered_block_index"] == 1

    # 3. Verify demo-verify also reports failure
    res_verify = client.get("/api/chain/demo-verify")
    assert res_verify.status_code == 200
    data_v = res_verify.json()
    assert data_v["is_valid"] is False

    # 4. Reset demo chain
    res_reset2 = client.post("/api/chain/demo-reset")
    assert res_reset2.status_code == 200
    data_r2 = res_reset2.json()
    assert data_r2["is_valid"] is True

    # 5. Verify demo-verify reports success
    res_verify2 = client.get("/api/chain/demo-verify")
    assert res_verify2.status_code == 200
    assert res_verify2.json()["is_valid"] is True
