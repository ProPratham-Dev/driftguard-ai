# DRIFTGUARD AI 🛡️
### NEUROFORGE 2026 – The Moving Target: Adaptive Real-Time Fraud Detection System

**DriftGuard AI** is an adaptive, real-time cybersecurity and fraud prevention platform designed to solve the "Moving Target" problem in financial transaction security. While traditional static fraud detection models degrade rapidly when adversarial fraudsters switch their strategies, DriftGuard AI dynamically detects **concept drift** and adapts via **online machine learning** (`partial_fit`) using newly verified transaction feedback.

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.11+
- Node.js v18+ and npm (for frontend in Phase 5)

### 1. Backend Setup & Virtual Environment
```bash
# Create virtual environment
py -3.11 -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Generate Synthetic Dataset & Train Baseline Models
Execute the end-to-end Phase 2 ML training and benchmark pipeline:
```bash
python -m backend.app.ml.train
```
This script will:
1. Generate `backend/data/transactions_12k.csv` (12,000 realistic transactions with historical and evasion fraud regimes).
2. Fit `FraudFeaturePipeline` without target leakage.
3. Train `FixedFraudModel` (SGDClassifier baseline).
4. Initialize `AdaptiveFraudModel` (Online SGDClassifier with `partial_fit`).
5. Chronologically evaluate both models across both regimes.
6. Persist models and scalers into `backend/models_saved/`.
7. Register model versions in the SQLite database (`driftguard.db`).

### 3. Run Automated Tests
```bash
pytest -v
```

---

## 📊 Empirical Benchmarks (Phase 2 Results)

All metrics are measured on identical chronological test records:

| Evaluation Stage | Model Type | Accuracy | Precision | Recall | F1-Score | False Negative Rate (FNR) |
|---|---|---|---|---|---|---|
| **Historical Holdout** (N=1,700) | Fixed Baseline | 100.0% | 100.0% | 100.0% | 1.0000 | 0.00% |
| **Historical Holdout** (N=1,700) | Adaptive Baseline | 100.0% | 100.0% | 100.0% | 1.0000 | 0.00% |
| **Concept Drift Stream** (N=4,800) | **Fixed Model (Decayed)** | 91.29% | 100.0% | **42.02%** | **0.5918** | **57.98%** |
| **Concept Drift Stream** (N=4,800) | **Adaptive Model (Online)**| **99.88%** | 100.0% | **99.17%** | **0.9958** | **0.83%** |
| **Post-Adaptation Steady State** (Last 1,000) | Fixed Model | 91.70% | 100.0% | 43.54% | 0.6066 | 56.46% |
| **Post-Adaptation Steady State** (Last 1,000) | Adaptive Model | **100.0%** | 100.0% | **100.0%** | **1.0000** | **0.00%** |

> **Key Finding**: When fraudsters adapt to micro-velocity nocturnal evasion attacks, the fixed model's False Negative Rate spikes to **57.98%** (failing to catch almost 6 out of 10 frauds). Through delayed verified feedback learning, the adaptive model achieves a **+56.46% Recall Gain** and reduces False Negatives to **0.00%**.

---

## 🔒 Security & Architecture Guarantees
- **No Ground-Truth Exposure**: Labels are never provided to models at prediction time. Online updates occur strictly after verified feedback arrives.
- **Strict Separation**: Fixed and Adaptive models maintain independent weights and memory spaces.
- **Rollback Resilience**: Adaptive model maintains version checkpoints enabling immediate rollbacks if candidate performance degrades.

---

## 🔬 Concept Drift Detection Methodology (Phase 3)

DriftGuard AI implements the **Adaptive Sliding-Window Statistical Drift Detector (ASW-DD)**:
- **Error Signal Monitoring**: Monitors binary prediction errors $e_i \in \{0, 1\}$ ($e_i = 1$ if $\hat{y}_i \neq y_i$) generated when delayed verified labels are compared with recorded predictions.
- **Window Partitioning**: Maintains a rolling historical reference window ($W_{\text{ref}}$, up to 400 samples) and an adaptive recent window ($W_{\text{recent}}$, past 80 samples).
- **Two-Sample Statistical Test**: Evaluates difference in misclassification rates using a two-sample proportion $Z$-test and error delta ($\Delta = p_{\text{recent}} - p_{\text{ref}}$).
- **Noise Immunity**: Single isolated classification errors do not trigger alerts; drift requires sustained elevation ($n_{\text{recent}} \ge 30$) with statistical significance ($Z \ge 2.0$ for WARNING, $Z \ge 3.0$ for CRITICAL).
- **Severity Tiers**:
  - `NORMAL`: Stable error rates ($\Delta < 0.06$).
  - `WARNING`: Significant error elevation ($\Delta \ge 0.06, Z \ge 2.0, p < 0.023$).
  - `CRITICAL`: Severe performance drop ($\Delta \ge 0.12, Z \ge 3.0, p < 0.0013$).

---

## 🔄 Adaptive Learning Lifecycle & Candidate Promotion

1. **Transaction Ingestion**: Ingests features, calculates inference scores for both Fixed and Adaptive models, and persists predictions in SQLite. Ground-truth labels are never exposed during inference.
2. **Delayed Feedback Arrival**: Operations team or automated dispute systems submit verified ground-truth labels via `POST /api/learning/feedback`.
3. **Drift Assessment**: Error signals update ASW-DD. If drift is detected, database alerts and audit logs are recorded.
4. **Candidate Model Training**: A candidate model is cloned from the active adaptive model and updated on the first 75% of available verified feedback.
5. **Holdout Validation**: The candidate is tested on the chronologically remaining 25% holdout.
6. **Promotion Criteria**:
   - Candidate Recall $\ge$ Active Model Recall.
   - Candidate F1-Score $\ge$ Active Model F1 $- 0.02$.
   - Candidate False Positive Rate (FPR) $\le 0.08$.
7. **Rollback Safety**: The previous active model is preserved in memory and disk, allowing immediate zero-downtime rollback via `POST /api/learning/rollback`.

---

## 🌐 API Endpoints (Phases 1–3)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check verifying core services. |
| `GET` | `/api/status` | System KPIs, transaction counts, active model versions. |
| `POST` | `/api/transactions/predict` | Predict incoming transaction features and record predictions. |
| `GET` | `/api/drift/status` | Current drift detector status, error rates, and severity. |
| `GET` | `/api/drift/events` | Chronological log of detected drift events. |
| `GET` | `/api/models/versions` | Audited model version history and benchmark metrics. |
| `POST` | `/api/learning/feedback` | Ingest verified ground truth for a transaction; triggers drift and candidate training. |
| `POST` | `/api/learning/rollback` | Revert adaptive model to previous stable version. |


