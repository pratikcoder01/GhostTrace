import pytest
from backend.app.database import TransactionModel, EvidenceModel
from backend.app.services.analysis_service import BlockchainAnalysisEngine
from backend.app.schemas import RiskLevel

def make_tx(tx_id, src, dst, amount, ts="2026-10-10T08:00:00Z"):
    return TransactionModel(
        tx_id=tx_id,
        case_id="CASE_TEST",
        network="simulated",
        data_origin="synthetic",
        timestamp=ts,
        from_address=src,
        to_address=dst,
        amount=amount,
        asset="SIM-ETH",
        fee=0.001,
        extra_metadata_json="{}"
    )

def test_graph_construction_and_metrics():
    engine = BlockchainAnalysisEngine(case_id="C1", network="simulated")
    txs = [
        make_tx("tx1", "victim", "attacker", 100.0, "2026-10-10T08:00:00Z"),
        make_tx("tx2", "attacker", "mule_a", 50.0, "2026-10-10T08:01:00Z"),
        make_tx("tx3", "attacker", "mule_b", 48.0, "2026-10-10T08:01:20Z")
    ]
    engine.build_graph(txs, seed_addresses=["victim"], evidence=[])

    assert engine.graph.number_of_nodes() == 4
    assert engine.graph.number_of_edges() == 3
    assert engine.graph.nodes["victim"]["outflow"] == 100.0
    assert engine.graph.nodes["attacker"]["inflow"] == 100.0
    assert engine.graph.nodes["attacker"]["outflow"] == 98.0

def test_fan_out_and_peeling_detection():
    engine = BlockchainAnalysisEngine(case_id="C2", network="simulated")
    txs = [
        make_tx("tx_in", "source", "hub", 200.0, "2026-10-10T08:00:00Z"),
        make_tx("tx_out1", "hub", "leaf1", 60.0, "2026-10-10T08:05:00Z"),
        make_tx("tx_out2", "hub", "leaf2", 60.0, "2026-10-10T08:05:30Z"),
        make_tx("tx_out3", "hub", "leaf3", 60.0, "2026-10-10T08:06:00Z"),
    ]
    engine.build_graph(txs, seed_addresses=["source"], evidence=[])

    leads = engine.calculate_priority_scores(seed_addresses=["source"])
    hub_lead = next(l for l in leads if l.address == "hub")
    
    assert "FAN_OUT_DISPERSAL" in hub_lead.reason_codes
    assert hub_lead.priority_score > 20.0

def test_temporal_burst_detection():
    engine = BlockchainAnalysisEngine(case_id="C3", network="simulated")
    txs = [
        make_tx("b1", "spammer", "dst1", 10.0, "2026-10-10T08:00:00Z"),
        make_tx("b2", "spammer", "dst2", 10.0, "2026-10-10T08:00:20Z"), # 20s delta
        make_tx("b3", "spammer", "dst3", 10.0, "2026-10-10T08:00:50Z"), # 30s delta
    ]
    engine.build_graph(txs, seed_addresses=[], evidence=[])
    bursts = engine.detect_temporal_bursts(max_delta_seconds=300.0)

    assert "spammer" in bursts
    assert bursts["spammer"] == 2

def test_bounded_path_tracing():
    engine = BlockchainAnalysisEngine(case_id="C4", network="simulated")
    txs = [
        make_tx("t1", "nodeA", "nodeB", 10.0),
        make_tx("t2", "nodeB", "nodeC", 9.0),
        make_tx("t3", "nodeC", "nodeD", 8.0)
    ]
    engine.build_graph(txs, seed_addresses=["nodeA"], evidence=[])
    paths = engine.trace_bounded_paths("nodeA", max_depth=3)

    assert ["nodeA", "nodeB", "nodeC", "nodeD"] in paths
