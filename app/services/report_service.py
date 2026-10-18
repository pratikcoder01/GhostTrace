from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.app.schemas import InvestigationReportResponse
from backend.app.services.case_service import case_service
from backend.app.services.analysis_service import BlockchainAnalysisEngine
from backend.app.repositories.case_repository import CaseRepository
from backend.app.blockchain.storage import global_chain
from backend.app.ml.model_registry import model_registry
import json

class ReportService:
    """
    Forensics Investigation Report Generator.
    Produces comprehensive, auditable forensic reports combining graph analytics,
    temporal timeline, OSINT indicators, ML assessments, and cryptographic TraceChain audits.
    """
    def generate_report(self, case_id: str, db: Any) -> InvestigationReportResponse:
        repo = CaseRepository(db)
        case = repo.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found.")

        txs = repo.get_transactions(case_id)
        evidence = repo.get_evidence(case_id)
        seed_addresses = json.loads(case.seed_addresses_json) if case.seed_addresses_json else []

        engine = BlockchainAnalysisEngine(case_id=case_id, network=case.network)
        engine.build_graph(txs, seed_addresses, evidence)

        leads = engine.calculate_priority_scores(seed_addresses)
        timeline = engine.build_timeline()
        graph_data = engine.export_graph_data(seed_addresses, leads)
        evidence_items = case_service.get_case_evidence(case_id, db)

        # TraceChain Verification
        is_valid, msg, tampered_idx = global_chain.verify_chain()
        tracechain_audit = {
            "is_valid": is_valid,
            "total_blocks": len(global_chain.chain),
            "verification_status": msg,
            "tampered_block_index": tampered_idx,
            "blocks_summary": [
                {
                    "index": b.index,
                    "event_type": b.event_type,
                    "timestamp": b.timestamp,
                    "hash": b.hash,
                    "previous_hash": b.previous_hash,
                    "difficulty": b.difficulty
                }
                for b in global_chain.chain if b.case_id == case_id or b.event_type == "GENESIS"
            ]
        }

        # ML Model Assessment Status
        active_model = model_registry.load_active_model()
        ml_assessment = None
        if active_model:
            ml_assessment = {
                "model_available": True,
                "algorithm": active_model["algorithm"],
                "version": active_model["version"],
                "network": active_model["network"],
                "dataset_provenance": active_model["dataset"],
                "features_count": active_model["features_count"],
                "benchmark_metrics": active_model["metrics"],
                "trained_at": active_model["trained_at"],
                "evaluation_limitations": active_model["limitations"]
            }

        # Executive Summary
        exec_summary = (
            f"Forensic investigation report for Case '{case.case_name}' ({case.case_id}) on network '{case.network}'. "
            f"Analyzed {len(txs)} transactions across {graph_data.node_count} unique wallet addresses. "
            f"Detected {len(leads)} prioritized investigation leads, with {sum(1 for l in leads if l.risk_level.value == 'Critical')} critical leads. "
            f"Identified {len(evidence_items)} threat intelligence matches from verified OSINT feeds."
        )

        provenance_str = (
            f"Data Source: '{case.data_source}'. "
            f"Network: '{case.network}'. "
            "All transaction records and threat indicators are cryptographically tracked in TraceChain."
        )

        network_guarantee = (
            f"Strict Network Isolation Guarantee: This investigation is isolated to the '{case.network}' context. "
            "Transactions from foreign networks (Bitcoin, Ethereum, or Simulated) are strictly barred from cross-mingling."
        )

        disclaimer = (
            "LEGAL & FORENSIC DISCLAIMER: Investigation priority scores represent calibrated heuristic "
            "and statistical risk assessments, NOT definitive legal proof of criminal intent. "
            "Graph proximity and transaction velocity must be independently corroborated by law enforcement subpoenas. "
            "If data origin is synthetic/simulated, it represents an offline benchmark scenario and must NOT be cited as a real-world incident."
        )

        return InvestigationReportResponse(
            case_id=case.case_id,
            case_name=case.case_name,
            network=case.network,
            status=case.status,
            created_at=case.created_at,
            generated_at=datetime.now(timezone.utc).isoformat(),
            executive_summary=exec_summary,
            data_origin_and_provenance=provenance_str,
            network_separation_guarantee=network_guarantee,
            transaction_statistics={
                "total_transactions": len(txs),
                "total_wallets": graph_data.node_count,
                "total_edges": graph_data.edge_count,
                "graph_density": graph_data.density,
                "clusters_count": graph_data.clusters_count,
                "seed_addresses": seed_addresses
            },
            ranked_leads=leads,
            timeline=timeline,
            evidence_items=evidence_items,
            tracechain_audit=tracechain_audit,
            ml_assessment=ml_assessment,
            limitations_and_disclaimer=disclaimer
        )

report_service = ReportService()
