export type NetworkType = 'bitcoin' | 'ethereum' | 'simulated';

export type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Low' | 'Informational';

export type CaseStatus = 'created' | 'ingested' | 'analyzing' | 'analyzed' | 'failed';

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  tracechain: {
    block_height: number;
    integrity_valid: boolean;
    status: string;
  };
  database: string;
}

export interface DataSourceItem {
  id: string;
  name: string;
  network: string;
  format: string;
  available: boolean;
  path?: string;
  description: string;
}

export interface DataSourcesResponse {
  status: string;
  total_sources: number;
  data_sources: DataSourceItem[];
}

export interface CaseCreatePayload {
  case_name: string;
  description?: string;
  network: NetworkType;
  seed_addresses: string[];
  data_source: string;
}

export interface CaseSummary {
  total_volume?: number;
  unique_addresses?: number;
  clusters_detected?: number;
  high_risk_leads?: number;
  critical_leads?: number;
  [key: string]: any;
}

export interface CaseItem {
  case_id: string;
  case_name: string;
  description?: string;
  network: string;
  data_source: string;
  status: CaseStatus | string;
  seed_addresses: string[];
  tx_count: number;
  evidence_count: number;
  created_at: string;
  updated_at: string;
  summary?: CaseSummary;
}

export interface GraphNode {
  id: string;
  in_degree: number;
  out_degree: number;
  total_inflow: number;
  total_outflow: number;
  net_flow: number;
  tx_count: number;
  is_seed: boolean;
  osint_hits: number;
  cluster_id: number;
  priority_score: number;
  risk_level: RiskLevel | string;
  // Visual force graph helpers
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  val?: number;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  tx_id: string;
  amount: number;
  asset: string;
  timestamp: string;
}

export interface GraphDataResponse {
  case_id: string;
  network: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
  density: number;
  clusters_count: number;
}

export interface AnalysisLead {
  lead_id: string;
  address: string;
  priority_score: number;
  risk_level: RiskLevel;
  reason_codes: string[];
  supporting_tx_ids: string[];
  evidence_ids: string[];
  provenance: string;
  summary: string;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  description: string;
  tx_id?: string;
  addresses_involved: string[];
  amount?: number;
  asset?: string;
  flags: string[];
}

export interface EvidenceItem {
  evidence_id: string;
  case_id: string;
  indicator_type: string;
  indicator_value: string;
  category: string;
  subcategory?: string;
  description?: string;
  source_name: string;
  source_url?: string;
  provenance: string;
  created_at: string;
}

export interface AnalyzeCaseResponse {
  case_id: string;
  status: string;
  summary: Record<string, any>;
  ranked_leads: AnalysisLead[];
  timeline: TimelineEvent[];
  graph: GraphDataResponse;
}

export interface TraceChainBlock {
  index: number;
  timestamp: string;
  previous_hash: string;
  nonce: number;
  difficulty: number;
  hash: string;
  event_type: string;
  case_id?: string;
  payload: Record<string, any>;
}

export interface TraceChainVerifyResponse {
  is_valid: boolean;
  total_blocks: number;
  genesis_valid: boolean;
  link_integrity_valid: boolean;
  pow_valid: boolean;
  details: string;
  tampered_block_index?: number;
}

export interface MLStatusResponse {
  model_loaded: boolean;
  model_name?: string;
  version?: string;
  network?: string;
  algorithm?: string;
  features_count: number;
  metrics?: {
    accuracy?: number;
    precision?: number;
    recall?: number;
    f1_score?: number;
    auc_roc?: number;
    average_precision?: number;
    threshold?: number;
    validation?: Record<string, any>;
    test?: Record<string, any>;
    [key: string]: any;
  };
  evaluation_limitations: string;
  training_timestamp?: string;
}

export interface MLPredictRequest {
  tx_id?: string;
  features: number[];
  network?: NetworkType;
}

export interface MLPredictResponse {
  tx_id: string;
  prediction_label: 'illicit' | 'licit' | string;
  prediction_class: number;
  risk_score: number;
  model_version: string;
  network: string;
  confidence_explanation: string;
  limitations: string;
}

export interface InvestigationReportResponse {
  case_id: string;
  case_name: string;
  network: string;
  status: string;
  created_at: string;
  generated_at: string;
  executive_summary: string;
  data_origin_and_provenance: string;
  network_separation_guarantee: string;
  transaction_statistics: {
    total_tx_count?: number;
    total_volume?: number;
    unique_senders?: number;
    unique_receivers?: number;
    avg_tx_amount?: number;
    burst_count?: number;
    [key: string]: any;
  };
  ranked_leads: AnalysisLead[];
  timeline: TimelineEvent[];
  evidence_items: EvidenceItem[];
  tracechain_audit: {
    is_valid: boolean;
    total_blocks: number;
    verification_status: string;
    tampered_block_index?: number;
    blocks_summary: Array<{
      index: number;
      event_type: string;
      timestamp: string;
      hash: string;
      previous_hash: string;
      difficulty: number;
    }>;
  };
  ml_assessment?: {
    model_version?: string;
    algorithm?: string;
    active_threshold?: number;
    evaluation_basis?: string;
    disclaimer?: string;
    [key: string]: any;
  };
  limitations_and_disclaimer: string;
}

// ----------------- Real-Time & Live Ingestion Types -----------------

export interface LiveProviderStatus {
  provider_name: string;
  network: string;
  connected: boolean;
  connection_state: string;
  last_received_block?: number;
  last_processed_block?: number;
  ingestion_lag: number;
  events_received_count: number;
  events_persisted_count: number;
  error_count: number;
  last_event_time?: string;
  is_simulated: boolean;
}

export interface LiveStatusResponse {
  status: string;
  provider: LiveProviderStatus;
  queue_size: number;
  latest_analysis_time?: string;
  osint_sources: Record<string, any>;
  model_version: string;
  active_threshold: number;
}

export interface WebSocketLiveEvent {
  event_id: string;
  type: 'connection.ack' | 'transaction.new' | 'graph.updated' | 'lead.created' | 'forecast.updated' | 'source.status' | 'audit.updated' | 'job.status' | string;
  timestamp: string;
  case_id?: string;
  data: Record<string, any>;
}

export interface SimulateEventRequest {
  case_id?: string;
  from_address?: string;
  to_address?: string;
  amount?: number;
  asset?: string;
  tx_type?: 'native' | 'erc20';
  is_removed?: boolean;
}

// ----------------- Matrices, Exposure, Forecast & Demo Types -----------------

export interface FeatureMatrixItem {
  fanIn: number;
  fanOut: number;
  meanTransferAmt: number;
  totalOut: number;
  hopDepth: number;
}

export interface WalletItem {
  id: string;
  address: string;
  label: string;
  category: string;
  notes?: string;
  inflow?: number;
  outflow?: number;
  tx_count?: number;
  risk_level?: string;
}

export interface MatricesResponse {
  flowMatrix: Record<string, Record<string, number>>;
  activityMatrix: Record<string, Record<string, number>>;
  bins: string[];
  walletIds: string[];
  featureMatrix: Record<string, FeatureMatrixItem>;
  wallets: WalletItem[];
}

export interface ExposurePathItem {
  path: string;
  amount: number;
  type: string;
}

export interface CandidateExitItem {
  walletId: string;
  address: string;
  label: string;
  observedAmount: number;
}

export interface ExposureResponse {
  observedSourceOutflow: number;
  observedSourceOutflowUSD: number;
  asset: string;
  candidateExitAmount: number | null;
  candidateExits: CandidateExitItem[];
  pathSummary: ExposurePathItem[];
  projectionStatus: string;
  projectionNote: string;
  doubleCountingWarning: string;
}

export interface ForecastDayItem {
  day: string;
  volume: number;
  probability: number;
}

export interface ForecastRouteItem {
  route: string;
  volume: number;
  risk: string;
}

export interface CashoutForecastResponse {
  case_id: string;
  total_initial_compromised: number;
  identified_exit_volume: number;
  unpeeled_floating_balance: number;
  cashout_probability: number;
  exit_gate_interactions: number;
  status: string;
  forecast_by_day: ForecastDayItem[];
  routes: ForecastRouteItem[];
  notice: string;
}

export interface CaseLeadsResponse {
  case_id: string;
  total: number;
  leads: AnalysisLead[];
}

export interface DemoTamperResponse {
  message: string;
  tampered_block_index: number;
  is_valid: boolean;
  details: string;
}

export interface DemoResetResponse {
  message: string;
  block_count: number;
  is_valid: boolean;
  details: string;
}

