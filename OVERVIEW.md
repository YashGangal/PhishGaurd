# 🛡️ PhishGuard — Comprehensive Project Overview & Architecture Guide

> **Intelligent Phishing Website Detection System using Machine Learning, Explainable AI (SHAP), and FastAPI**

---

## 📌 Executive Summary

**PhishGuard** is an end-to-end, enterprise-grade cybersecurity intelligence system designed to detect phishing websites in real time using structural URL analysis and HTML content characteristics. Unlike conventional threat prevention systems that rely on slow, static blacklists or expensive third-party APIs, PhishGuard utilizes a custom-trained **Supervised Machine Learning Pipeline** combined with **Explainable AI (SHAP)** to deliver high-accuracy classification with human-interpretable risk breakdown.

The system features a **FastAPI backend**, an **Obsidian Vault-themed React frontend**, an **Explainable AI Engine**, an **Automated Scraper**, and a **Durable SQLite Database** for scan logs and model auditing.

---

## 🎯 Problem Statement & Objectives

### The Challenge
Phishing attacks are responsible for over 80% of reported security incidents worldwide. Modern phishing campaigns deploy short-lived, dynamically generated zero-day domain names that bypass traditional IP/domain blacklists before security feeds can index them. Existing commercial solutions often require expensive API subscriptions, introduce latency, or operate as black boxes without explaining why a site is flagged.

### Project Objectives
- 🚀 **Real-time URL Classification**: Analyze and classify target URLs as **Legitimate** or **Phishing** in under 500ms.
- 🔬 **25-Feature Hybrid Vector**: Extract 18 URL-side signals (structure + reputation/keyword) and 7 page/redirect signals without third-party threat APIs.
- 🎯 **≥95% Detection Accuracy**: Evaluate and compare multiple ML models (Random Forest, XGBoost, Logistic Regression, SVM) to select the optimal model.
- 💡 **Explainable AI (XAI)**: Quantify contributing threat factors using SHAP values to explain every verdict.
- 🛡️ **Graceful System Degradation**: Automatically fallback to URL-only feature extraction if a target website is offline or unreachable.
- 📊 **Forensic Dashboard & Analytics**: Provide security analysts with scan history, filterable records, analytics metrics, and PDF export capabilities.

---

## 🎨 Visual Identity & Design Philosophy ("Obsidian Vault")

PhishGuard avoids generic SaaS templates and flashy cyberpunk clichés in favor of a **high-end security audit posture**:

- **Canvas Background**: Deep warm obsidian `#08080f`
- **Cards & Surfaces**: Dark slate `#0f0f1a` with 1px structural hairline borders `#1e1e33`
- **Safe Verdict Accent**: Precision Mint `#00e5c0`
- **Phishing Verdict Accent**: Coral Red `#ff5a5a`
- **Warning Indicator**: Muted Gold `#f0c040`
- **Typography**: Clean `Inter` for UI elements paired with `JetBrains Mono` for URLs, risk scores, and data values.

---

## 🏛️ System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                   │
│                 React 18 + Vite + Tailwind CSS                          │
│     Overview  │  Scan URL  │  History  │  Analytics  │  Model & API         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP (fetch / REST)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND LAYER                           │
│                                                                         │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐  │
│  │    predict.py    │    │    history.py    │    │   model_info.py   │  │
│  │   POST /predict  │    │ GET/DELETE       │    │ GET /model-info   │  │
│  │                  │    │ /history         │    │ GET /health       │  │
│  └────────┬─────────┘    └────────┬─────────┘    └─────────┬─────────┘  │
│           │                       │                        │            │
│           ▼                       ▼                        ▼            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         SERVICE LAYER                             │  │
│  │                                                                   │  │
 │  │  feature_engineering.py   (18 URL-side + 7 page-signal extractors)    │  │
│  │  scraper.py              (HTML Async Scraper, 4s Timeout)        │  │
│  │  prediction.py           (Cached Singleton ML Model Inference)    │  │
│  │  explainability.py       (SHAP Top-5 Contributing Signals)        │  │
│  └────────────────┬──────────────────┬───────────────────────────────┘  │
│                   │                  │                                  │
│         ┌─────────┴────────┐         └──────────┐                       │
│         ▼                  ▼                    ▼                       │
│  ┌──────────────┐   ┌─────────────┐     ┌──────────────┐                │
│  │   ML Model   │   │ SQLite DB   │     │ Swagger UI   │                │
│  │ (RandomForest│   │ ScanHistory │     │  /docs       │                │
│  │  / XGBoost)  │   │ ModelMeta   │     │              │                │
│  └──────────────┘   └─────────────┘     └──────────────┘                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📄 Application Pages & User Experience

PhishGuard consists of **6 primary pages/screens**, each designed for a specific workflow in the threat analysis lifecycle:

### 1. 🏠 Overview Page (`/`)
- **Executive Summary Header**: Introduces PhishGuard with system health status badge (Online/Offline) and active ML model chip.
- **Quick Scan Bar**: Compact URL submission input allowing instant analysis from the landing view.
- **Latest Scan Card**: Summarizes the most recent scan result (URL, verdict badge, confidence score, and time elapsed).
- **System Health Monitor**: Live ping status showing database connection state and active model version.

### 2. 🔍 Scan URL Workspace (`/scan`) — *Primary Analysis Core*
- **URL Input Panel**: Formatted monospace input field with client-side URL validation and immediate error feedback.
- **EKG Scan Line Animation**: A 1px horizontal mint pulse line that traverses the panel during active analysis.
- **Verdict Display**: High-impact, asymmetric verdict block:
  - **Verdict Tag**: `PHISHING DETECTED` (Coral Red with Octagon warning icon) or `URL IS SAFE` (Mint Green with Shield check icon).
  - **Confidence Gauge**: Precise ML confidence percentage (e.g., `97.3%`).
  - **Risk Score Meter**: Asymmetric score (`0–100`) mapped to risk tiers:
    - 🟢 `0 - 33`: Low Risk (Safe)
    - 🟡 `34 - 66`: Medium Risk (Caution)
    - 🔴 `67 - 100`: High Risk (Danger)
- **Degradation Indicator**: Displays `"Analysis based on URL structure only"` if target site HTML was unreachable.
- **Contributing Signal List (SHAP Evidence)**: Top 5 feature explanations showing feature name, raw value, risk impact bar (`+82%`), direction (`increases_risk` vs `decreases_risk`), and plain-English explanation.
- **Full 25-Feature Accordion**: Expandable breakdown of all 18 URL-side and 7 page/redirect extracted values.

### 3. 📜 Scan History Page (`/history`)
- **Global Search & Filtering**: Instant URL/domain text search with filtering pill buttons (`All`, `Legitimate`, `Phishing`).
- **Data Table Layout**: Displays URL (truncated with copy icon), Verdict pill badge, Risk Score, Confidence %, and Timestamp.
- **Action Controls**:
  - `View`: Opens full scan detail modal for any historical scan.
  - `Delete`: Triggers confirmation overlay to safely remove a scan record.
- **CSV Data Export**: Button to download full scan history as a structured `.csv` file.
- **Pagination**: Monospace pagination bar (`Page X of Y`).

### 4. 📈 Analytics Page (`/analytics`)
- **Key Metrics Overview**:
  - `Total Scans`: Total volume of processed scans.
  - `Phishing Detected`: Count and percentage of malicious URLs.
  - `Average Confidence`: Overall confidence rating of system predictions.
  - `Model Accuracy`: Benchmark performance of the deployed model.
- **Model Evaluation Matrix**: Static comparison table comparing Logistic Regression, Random Forest, XGBoost, and SVM across Accuracy, Precision, Recall, F1-Score, and ROC-AUC.
- **Visual Performance Artifacts**:
  - `Confusion Matrix Heatmap`: Visual breakdown of True Positives, True Negatives, False Positives, and False Negatives.
  - `ROC Curves`: Multi-model ROC comparison chart.
  - `Feature Importance Bar Chart`: Distribution of top features driving model decisions.

### 5. ⚙️ Model & API Page (`/model-api`)
- **Active Model Metadata**: Displays loaded algorithm name, training timestamp, dataset size (e.g., 1,225,480 URLs), and evaluation metrics.
- **API Endpoint Registry**: Detailed interactive card list for all backend routes:
  - `POST /predict`: Submit URL for analysis.
  - `GET /history`: Fetch paginated scan records.
  - `DELETE /history/{id}`: Delete a scan entry.
  - `GET /model-info`: Retrieve model performance metrics.
  - `GET /health`: Liveness probe.
- **Embedded Swagger UI**: Interactive iframe embedding FastAPI's auto-generated `/docs` interface for live API testing.

### 6. 🖨️ Detailed Scan Report Page (`/report`)
- **Print & PDF-Optimized View**: Clean, white-background, high-contrast layout formatted for browser print-to-PDF export.
- **Report Sections**:
  1. Audit Header & Serial Timestamp
  2. Target URL & Domain Info
  3. Executive Verdict & Risk Level
  4. Top 5 Forensic Evidence Signals (SHAP)
  5. Complete 25-Feature Matrix Table
  6. Model Signature & System Verification Footer

---

## 🔬 Feature Engineering Matrix (25 Features)

### A. URL Structural Features (15 Always-Available Features)
| # | Feature | Type | Extraction Logic | Threat Signal |
|---|---|---|---|---|
| 1 | `url_length` | `int` | `len(url)` | Abnormally long URLs hide actual destination |
| 2 | `domain_length` | `int` | `len(domain)` | Typosquatting/spoofed brand domains |
| 3 | `num_dots` | `int` | count of `.` | Excessive subdomains (`login.paypal.com.evil.com`) |
| 4 | `num_hyphens` | `int` | count of `-` | Used to mimic legit domain names |
| 5 | `num_digits` | `int` | count of `[0-9]` | Random generated string domains |
| 6 | `num_subdomains` | `int` | count of subdomains | Deep subdomain nesting |
| 7 | `has_https` | `bool` | `scheme == "https"` | Absence indicates unencrypted HTTP transport |
| 8 | `has_ip_address` | `bool` | Regex dotted IP | Raw IP hostnames bypass domain reputation |
| 9 | `has_at_symbol` | `bool` | `"@" in url` | Browser treats `@` as user-info redirect trick |
| 10 | `has_double_slash_redirect` | `bool` | `"//"` after pos 7 | Redirect abuse in path |
| 11 | `is_shortened_url` | `bool` | Match shortener list | Obfuscates destination domain (bit.ly, t.co) |
| 12 | `num_suspicious_chars` | `int` | count `@ % _ = &` | Special char encoding tricks |
| 13 | `url_entropy` | `float` | Shannon entropy | High randomness in URL path/params |
| 14 | `has_suspicious_tld` | `bool` | Match high-risk TLDs | `.xyz`, `.top`, `.tk`, `.gq`, `.ml`, etc. |
| 15 | `path_length` | `int` | `len(path)` | Deep path structure hiding payloads |

### B. HTML Content & DOM Features (7 Webpage Features)
| # | Feature | Type | Extraction Logic | Threat Signal |
|---|---|---|---|---|
| 16 | `has_iframe` | `bool` | `<iframe>` tag present | Used to load phishing form inside clean frame |
| 17 | `redirect_count` | `int` | Count HTTP redirects | Multi-hop redirection chains |
| 18 | `num_external_links` | `int` | Foreign domain `<a href>` | Phishing sites copy asset links from real site |
| 19 | `form_action_suspicious` | `bool` | Blank/IP/foreign form action | Credential harvesting sent to third-party server |
| 20 | `has_javascript_events` | `bool` | `onmouseover`/`onload` tricks | Right-click disable or status bar spoofing |
| 21 | `has_popup_window` | `bool` | `window.open()` in script | Fake login prompt popups |
| 22 | `has_hidden_elements` | `bool` | `display:none` or `opacity:0` | Hidden text/links used for SEO/credential traps |

### C. Reputation & Keyword Features (3 URL-Side Features, appended v2)
| # | Feature | Type | Extraction Logic | Threat Signal |
|---|---|---|---|---|
| 23 | `domain_in_top_list` | `bool` | Registrable domain in `ml/data/reputation_top1m.csv` (Cisco Umbrella top-1M) | Instant exoneration of github/wikipedia/google class |
| 24 | `has_auth_keyword` | `bool` | `login\|signin\|verify\|account\|password\|2fa\|otp` in subdomain/path/query | Auth-flow lure |
| 25 | `keyword_domain_mismatch` | `bool` | Brand keyword (`paypal\|apple\|google\|…`) in subdomain/path but NOT in the registrable domain | The true phish shape (`evil.com/paypal-login`) |

---

## 🤖 Machine Learning Pipeline & Model Benchmark Results

The system evaluates four candidate supervised learning algorithms on a dataset of **1,225,534 URLs** (see `phishing_detector/backend/ml/comparison_report.json`, trained 2026-09-14 — this table mirrors that report):

### Performance Comparison Matrix

| Algorithm | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Status / Role |
|---|---|---|---|---|---|---|
| 🌲 **Random Forest** | **93.55%** | **92.34%** | **90.51%** | **91.41%** | **0.9827** | 🏆 **SELECTED BEST MODEL** |
| ⚡ **XGBoost** | 90.48% | 88.16% | 86.52% | 87.33% | 0.9652 | Runner-up candidate |
| 📈 **Logistic Regression** | 79.68% | 71.85% | 76.32% | 74.01% | 0.8811 | Interpretable Baseline |
| 🎯 **SVM (calibrated linear)** | 79.16% | 71.37% | 75.19% | 73.23% | 0.8799 | Benchmark comparison |

### Model Selection Rationale
**Random Forest** was selected as the active production model because it achieved the highest **F1-Score (91.41%)** and **ROC-AUC (0.9827)** among all candidates, balancing low false-positive rates with high threat recall while seamlessly integrating with SHAP `TreeExplainer` for local explanations.

### Calibration (shipped, v3)
Raw forest scores rank well but are overconfident, so the shipped artifact
is isotonic-calibrated (`ml/calibrate.py`, no retrain): prefit on 122,553
held-out rows recovered deterministically from the training run's own test
split (reproduced to 5e-05; wrong-split controls deviate 1e-02). Held-out
effect: Brier 0.0493 → 0.0465, log-loss 0.1702 → 0.1563, F1 0.9145 → 0.9135
(precision 92.5% → 94.6%, recall 90.5% → 88.3%), ROC-AUC flat at 0.9829.
`/model-info` reports these calibrated numbers. The decision threshold
stays 0.5 (the frozen gate assumes it); measured alternatives and the
abstain-band analysis live in `ml/calibration_report.json`.

---

## 💻 Tech Stack & System Specifications

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.11+ / Node.js 20.19+ | Runtime environment |
| **Backend Framework** | FastAPI (ASGI / Uvicorn) | High-performance async REST API |
| **Machine Learning** | Scikit-learn, XGBoost, SHAP | Model training, inference, and explainability |
| **Data Processing** | Pandas, NumPy, tldextract | Data manipulation & domain parsing |
| **Database & ORM** | SQLite / SQLAlchemy | Persistent storage for scan history & metadata |
| **Web Scraping** | BeautifulSoup4, Requests | Async HTML DOM feature extraction |
| **Frontend Framework** | React 18, Vite | Component-based interactive UI |
| **Styling & Icons** | Tailwind CSS, Lucide Icons | Obsidian Vault design system styling |
| **Charts & Visuals** | Custom SVG schematics | Analytics charts rendered without a chart dependency |
| **Validation** | Pydantic v2 | Strict API request/response schema enforcement |

---

## 🗄️ Database Schema & API Specifications

### Database Tables (SQLite)

#### 1. `scan_history` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `url` (VARCHAR 2048, Indexed)
- `domain` (VARCHAR 255, Indexed)
- `prediction` (VARCHAR 20) — `"phishing"` | `"legitimate"`
- `confidence` (FLOAT) — `0.0` to `1.0`
- `risk_score` (INTEGER) — `0` to `100`
- `risk_level` (VARCHAR 10) — `"low"` | `"medium"` | `"high"`
- `features_json` (TEXT) — Encoded 25-feature dictionary
- `top_features_json` (TEXT) — Encoded top-5 SHAP signals
- `model_version` (VARCHAR 50, Foreign Key)
- `scanned_at` (DATETIME, Indexed)

#### 2. `model_metadata` Table
- `id` (INTEGER, Primary Key)
- `model_name` (VARCHAR 50)
- `version` (VARCHAR 50, Unique)
- `accuracy`, `precision`, `recall`, `f1_score`, `roc_auc` (FLOAT)
- `dataset_size` (INTEGER)
- `file_path` (VARCHAR 255)
- `is_active` (BOOLEAN, Indexed)

---

## 🛠️ Quickstart & Local Setup Guide

### 1. Backend Setup (FastAPI — Python 3.11, uv)
```powershell
# Navigate to backend directory
cd phishing_detector/backend

# Create & activate virtual environment (uv-managed; .python-version pins 3.11)
uv python install 3.11
uv venv --python 3.11 .venv
.\.venv\Scripts\Activate.ps1  # Windows (source .venv/bin/activate on Linux/macOS)

# Install dependencies (production + dev/test tooling)
uv pip install --python .venv\Scripts\python.exe -r requirements.txt -r requirements-dev.txt

# Copy the environment template (real .env stays local-only, gitignored)
Copy-Item .env.example .env

# Run database initialization and model training (if needed)
python -m ml.train

# Start FastAPI dev server
uvicorn app.main:app --reload --port 8000
```
- Versions in `requirements.txt` are `==`-pinned on purpose: the pickled model artifact can become unloadable (or silently change predictions) across sklearn/XGBoost versions — retrain before upgrading. See `phishing_detector/backend/README.md`.
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Frontend Setup (React + Vite)
```bash
# Navigate to frontend directory (or root if integrated)
npm install

# Start Vite development server
npm run dev
```
- Application Web Dashboard: [http://localhost:5173](http://localhost:5173)

---

## 📂 Project Structure Map

```text
PhishGuard/
├── README.md                             # Start here — install, run, train, test
├── OVERVIEW.md                             # Canonical project overview (this file)
├── ACCURACY-REPORT.md                      # 24-URL live accuracy report (v1 model era)
├── accuracy-test-results.json              # Raw per-URL results backing that report
├── IMPROVEMENT-PLAN.md                     # Accuracy roadmap (Tier 1: v2 retrain)
├── phishguard-ui-plan-INTEGRATED-v2.md     # UI/UX specification & design system
├── FIRETEST-REPORT.md                      # Latest live-fire test report (2026-09-14)
├── firetest-results-v2.json                # Current model live-fire results
├── firetest-urls.json                      # Live-fire input URL set
├── archive/                                # Superseded docs & historical evidence
│   ├── project_overview.md                 # Early abstract (superseded by OVERVIEW.md)
│   ├── Project Prompt.txt                  # v1 genesis build order (superseded)
│   ├── Frontend-Prompt.md                  # Generic agent prompt (not PhishGuard-specific)
│   ├── 06_frontend_component_tree.md        # Early component plan (superseded by INTEGRATED-v2)
│   └── firetest-results-v1-heuristic.json  # Heuristic-era results (6/15, kept as evidence)
│
│   NOTE: training data (*.csv), the trained artifact (*.pkl), the SQLite
│   database (*.db), and backend/.env are local-only and gitignored — they
│   are regenerated/documented via the backend README, never committed.
│
├── files/                                  # Architectural design specs
│   ├── 01_system_architecture.md
│   ├── 02_database_schema.md
│   ├── 03_api_contract.md                # Canonical API contract
│   ├── 04_feature_engineering_spec.md
│   └── 05_model_comparison_matrix.md     # Selection method (numbers superseded by comparison_report.json)
│
└── phishing_detector/
    └── backend/                            # FastAPI backend service
        ├── requirements.txt
        ├── phishguard.db                   # SQLite database file (local-only, gitignored)
        ├── models/
        │   └── best_model.pkl              # Trained artifact (local-only, gitignored)
        ├── ml/                             # Machine learning scripts
        │   ├── train.py                    # Training & evaluation script
        │   ├── calibrate.py                # Isotonic calibration (no retrain)
        │   ├── evaluate.py                 # Benchmarking script
        │   ├── calibration_report.json     # Calibration metrics + thresholds
        │   ├── data/
        │   │   ├── eval_gate.json          # Frozen 40-URL acceptance set
        │   │   └── hard_negatives.csv      # Curated top-site logins (versioned)
        │   └── comparison_report.json      # Trained models comparison metrics
        ├── eval_gate.py                    # Frozen acceptance gate (exit 0 = ship)
        └── app/                            # Application package
            ├── main.py                     # FastAPI entry point & app factory
            ├── core/                       # Config & logging
            ├── models/                     # SQLAlchemy database models
            ├── schemas/                    # Pydantic request/response schemas
            ├── routers/                    # API endpoints (/predict, /history, /model-info)
            └── services/                   # Feature extraction, scraping, SHAP explainability
```

---
*PhishGuard — Intelligent Phishing Website Detection System*
