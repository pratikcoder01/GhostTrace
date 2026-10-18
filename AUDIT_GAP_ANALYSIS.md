# GhostTrace Real-Time Architecture Audit & Gap Analysis

## 1. Existing System Audit

| Component | Current Implementation | Status | Real Data vs Synthetic |
|---|---|---|---|
| **Backend Framework** | FastAPI (Python 3.11) with Uvicorn | Working | Real |
| **Database** | SQLite via SQLAlchemy 2.0 (`CaseModel`, `TransactionModel`, `EvidenceModel`, `TraceChainBlockModel`, `MLModelRecordModel`) | Working | Real storage engine |
| **Existing Ingestion** | `SyntheticAttackAdapter` (JSON fixture), `EllipticDatasetAdapter` (Bitcoin CSV), `EthereumAdapter` (Etherscan REST API) | Working | Synthetic fixture (`synthetic_ghost_attack`), Historical Benchmark (`elliptic`), Real read-only REST (`Etherscan`) |
| **TraceChain** | Custom Proof-of-Work cryptographic audit blockchain with block mining & SHA-256 link verification | Working (23 tests passing) | Real cryptographic logic |
| **ML Engine** | `RandomForest v1.1.0` (165 features, registered threshold 0.42, trained on Elliptic Bitcoin dataset) | Working | Real trained model artifact on disk (`model_randomforest_v1.1.0.joblib`) |
| **OSINT Service** | `CryptoScamDBAdapter` (local snapshot JSON), `SyntheticAttackAdapter` planted indicators, Pegasus CSV | Working | Local snapshot + synthetic fixture |
| **Graph Forensics** | NetworkX `BlockchainAnalysisEngine` (burst detection, peeling chains, clusters, lead priority scoring) | Working | Real NetworkX algorithms |
| **WebSocket** | None currently implemented (`/ws/live` missing) | Missing | Gapped |
| **Real-time Ingestion** | No WebSocket listener, no Alchemy WS, no ERC-20 log decoders, no block cursor, no reorg handler | Missing | Gapped |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Lucide icons, React Force Graph 2D, Recharts | Working (build passes) | Real SPA UI |

## 2. Identified Gaps & Target Implementation Plan

### Phase 2: Live Blockchain Ingestion
- **Provider Abstraction**: Create `BlockchainProvider` interface with `AlchemyWebSocketProvider`, `EtherscanProvider`, and safe deterministic `SimulatorProvider`.
- **Network Support**: Ethereum mainnet/sepolia configuration with chain ID, block headers subscription, and ERC-20 `Transfer(address,address,uint256)` log decoding.
- **Normalization & Idempotency**: Normalization for amounts (wei / decimals), timestamps (ISO-8601 UTC), addresses (case-normalized), hashes, and block numbers.
- **Resilience**: Exponential backoff reconnects, persistent `BlockCursorModel`, bounded backfill, and chain reorganization (`removed: true`) handling.
- **Observability**: Health metrics, lag tracking, error counters, and explicit provider state.

### Phase 3: Idempotent Event Processing & Storage
- **Event Pipeline**: Receive -> Validate/Normalize -> Persist Raw (`RawBlockchainEventModel`) -> Persist Normalized (`TransactionModel`) -> Correlate Open Cases -> Enqueue Async Analysis -> TraceChain Audit -> WebSocket Publish.
- **Asynchronous Queue**: Bounded `asyncio.Queue` with background worker preventing event loss and keeping WebSocket receive loop unblocked.

### Phase 4: Real-time Investigation Analysis
- **Graph Updates**: Incremental node and edge additions, recalculating temporal bursts, peeling patterns, and clusters.
- **Feature Schema Validation & ML**: Validate against exact 165-feature schema required by `RandomForest v1.1.0`. For non-calibrated cross-chain or insufficient feature inputs, return an explicit `unavailable` status rather than fabricating predictions. Enforce threshold `0.42`. Distinguish statistical model risk scores from verified OSINT malicious labels.
- **Forecasting & Metrics**: Real-time cashout probability, exit gate interactions, and priority score updates.

### Phase 5: Live OSINT
- **Collector Service**: `LiveOSINTCollector` supporting public threat intelligence (CryptoScamDB live/snapshot, PhishFort, URLhaus), caching with content hashes, rate-limiting, and clear distinction between live and cached results.

### Phase 6: Real-time Frontend Updates
- **WebSocket Endpoint**: `/ws/live` supporting connection health, heartbeats, case subscriptions, and typed events (`transaction.new`, `graph.updated`, `lead.created`, `forecast.updated`, `source.status`, `audit.updated`, `job.status`).
- **Frontend Integration**: `WebSocketContext` with auto-reconnect, top-bar live indicator, and real-time incremental updates to Transaction Graph, Dashboard, Leads, and Triage.

### Phase 7: API and Observability
- Endpoints: `GET /api/live/status`, `GET /api/health`, `GET /api/data-sources`, `GET /api/ml/status`, `POST /api/cases/{id}/analyze`, `POST /api/live/simulate-event`.

### Phase 8 & 9: Testing & Verification
- Unit & integration test suite covering normalization, deduplication, cursor recovery, reorgs, queue failure, and WebSocket delivery.
- Opt-in live smoke test with real credentials.
- End-to-end verification and ZIP packaging.
