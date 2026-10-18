from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class NetworkType(str, Enum):
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    SIMULATED = "simulated"

class DataOrigin(str, Enum):
    SYNTHETIC = "synthetic"
    ELLIPTIC_BENCHMARK = "elliptic_benchmark"
    LIVE_PROVIDER = "live_provider"
    HISTORICAL_SAMPLE = "historical_sample"
    OSINT_SNAPSHOT = "osint_snapshot"

class RiskLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"

class CaseStatus(str, Enum):
    CREATED = "created"
    INGESTED = "ingested"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"

# ----------------- Transaction Schemas -----------------

class TransactionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    tx_id: str = Field(..., description="Unique transaction identifier")
    network: NetworkType = Field(..., description="Blockchain or simulated network")
    data_origin: DataOrigin = Field(..., description="Origin of this data record")
    timestamp: str = Field(..., description="Canonical ISO-8601 timestamp")
    from_address: str = Field(..., description="Sender wallet or contract address")
    to_address: str = Field(..., description="Receiver wallet or contract address")
    amount: float = Field(..., ge=0.0, description="Decimal amount transferred")
    asset: str = Field("SIM-ETH", description="Asset symbol (e.g. BTC, ETH, USDT)")
    block_number: Optional[int] = Field(None, description="Block height if available")
    tx_hash: Optional[str] = Field(None, description="On-chain transaction hash")
    fee: Optional[float] = Field(0.0, ge=0.0, description="Transaction fee")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context/attributes")

# ----------------- OSINT & Evidence Schemas -----------------

class OSINTIndicator(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    indicator_id: str
    indicator_type: str = Field(..., description="address, domain, twitter_handle, ip, ioc_signature")
    indicator_value: str
    network: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    description: Optional[str] = None
    source_name: str
    source_url: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    retrieved_at: str
    provenance: str

class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    evidence_id: str
    case_id: str
    indicator_type: str
    indicator_value: str
    category: str
    subcategory: Optional[str] = None
    description: Optional[str] = None
    source_name: str
    source_url: Optional[str] = None
    provenance: str
    created_at: str

# ----------------- Case Schemas -----------------

class CaseCreate(BaseModel):
    case_name: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = None
    network: NetworkType = Field(default=NetworkType.SIMULATED)
    seed_addresses: List[str] = Field(..., min_length=1)
    data_source: str = Field(default="synthetic_ghost_attack", description="synthetic_ghost_attack, cryptoscamdb, elliptic, ethereum_etherscan")

class CaseResponse(BaseModel):
    case_id: str
    case_name: str
    description: Optional[str] = None
    network: str
    data_source: str
    status: str
    seed_addresses: List[str] = Field(default_factory=list)
    tx_count: int = 0
    evidence_count: int = 0
    created_at: str
    updated_at: str
    summary: Optional[Dict[str, Any]] = None

# ----------------- Analysis & Graph Schemas -----------------

class GraphNode(BaseModel):
    id: str
    in_degree: int = 0
    out_degree: int = 0
    total_inflow: float = 0.0
    total_outflow: float = 0.0
    net_flow: float = 0.0
    tx_count: int = 0
    is_seed: bool = False
    osint_hits: int = 0
    cluster_id: int = 0
    priority_score: float = 0.0
    risk_level: str = "Low"

class GraphEdge(BaseModel):
    source: str
    target: str
    tx_id: str
    amount: float
    asset: str
    timestamp: str

class GraphDataResponse(BaseModel):
    case_id: str
    network: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int
    density: float
    clusters_count: int

class AnalysisLead(BaseModel):
    lead_id: str
    address: str
    priority_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: RiskLevel
    reason_codes: List[str]
    supporting_tx_ids: List[str]
    evidence_ids: List[str]
    provenance: str
    summary: str

class TimelineEvent(BaseModel):
    timestamp: str
    event_type: str
    description: str
    tx_id: Optional[str] = None
    addresses_involved: List[str] = Field(default_factory=list)
    amount: Optional[float] = None
    asset: Optional[str] = None
    flags: List[str] = Field(default_factory=list)

# ----------------- TraceChain Schemas -----------------

class TraceChainBlockResponse(BaseModel):
    index: int
    timestamp: str
    previous_hash: str
    nonce: int
    difficulty: int
    hash: str
    event_type: str
    case_id: Optional[str] = None
    payload: Dict[str, Any]

class TraceChainVerifyResponse(BaseModel):
    is_valid: bool
    total_blocks: int
    genesis_valid: bool
    link_integrity_valid: bool
    pow_valid: bool
    details: str
    tampered_block_index: Optional[int] = None

# ----------------- ML Schemas -----------------

class MLStatusResponse(BaseModel):
    model_loaded: bool
    model_name: Optional[str] = None
    version: Optional[str] = None
    network: Optional[str] = None
    algorithm: Optional[str] = None
    features_count: int = 0
    metrics: Optional[Dict[str, Any]] = None
    evaluation_limitations: str
    training_timestamp: Optional[str] = None

class MLPredictRequest(BaseModel):
    tx_id: Optional[str] = "custom_tx_test"
    features: List[float] = Field(..., min_length=1, description="Feature vector matching model schema")
    network: NetworkType = NetworkType.BITCOIN

class MLPredictResponse(BaseModel):
    tx_id: str
    prediction_label: str = Field(..., description="illicit or licit")
    prediction_class: int = Field(..., description="1 for illicit, 0 for licit")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Raw model confidence / probability")
    model_version: str
    network: str
    confidence_explanation: str
    limitations: str

class MLTrainRequest(BaseModel):
    dataset_name: str = Field(default="elliptic", description="elliptic or synthetic_fixture")
    max_rows: Optional[int] = Field(default=50000, description="Bounded row limit for CPU execution")

class MLTrainResponse(BaseModel):
    status: str
    model_name: str
    algorithm: str
    version: str
    train_rows: int
    test_rows: int
    metrics: Dict[str, Any]
    artifacts_saved: List[str]

# ----------------- Reporting Schema -----------------

class InvestigationReportResponse(BaseModel):
    case_id: str
    case_name: str
    network: str
    status: str
    created_at: str
    generated_at: str
    executive_summary: str
    data_origin_and_provenance: str
    network_separation_guarantee: str
    transaction_statistics: Dict[str, Any]
    ranked_leads: List[AnalysisLead]
    timeline: List[TimelineEvent]
    evidence_items: List[EvidenceItem]
    tracechain_audit: Dict[str, Any]
    ml_assessment: Optional[Dict[str, Any]] = None
    limitations_and_disclaimer: str

# ----------------- Live Real-Time & Provider Schemas -----------------

class BlockchainEventType(str, Enum):
    BLOCK_HEADER = "block_header"
    NATIVE_TRANSFER = "native_transfer"
    ERC20_TRANSFER = "erc20_transfer"
    REORG_REMOVED = "reorg_removed"

class NormalizedBlockchainEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    event_id: str
    chain_id: int = 1
    network: str = "ethereum"
    event_type: BlockchainEventType = BlockchainEventType.NATIVE_TRANSFER
    block_number: int
    block_hash: str
    tx_hash: str
    log_index: Optional[int] = None
    timestamp: str
    from_address: str
    to_address: str
    amount: float
    asset: str = "ETH"
    contract_address: Optional[str] = None
    fee: float = 0.0
    is_removed: bool = False
    raw_provenance: Dict[str, Any] = Field(default_factory=dict)

class LiveProviderStatus(BaseModel):
    provider_name: str
    network: str
    connected: bool
    connection_state: str
    last_received_block: Optional[int] = None
    last_processed_block: Optional[int] = None
    ingestion_lag: int = 0
    events_received_count: int = 0
    events_persisted_count: int = 0
    error_count: int = 0
    last_event_time: Optional[str] = None
    is_simulated: bool = False

class LiveStatusResponse(BaseModel):
    status: str
    provider: LiveProviderStatus
    queue_size: int
    latest_analysis_time: Optional[str] = None
    osint_sources: Dict[str, Any] = Field(default_factory=dict)
    model_version: str = "v1.1.0"
    active_threshold: float = 0.42

class WebSocketMessage(BaseModel):
    event_id: str
    type: str
    timestamp: str
    case_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

class SimulateEventRequest(BaseModel):
    case_id: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    amount: Optional[float] = 2.5
    asset: Optional[str] = "ETH"
    tx_type: Optional[str] = "native"
    contract_address: Optional[str] = None
    is_removed: Optional[bool] = False

# ----------------- Matrices, Exposure, Forecast & Demo Schemas -----------------

class FeatureMatrixItem(BaseModel):
    fanIn: int = 0
    fanOut: int = 0
    meanTransferAmt: float = 0.0
    totalOut: float = 0.0
    hopDepth: int = 0

class WalletItem(BaseModel):
    id: str
    address: str
    label: str
    category: str
    notes: Optional[str] = None
    inflow: Optional[float] = 0.0
    outflow: Optional[float] = 0.0
    tx_count: Optional[int] = 0
    risk_level: Optional[str] = "Low"

class MatricesResponse(BaseModel):
    flowMatrix: Dict[str, Dict[str, float]]
    activityMatrix: Dict[str, Dict[str, int]]
    bins: List[str]
    walletIds: List[str]
    featureMatrix: Dict[str, FeatureMatrixItem]
    wallets: List[WalletItem]

class ExposurePathItem(BaseModel):
    path: str
    amount: float
    type: str

class CandidateExitItem(BaseModel):
    walletId: str
    address: str
    label: str
    observedAmount: float

class ExposureResponse(BaseModel):
    observedSourceOutflow: float
    observedSourceOutflowUSD: float
    asset: str
    candidateExitAmount: Optional[float] = None
    candidateExits: List[CandidateExitItem]
    pathSummary: List[ExposurePathItem]
    projectionStatus: str
    projectionNote: str
    doubleCountingWarning: str

class ForecastDayItem(BaseModel):
    day: str
    volume: float
    probability: float

class ForecastRouteItem(BaseModel):
    route: str
    volume: float
    risk: str

class CashoutForecastResponse(BaseModel):
    case_id: str
    total_initial_compromised: float
    identified_exit_volume: float
    unpeeled_floating_balance: float
    cashout_probability: float
    exit_gate_interactions: int
    status: str
    forecast_by_day: List[ForecastDayItem]
    routes: List[ForecastRouteItem]
    notice: str

class CaseLeadsResponse(BaseModel):
    case_id: str
    total: int
    leads: List[AnalysisLead]

class DemoTamperResponse(BaseModel):
    message: str
    tampered_block_index: int
    is_valid: bool
    details: str

class DemoResetResponse(BaseModel):
    message: str
    block_count: int
    is_valid: bool
    details: str

