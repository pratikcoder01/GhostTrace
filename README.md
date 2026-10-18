# GhostTrace — Blockchain Forensics & Threat Intelligence Platform

GhostTrace is a high-performance, modular blockchain forensics and threat intelligence backend engineered specifically for the **Ghost Attacks** hackathon challenge.

It delivers end-to-end multi-hop transaction tracing, graph pattern recognition (fan-out, fan-in, peeling chains, burst transactions), open-source intelligence (OSINT) correlation, machine learning-driven illicit transaction classification, and a custom cryptographic audit blockchain (**TraceChain**) for tamper-proof chain of custody.

---

## 1. Key Capabilities & Ghost Attacks Problem Alignment

1. **Deterministic Synthetic Investigation Scenario (`Operation Phantom Drain`)**:
   - Complete offline simulation of a cyber intrusion involving multi-stage fund drains:
     - Compromised victim treasury (`0xSIM_VICTIM_VAULT_01`)
     - Infiltrator collection wallet (`0xSIM_ATTACKER_INFILTRATOR`)
     - High-velocity burst peeling dispersal across 4 mule accounts
     - Layering and mixer tumble aggregation (`0xSIM_MIXER_HOP2_WASH_1`)
     - Cross-chain bridge obfuscation and centralized exchange hot wallet exit (`0xSIM_EXCHANGE_HOT_WALLET_EXIT`)
     - Benign commerce decoys to rigorously evaluate precision.
2. **NetworkX Directed Graph Engine**:
   - Inflow/outflow accounting, network density, and weakly connected community clustering.
   - Algorithmic detection of fan-out dispersal, fan-in aggregation, peeling chains, and temporal bursts (<300s).
   - Calibrated **Investigation Priority Scoring (0–100)** with reason codes and supporting transaction links (avoids uncalibrated legal/criminal claims).
3. **Reproducible Machine Learning Pipeline**:
   - Trained on the benchmark **Elliptic Bitcoin dataset** (46,564 labeled transactions across 49 chronological time steps).
   - Strict chronological validation (train: steps 1–34, test: steps 35–49) preventing temporal target leakage.
   - Comprehensive model comparison: `DummyBaseline`, `LogisticRegression`, `RandomForest`, and `XGBoost`.
   - **Champion Model**: `RandomForestClassifier` achieving **81.07% Illicit F1** and **91.52% Precision** on the held-out test split.
4. **Source-Backed OSINT Correlation**:
   - Ingests **5,633 addresses** and **9,906 scam domains** from CryptoScamDB.
   - Ingests telemetry signatures and anomaly indicators from Pegasus zero-click cyber intrusion feeds.
   - Exact normalized address matching with source URLs, timestamps, and provenance tracking.
5. **TraceChain Custom Audit Ledger**:
   - Hash-linked audit blockchain verifying chain of custody.
   - Proof-of-Work difficulty target (SHA-256 with canonical sorted JSON serialization).
   - Automatic tamper detection, link integrity validation, and persistent storage across server restarts.
6. **Strict Network Isolation**:
   - Enforces strict separation between Bitcoin, Ethereum, and Simulated demonstration environments to prevent erroneous entity attribution across disparate networks.

---

## 2. Dataset Inventory

| Dataset | Location | Records / Schema | Network | Origin |
|---|---|---|---|---|
| **Elliptic Bitcoin Dataset** | `backend/data/elliptic/elliptic_bitcoin_dataset/` | 203,769 transactions, 49 time steps, 165 features, 234,355 edges | Bitcoin | `elliptic_benchmark` |
| **CryptoScamDB Snapshot** | `backend/data/cryptoscamdb_snapshot.json` | 5,633 flagged scam addresses, 9,906 domains | Cross-chain (ETH/BTC) | `osint_snapshot` |
| **Synthetic Pegasus Dataset** | `backend/data/pegasus/synthetic_pegasus_dataset.csv` | 1,000 log events with IOC anomaly signatures | Threat Intel | `synthetic` |
| **Operation Phantom Drain** | `backend/data/synthetic_attack.json` | 15 transactions, 3 planted OSINT indicators, 1 multi-hop path | Simulated EVM | `synthetic` |

Original zip archives (`archive (4).zip`, `archive (5).zip`, `blacklist-master (1).zip`) are preserved completely untouched.

---

## 3. Machine Learning Benchmark Results

Evaluated on the held-out test partition (time steps 35 to 49) comprising 16,670 transactions (1,083 illicit, 15,587 licit):

| Model | Illicit Precision | Illicit Recall | Illicit F1 Score | Overall Accuracy | PR-AUC |
|---|---|---|---|---|---|
| **DummyBaseline (Most Frequent)** | 0.0000 | 0.0000 | 0.0000 | 0.9350 | 0.5325 |
| **Logistic Regression (Balanced)** | 0.1829 | **0.8790** | 0.3028 | 0.7371 | 0.2904 |
| **Random Forest (Champion)** | **0.9152** | 0.7276 | **0.8107** | **0.9779** | **0.7991** |
| **XGBoost (scale_pos_weight)** | 0.7227 | 0.7387 | 0.7306 | 0.9646 | 0.7987 |

**Model Artifacts Saved**:
- Model Bundle: `backend/models/model_randomforest_v1.0.0.joblib`
- Metadata Sidecar: `backend/models/model_randomforest_v1.0.0_metadata.json`

---

## 4. Execution Commands (Windows PowerShell)

### Step 1: Install Dependencies
```powershell
python -m pip install -r backend/requirements.txt
```

### Step 2: Run Automated Test Suite
```powershell
python -m pytest backend/tests -v
```

### Step 3: Run Model Training & Evaluation (Optional CLI)
```powershell
python -m backend.app.ml.train --dataset elliptic --max-rows 46564
```

### Step 4: Start the GhostTrace Backend API
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI Documentation will be live at:
**http://127.0.0.1:8000/docs**

---

## 5. REST API Endpoint Reference

### Health & Discovery
- `GET /api/health`: System health, database connectivity, and TraceChain height.
- `GET /api/data-sources`: Inventory of on-disk datasets and configured adapters.

### Investigation Cases
- `POST /api/cases`: Create case, ingest transaction records, correlate OSINT, and mine TraceChain audit blocks.
- `GET /api/cases`: List all active and archived cases.
- `GET /api/cases/{case_id}`: Retrieve case metadata, status, and summary statistics.
- `POST /api/cases/{case_id}/analyze`: Execute NetworkX graph analysis, burst calculation, peeling detection, and lead ranking.
- `GET /api/cases/{case_id}/graph`: Retrieve nodes, edges, degree metrics, flow sums, and community cluster IDs.
- `GET /api/cases/{case_id}/evidence`: Retrieve matched OSINT indicators with provenance and source URLs.
- `GET /api/cases/{case_id}/timeline`: Retrieve chronological event timeline with forensic anomaly flags.
- `GET /api/cases/{case_id}/report`: Full auditable forensic JSON report.

### TraceChain Audit Ledger
- `GET /api/chain/blocks`: List all mined blocks in the chain of custody.
- `GET /api/chain/verify`: Cryptographically verify genesis, link hashes, and proof-of-work.

### Machine Learning
- `GET /api/ml/status`: Retrieve champion model metadata, version, features, and benchmark metrics.
- `POST /api/ml/predict`: Submit 165-dimensional feature vector for real-time illicit risk classification.
- `POST /api/ml/train`: Trigger authenticated, bounded re-training pipeline.

---

## 6. Example API Usage

### Create a Case (Operation Phantom Drain)
```bash
curl -X POST http://127.0.0.1:8000/api/cases \
  -H "Content-Type: application/json" \
  -d '{
    "case_name": "Investigation Phantom Drain #042",
    "description": "Multi-hop cyber drain forensic analysis",
    "network": "simulated",
    "seed_addresses": ["0xSIM_VICTIM_VAULT_01"],
    "data_source": "synthetic_ghost_attack"
  }'
```

### Analyze Case & Retrieve Leads
```bash
curl -X POST http://127.0.0.1:8000/api/cases/{case_id}/analyze
```

### Verify TraceChain Integrity
```bash
curl http://127.0.0.1:8000/api/chain/verify
```

---

## 7. Security and Forensic Disclaimers

1. **Read-Only Access**: All blockchain adapters interact strictly in read-only mode. No private keys are ever handled, requested, or required.
2. **Offline-First**: The entire forensic MVP operates completely offline without paid subscriptions or external API dependencies.
3. **Calibrated Priority Scoring**: Scores are explicitly labeled as investigative priority rankings, not conclusive determinations of guilt or criminal liability.
4. **Network Boundaries**: Bitcoin, Ethereum, and Simulated demonstration networks are strictly partitioned to prevent invalid cross-network identity attribution.
