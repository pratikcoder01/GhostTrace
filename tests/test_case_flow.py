import pytest
import mongomock
from backend.app.schemas import CaseCreate, NetworkType
from backend.app.services.case_service import case_service
from backend.app.services.report_service import report_service
from backend.app.blockchain.storage import global_chain, TraceChainStorage
from backend.app.blockchain.chain import TraceChain
from backend.app.config import settings
from backend.app.mongodb import mongo_manager

@pytest.fixture
def case_db():
    mock_client = mongomock.MongoClient()
    db = mock_client["ghosttrace_case_flow_test"]
    mongo_manager.client = mock_client
    mongo_manager.db_name = "ghosttrace_case_flow_test"
    mongo_manager._is_mock = True
    mongo_manager._connected = True
    mongo_manager.create_indexes()

    fresh = TraceChain(difficulty=settings.TRACECHAIN_DIFFICULTY)
    global_chain.chain = fresh.chain
    global_chain.difficulty = fresh.difficulty

    TraceChainStorage.load_or_init_chain(db)
    yield db


def test_end_to_end_ghost_attack_investigation(case_db):
    """
    Acceptance Test: Demonstrates complete end-to-end simulated attack investigation.
    Correlates transaction patterns with planted OSINT indicators, ranks expected
    investigation leads, persists the case, and verifies TraceChain integrity.
    """
    # 1. Create Case and Ingest Simulated Attack
    case_in = CaseCreate(
        case_name="Operation Phantom Drain Acceptance Test",
        description="Automated acceptance test for simulated cyber-financial drain scenario",
        network=NetworkType.SIMULATED,
        seed_addresses=["0xSIM_VICTIM_VAULT_01"],
        data_source="synthetic_ghost_attack",
    )

    created_case = case_service.create_and_ingest_case(case_in, case_db)
    assert created_case.status == "ingested"
    assert created_case.tx_count > 0
    assert created_case.evidence_count > 0

    # 2. Execute Forensic Graph Analysis
    analysis_res = case_service.analyze_case(created_case.case_id, case_db)
    assert analysis_res["status"] == "analyzed"
    summary = analysis_res["summary"]
    assert summary["total_transactions"] >= 12
    assert summary["leads_count"] > 0
    assert summary["critical_leads_count"] > 0

    # 3. Verify Planted OSINT & Lead Ranking
    leads = analysis_res["ranked_leads"]
    lead_addresses = [l.address for l in leads]

    # Attacker infiltrator and mixer should be identified
    assert "0xSIM_ATTACKER_INFILTRATOR" in lead_addresses
    assert "0xSIM_MIXER_HOP2_WASH_1" in lead_addresses

    # Check that Attacker Infiltrator received critical/high priority due to
    # direct OSINT match + fan-out
    attacker_lead = next(l for l in leads if l.address == "0xSIM_ATTACKER_INFILTRATOR")
    assert attacker_lead.priority_score >= 60.0
    assert "DIRECT_OSINT_MATCH" in attacker_lead.reason_codes
    assert "FAN_OUT_DISPERSAL" in attacker_lead.reason_codes

    # 4. Verify Timeline
    timeline = analysis_res["timeline"]
    assert len(timeline) >= 12
    # Verify burst transfer flags
    burst_events = [e for e in timeline if "RAPID_BURST" in e.flags]
    assert len(burst_events) > 0

    # 5. Verify TraceChain Proof of Custody
    is_valid, msg, tampered_idx = global_chain.verify_chain()
    assert is_valid is True, (
        f"TraceChain integrity check failed: {msg} "
        f"(tampered block index: {tampered_idx})"
    )
    assert tampered_idx is None

    # Verify that blocks were mined for this case
    case_blocks = [b for b in global_chain.chain if b.case_id == created_case.case_id]
    event_types = [b.event_type for b in case_blocks]
    assert "CASE_INITIALIZED" in event_types
    assert "DATA_INGESTED" in event_types
    assert "FORENSIC_ANALYSIS_COMPLETED" in event_types

    # 6. Generate Forensic Report
    report = report_service.generate_report(created_case.case_id, case_db)
    assert report.case_id == created_case.case_id
    assert report.status == "analyzed"
    assert len(report.ranked_leads) > 0
    assert len(report.timeline) > 0
    assert len(report.evidence_items) > 0
    assert report.tracechain_audit["is_valid"] is True
    assert "LEGAL & FORENSIC DISCLAIMER" in report.limitations_and_disclaimer
