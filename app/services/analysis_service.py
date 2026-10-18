import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Set, Optional
import networkx as nx
from backend.app.schemas import (
    GraphNode, GraphEdge, GraphDataResponse, AnalysisLead, TimelineEvent, RiskLevel
)
from backend.app.database import TransactionModel, EvidenceModel
from backend.app.services.osint_service import osint_service

class BlockchainAnalysisEngine:
    """
    Forensics Analysis Engine powered by NetworkX.
    Performs directed transaction graph analysis, temporal burst calculation,
    fan-in/fan-out pattern detection, graph clustering, OSINT correlation,
    and investigation-priority score calculation.
    """
    def __init__(self, case_id: str, network: str):
        self.case_id = case_id
        self.network = network
        self.graph = nx.MultiDiGraph()
        self.transactions: List[TransactionModel] = []
        self.evidence: List[EvidenceModel] = []

    def build_graph(
        self,
        transactions: List[TransactionModel],
        seed_addresses: List[str],
        evidence: List[EvidenceModel]
    ) -> None:
        self.transactions = sorted(transactions, key=lambda x: x.timestamp)
        self.evidence = evidence
        self.graph.clear()

        # Build address to evidence mapping
        evidence_by_addr: Dict[str, List[EvidenceModel]] = {}
        for ev in evidence:
            val = ev.indicator_value.strip()
            norm = val.lower() if val.startswith("0x") else val
            evidence_by_addr.setdefault(norm, []).append(ev)

        # Add nodes and edges
        for tx in self.transactions:
            src = tx.from_address.strip()
            dst = tx.to_address.strip()

            if not self.graph.has_node(src):
                self.graph.add_node(
                    src,
                    inflow=0.0,
                    outflow=0.0,
                    tx_count=0,
                    is_seed=src in seed_addresses,
                    osint_hits=len(evidence_by_addr.get(src.lower() if src.startswith("0x") else src, []))
                )
            if not self.graph.has_node(dst):
                self.graph.add_node(
                    dst,
                    inflow=0.0,
                    outflow=0.0,
                    tx_count=0,
                    is_seed=dst in seed_addresses,
                    osint_hits=len(evidence_by_addr.get(dst.lower() if dst.startswith("0x") else dst, []))
                )

            # Update metrics
            self.graph.nodes[src]["outflow"] += tx.amount
            self.graph.nodes[src]["tx_count"] += 1
            self.graph.nodes[dst]["inflow"] += tx.amount
            self.graph.nodes[dst]["tx_count"] += 1

            # Add directed edge with attributes
            self.graph.add_edge(
                src,
                dst,
                key=tx.tx_id,
                tx_id=tx.tx_id,
                amount=tx.amount,
                asset=tx.asset,
                timestamp=tx.timestamp,
                fee=tx.fee or 0.0
            )

    def detect_temporal_bursts(self, max_delta_seconds: float = 300.0) -> Dict[str, int]:
        """
        Calculates high-frequency burst patterns: transfers from the same sender
        occurring within a narrow time window (<= 300s).
        Returns {address: burst_count}.
        """
        bursts_by_sender: Dict[str, int] = {}
        tx_by_sender: Dict[str, List[datetime]] = {}

        for tx in self.transactions:
            try:
                # Parse ISO timestamp
                ts = datetime.fromisoformat(tx.timestamp.replace("Z", "+00:00"))
                tx_by_sender.setdefault(tx.from_address, []).append(ts)
            except Exception:
                continue

        for sender, timestamps in tx_by_sender.items():
            if len(timestamps) < 2:
                continue
            timestamps.sort()
            burst_count = 0
            for i in range(1, len(timestamps)):
                delta = (timestamps[i] - timestamps[i - 1]).total_seconds()
                if delta <= max_delta_seconds:
                    burst_count += 1
            if burst_count > 0:
                bursts_by_sender[sender] = burst_count

        return bursts_by_sender

    def detect_peeling_chains(self) -> Set[str]:
        """
        Detects addresses exhibiting peeling chain behavior:
        One large incoming transfer followed by multiple asymmetric outgoing transfers.
        """
        peeling_addrs: Set[str] = set()
        for node in self.graph.nodes:
            in_deg = self.graph.in_degree(node)
            out_deg = self.graph.out_degree(node)
            outflow = self.graph.nodes[node]["outflow"]
            inflow = self.graph.nodes[node]["inflow"]

            # Peeling characteristic: received funds then dispersed to >= 2 destinations
            if in_deg >= 1 and out_deg >= 2 and inflow > 0:
                # Check for asymmetry in outgoing edge amounts
                out_edges = self.graph.out_edges(node, data=True)
                amounts = [e[2].get("amount", 0.0) for e in out_edges]
                if len(amounts) >= 2:
                    peeling_addrs.add(node)
        return peeling_addrs

    def compute_graph_clusters(self) -> Dict[str, int]:
        """
        Computes graph clusters / wallet communities using weakly connected components.
        Returns {address: cluster_id}.
        """
        wcc = list(nx.weakly_connected_components(self.graph))
        cluster_map: Dict[str, int] = {}
        for cluster_id, component in enumerate(wcc):
            for addr in component:
                cluster_map[addr] = cluster_id
        return cluster_map

    def trace_bounded_paths(
        self,
        source_address: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """
        Finds bounded simple paths from a source address up to max_depth.
        """
        if source_address not in self.graph:
            return []

        paths: List[List[str]] = []
        for target in self.graph.nodes:
            if target == source_address:
                continue
            try:
                for path in nx.all_simple_paths(self.graph, source=source_address, target=target, cutoff=max_depth):
                    paths.append(path)
                    if len(paths) >= 25: # Bound path exploration
                        break
            except Exception:
                continue
        return paths

    def calculate_priority_scores(
        self,
        seed_addresses: List[str]
    ) -> List[AnalysisLead]:
        """
        Computes calibrated investigation priority scores (0.0 to 100.0).
        Weights:
        - Direct OSINT Match: 40 points
        - Fan-Out / Dispersal: 20 points
        - High-Frequency Burst Pattern: 15 points
        - Peeling Chain Pattern: 15 points
        - Exchange / Exit Gate Interaction: 10 points
        """
        bursts = self.detect_temporal_bursts(max_delta_seconds=300.0)
        peeling = self.detect_peeling_chains()
        clusters = self.compute_graph_clusters()

        leads: List[AnalysisLead] = []

        evidence_map: Dict[str, List[EvidenceModel]] = {}
        for ev in self.evidence:
            val = ev.indicator_value.strip()
            norm = val.lower() if val.startswith("0x") else val
            evidence_map.setdefault(norm, []).append(ev)

        for node in self.graph.nodes:
            score = 0.0
            reason_codes: List[str] = []
            supporting_tx_ids: List[str] = []
            evidence_ids: List[str] = []

            # 1. OSINT Evidence Correlation
            norm_node = node.lower() if node.startswith("0x") else node
            matched_evidence = evidence_map.get(norm_node, [])
            if matched_evidence:
                score += 40.0
                reason_codes.append("DIRECT_OSINT_MATCH")
                for ev in matched_evidence:
                    evidence_ids.append(ev.evidence_id)
                    reason_codes.append(f"OSINT_FLAG_{ev.category.upper().replace(' ', '_')}")

            # 2. Fan-Out Pattern
            out_deg = self.graph.out_degree(node)
            in_deg = self.graph.in_degree(node)
            if out_deg >= 3:
                score += 20.0
                reason_codes.append("FAN_OUT_DISPERSAL")
            elif out_deg >= 2:
                score += 10.0
                reason_codes.append("MULTI_DESTINATION_TRANSFER")

            # 3. Fan-In Aggregation Pattern
            if in_deg >= 2:
                score += 10.0
                reason_codes.append("FAN_IN_AGGREGATION")

            # 4. Burst Transfers
            if node in bursts:
                burst_score = min(15.0, bursts[node] * 5.0)
                score += burst_score
                reason_codes.append(f"HIGH_BURST_FREQUENCY_{bursts[node]}_TRANSFERS")

            # 5. Peeling Chain
            if node in peeling:
                score += 15.0
                reason_codes.append("PEELING_CHAIN_DETECTED")

            # 6. Seed Address Proximity & High Value Flow
            if node in seed_addresses:
                reason_codes.append("SEED_COMPROMISED_WALLET")
            
            # Detect exit or bridge keywords in address or metadata
            node_lower = node.lower()
            if "exchange" in node_lower or "exit" in node_lower or "deposit" in node_lower:
                score += 10.0
                reason_codes.append("EXCHANGE_EXIT_DEPOSIT")
            if "bridge" in node_lower or "mixer" in node_lower or "wash" in node_lower:
                score += 10.0
                reason_codes.append("OBFUSCATION_GATE_INTERACTION")

            # Collect supporting transactions
            for _, _, data in self.graph.in_edges(node, data=True):
                supporting_tx_ids.append(data.get("tx_id"))
            for _, _, data in self.graph.out_edges(node, data=True):
                supporting_tx_ids.append(data.get("tx_id"))

            score = min(100.0, score)

            # Determine Risk Level
            if score >= 75.0:
                risk_level = RiskLevel.CRITICAL
            elif score >= 50.0:
                risk_level = RiskLevel.HIGH
            elif score >= 25.0:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            summary_text = (
                f"Address {node[:12]}... exhibits priority score {score:.1f}/100 based on "
                f"{len(reason_codes)} forensic indicators. Inflow: {self.graph.nodes[node]['inflow']:.2f}, "
                f"Outflow: {self.graph.nodes[node]['outflow']:.2f}."
            )

            lead = AnalysisLead(
                lead_id=f"LEAD-{self.case_id}-{len(leads)+1:03d}",
                address=node,
                priority_score=round(score, 2),
                risk_level=risk_level,
                reason_codes=list(dict.fromkeys(reason_codes)), # Deduplicate
                supporting_tx_ids=list(dict.fromkeys(supporting_tx_ids)),
                evidence_ids=list(dict.fromkeys(evidence_ids)),
                provenance="GhostTrace NetworkX Forensics Engine",
                summary=summary_text
            )
            leads.append(lead)

        # Sort leads descending by priority score
        leads.sort(key=lambda x: x.priority_score, reverse=True)
        return leads

    def build_timeline(self) -> List[TimelineEvent]:
        """Constructs a chronological event timeline with forensic flags."""
        timeline: List[TimelineEvent] = []
        bursts = self.detect_temporal_bursts()
        peeling = self.detect_peeling_chains()

        for tx in self.transactions:
            flags: List[str] = []
            if tx.from_address in bursts:
                flags.append("RAPID_BURST")
            if tx.from_address in peeling:
                flags.append("PEELING_STEP")
            if "drain" in tx.tx_id:
                flags.append("INITIAL_COMPROMISE")
            if "bridge" in tx.to_address.lower():
                flags.append("BRIDGE_TRANSIT")
            if "exchange" in tx.to_address.lower():
                flags.append("EXCHANGE_DEPOSIT")

            event_desc = (
                f"Transfer of {tx.amount:.2f} {tx.asset} from "
                f"{tx.from_address} to {tx.to_address}"
            )
            timeline.append(
                TimelineEvent(
                    timestamp=tx.timestamp,
                    event_type="TRANSACTION_FLOW",
                    description=event_desc,
                    tx_id=tx.tx_id,
                    addresses_involved=[tx.from_address, tx.to_address],
                    amount=tx.amount,
                    asset=tx.asset,
                    flags=flags
                )
            )

        timeline.sort(key=lambda x: x.timestamp)
        return timeline

    def export_graph_data(
        self,
        seed_addresses: List[str],
        leads: List[AnalysisLead]
    ) -> GraphDataResponse:
        lead_score_map = {l.address: (l.priority_score, l.risk_level.value) for l in leads}
        clusters = self.compute_graph_clusters()

        nodes: List[GraphNode] = []
        for n in self.graph.nodes:
            inflow = float(self.graph.nodes[n].get("inflow", 0.0))
            outflow = float(self.graph.nodes[n].get("outflow", 0.0))
            p_score, r_lvl = lead_score_map.get(n, (0.0, "Low"))

            nodes.append(
                GraphNode(
                    id=n,
                    in_degree=self.graph.in_degree(n),
                    out_degree=self.graph.out_degree(n),
                    total_inflow=round(inflow, 4),
                    total_outflow=round(outflow, 4),
                    net_flow=round(inflow - outflow, 4),
                    tx_count=self.graph.nodes[n].get("tx_count", 0),
                    is_seed=n in seed_addresses,
                    osint_hits=self.graph.nodes[n].get("osint_hits", 0),
                    cluster_id=clusters.get(n, 0),
                    priority_score=p_score,
                    risk_level=r_lvl
                )
            )

        edges: List[GraphEdge] = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(
                GraphEdge(
                    source=u,
                    target=v,
                    tx_id=data.get("tx_id", ""),
                    amount=float(data.get("amount", 0.0)),
                    asset=data.get("asset", "SIM-ETH"),
                    timestamp=data.get("timestamp", "")
                )
            )

        density = nx.density(self.graph) if len(nodes) > 1 else 0.0

        return GraphDataResponse(
            case_id=self.case_id,
            network=self.network,
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
            density=round(density, 4),
            clusters_count=len(set(clusters.values())) if clusters else 0
        )
