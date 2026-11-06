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
