import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


from backend.app.config import settings
from backend.app.database import CaseModel, TransactionModel, EvidenceModel
from backend.app.repositories.case_repository import CaseRepository
from backend.app.services.analysis_service import BlockchainAnalysisEngine
from backend.app.ml.predict import inference_service
from backend.app.ml.model_registry import model_registry
from backend.app.blockchain.storage import global_chain, TraceChainStorage
from backend.app.schemas import NetworkType

logger = logging.getLogger(__name__)

class LiveAnalysisService:
    """
    Real-time forensics analysis engine.
    Incrementally recomputes transaction graphs, priority leads, cash-out forecasts,
    and runs the registered ML model when exact 165-feature vector is validated.
    """
    def analyze_case_incremental(
        self,
        case_id: str,
        db: Any,
        trigger_tx_id: Optional[str] = None
    ) -> Dict[str, Any]:
        repo = CaseRepository(db)
        case = repo.get_case(case_id)
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        seed_addresses: List[str] = json.loads(case.seed_addresses_json) if case.seed_addresses_json else []
        txs = repo.get_transactions(case_id)
        evidence = repo.get_evidence(case_id)

        # 1. Update Graph & Forensics Engine
        engine = BlockchainAnalysisEngine(case_id=case_id, network=case.network)
        engine.build_graph(txs, seed_addresses, evidence)

        leads = engine.calculate_priority_scores(seed_addresses)
        timeline = engine.build_timeline()
        graph_data = engine.export_graph_data(seed_addresses, leads)

        # 2. Recompute Cash-Out Forecast
        forecast = self._compute_cashout_forecast(txs, leads, seed_addresses)

        # 3. Model Inference Execution with Schema Validation
        ml_result = self._evaluate_ml_inference(txs, case.network, trigger_tx_id)

        summary = {
            "total_transactions": len(txs),
            "total_wallets": graph_data.node_count,
            "total_edges": graph_data.edge_count,
            "graph_density": graph_data.density,
            "clusters_count": graph_data.clusters_count,
            "leads_count": len(leads),
            "top_priority_score": leads[0].priority_score if leads else 0.0,
            "critical_leads_count": sum(1 for l in leads if l.risk_level.value == "Critical"),
            "cashout_forecast": forecast,
            "ml_assessment": ml_result,
            "last_analyzed_at": datetime.now(timezone.utc).isoformat()
        }

        # Update case in DB
        repo.update_status(
            case_id=case_id,
            status="analyzed",
            tx_count=len(txs),
            evidence_count=len(evidence),
            summary=summary
        )

        # 4. Append Tamper-Evident TraceChain Block
        audit_block = global_chain.mine_and_add_block(
            event_type="REALTIME_ANALYSIS_UPDATED",
            payload={
                "case_id": case_id,
                "trigger_tx_id": trigger_tx_id,
                "tx_count": len(txs),
                "leads_count": len(leads),
                "top_score": summary["top_priority_score"],
                "ml_status": ml_result.get("status")
            },
            case_id=case_id
        )
        TraceChainStorage.persist_block(audit_block, db)

        return {
            "case_id": case_id,
            "status": "analyzed",
            "summary": summary,
            "ranked_leads": [l.model_dump() for l in leads],
            "graph": graph_data.model_dump(),
            "timeline": [t.model_dump() for t in timeline],
            "cashout_forecast": forecast,
            "ml_assessment": ml_result,
            "audit_block": {
                "index": audit_block.index,
                "hash": audit_block.hash,
                "timestamp": audit_block.timestamp
            }
        }

    def _compute_cashout_forecast(
        self,
        txs: List[TransactionModel],
        leads: Any,
        seed_addresses: List[str]
    ) -> Dict[str, Any]:
        """Calculates cashout dissipation speed and exit gate interaction likelihood."""
        total_inflow = sum(tx.amount for tx in txs if tx.from_address in seed_addresses)
        exit_volume = 0.0
        exit_gate_hits = 0

        for tx in txs:
            to_lower = tx.to_address.lower()
            if any(k in to_lower for k in ("exchange", "binance", "coinbase", "kraken", "deposit", "exit")):
                exit_volume += tx.amount
                exit_gate_hits += 1

        unpeeled_balance = max(0.0, total_inflow - exit_volume)
        cashout_prob = min(1.0, (exit_volume / total_inflow)) if total_inflow > 0 else (0.4 if exit_gate_hits > 0 else 0.0)

        return {
            "total_initial_compromised": round(total_inflow, 4),
            "identified_exit_volume": round(exit_volume, 4),
            "unpeeled_floating_balance": round(unpeeled_balance, 4),
            "cashout_probability": round(cashout_prob, 4),
            "exit_gate_interactions": exit_gate_hits,
            "status": "imminent" if cashout_prob > 0.75 else ("in_transit" if cashout_prob > 0.25 else "dormant")
        }

    def _evaluate_ml_inference(
        self,
        txs: List[TransactionModel],
        case_network: str,
        trigger_tx_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates feature schema and runs RandomForest v1.1.0 at threshold 0.42.
        If feature vector is incomplete or from non-calibrated network without 165 features,
        returns an explicit unavailable result rather than fabricating values.
        """
        active_bundle = model_registry.load_active_model()
        if not active_bundle:
            return {
                "status": "unavailable",
                "reason": "No active ML model found in registry.",
                "threshold_applied": settings.ML_ACTIVE_THRESHOLD,
                "model_risk_score": None,
                "verified_threat_label": None
            }

        target_tx = None
        if trigger_tx_id:
            target_tx = next((t for t in txs if t.tx_id == trigger_tx_id), None)
        if not target_tx and txs:
            target_tx = txs[-1]

        if not target_tx:
            return {
                "status": "unavailable",
                "reason": "No transaction records present for ML evaluation.",
                "threshold_applied": settings.ML_ACTIVE_THRESHOLD,
                "model_risk_score": None,
                "verified_threat_label": None
            }

        # Check for explicit 165-feature vector in transaction metadata
        features_vec = None
        try:
            extra = json.loads(target_tx.extra_metadata_json) if target_tx.extra_metadata_json else {}
            if "feature_vector" in extra and isinstance(extra["feature_vector"], list):
                if len(extra["feature_vector"]) == 165:
                    features_vec = [float(x) for x in extra["feature_vector"]]
        except Exception:
            pass

        # If 165 features exist, run inference safely
        if features_vec and len(features_vec) == 165:
            try:
                res = inference_service.predict(
                    features=features_vec,
                    tx_id=target_tx.tx_id,
                    network=NetworkType.BITCOIN if case_network == "bitcoin" else NetworkType.ETHEREUM,
                    custom_threshold=settings.ML_ACTIVE_THRESHOLD
                )
                return {
                    "status": "evaluated",
                    "algorithm": active_bundle.get("algorithm", "RandomForest"),
                    "model_version": active_bundle.get("version", "v1.1.0"),
                    "threshold_applied": settings.ML_ACTIVE_THRESHOLD,
                    "model_risk_score": res.risk_score,
                    "prediction_label": res.prediction_label,
                    "confidence_explanation": res.confidence_explanation,
                    "is_statistical_risk_score": True,
                    "verified_threat_label": None, # Distinguished from statistical score
                    "feature_count_validated": 165
                }
            except Exception as e:
                logger.warning(f"Inference execution error: {e}")

        # Return explicit unavailable result with explanation
        return {
            "status": "unavailable",
            "algorithm": active_bundle.get("algorithm", "RandomForest"),
            "model_version": active_bundle.get("version", "v1.1.0"),
            "threshold_applied": settings.ML_ACTIVE_THRESHOLD,
            "reason": (
                f"Transaction '{target_tx.tx_id}' on network '{case_network}' lacks calibrated 165-feature vector. "
                "Feature substitution withheld to prevent uncalibrated false positives."
            ),
            "model_risk_score": None,
            "verified_threat_label": None
        }

live_analysis_service = LiveAnalysisService()
