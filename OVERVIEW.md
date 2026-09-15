# PhishGuard — System Architecture & Design Overview

> **Intelligent phishing website detection with machine learning, explainable AI (SHAP), and FastAPI.**
> Paste a URL → get a verdict, risk score, and the evidence behind it.

Start with [`README.md`](README.md) for setup, training, and API usage.
This document covers the *why* and *how*: problem framing, design language,
architecture, user experience, feature engineering, model evaluation, calibration,
trust layers, data contracts, and repository layout.

---

## Contents

- [Executive summary](#executive-summary)
- [Problem & objectives](#problem--objectives)
- [Design language](#design-language)
- [System architecture](#system-architecture)
- [Application pages](#application-pages)
- [Feature engineering (25 signals)](#feature-engineering-25-signals)
- [ML pipeline & benchmarks](#ml-pipeline--benchmarks)
- [Calibration](#calibration)
- [Trust layers](#trust-layers)
- [Tech stack](#tech-stack)
- [Data contracts](#data-contracts)
- [Run it locally](#run-it-locally)
- [Repository map](#repository-map)

---

## Executive summary

**PhishGuard** is an end-to-end cybersecurity intelligence system that detects
phishing websites in real time using structural URL analysis and HTML content
signals. Instead of slow static blacklists or paid third-party threat APIs,
it uses a custom-trained **supervised ML pipeline** with **SHAP explainability**
to deliver high-accuracy verdicts with human-readable evidence.

| Layer | What it is |
|---|---|
| **Backend** | FastAPI (async) — prediction, history, model-info, health |
| **Intelligence** | 25-feature extractor → calibrated RandomForest → SHAP top-5 |
| **Safety nets** | Vendored threat-feed pre-filter · advisory review band · frozen eval gate |
| **Frontend** | React 18 + Vite 7 + Tailwind forensic bench (dark evidence-room + daylight lab) |
| **Persistence** | SQLite custody log (scans + features + SHAP + model version) |

---

## Problem & objectives

### The challenge

Phishing drives the majority of reported security incidents. Modern campaigns use
short-lived, dynamically generated zero-day domains that outrun traditional
IP/domain blacklists. Commercial alternatives often need paid API subscriptions,
add latency, or act as black boxes — flagging sites without saying *why*.

### Objectives

| # | Objective | Status |
|---|---|---|
| 1 | **Real-time classification** — legitimate vs. phishing with confidence + 0–100 risk | Shipped (`POST /predict`) |
| 2 | **25-signal hybrid vector** — 18 URL-side + 7 page/redirect signals, no threat APIs at serve time | Shipped, URL-only fallback |
| 3 | **Best-model selection** — compare Logistic Regression, Random Forest, XGBoost, SVM on F1 / ROC-AUC | Shipped — RandomForest selected |
| 4 | **Explainability** — SHAP top-5 drivers on every verdict | Shipped |
| 5 | **Graceful degradation** — URL-only analysis when the target is offline | Shipped (`html_features_available` flag) |
| 6 | **Analyst workflow** — history, filters, analytics, PDF-ready report | Shipped (6 pages) |

> The original ≥95% accuracy target was aspirational. The shipped model reaches
> **93.57% accuracy / 91.40 F1 / 0.9829 ROC-AUC** on 1.23M URLs — documented
> honestly in [ML pipeline](#ml-pipeline--benchmarks) with calibration gains.

---

## Design language

PhishGuard avoids generic SaaS templates in favor of a **security-audit posture**
("Obsidian Vault"): dense, precise, evidence-first.

| Token | Value | Use |
|---|---|---|
| Canvas | `#08080f` | App background |
| Surface | `#0f0f1a` + `#1e1e33` hairline | Cards, panels |
| Safe | `#00e5c0` (mint) | Legitimate verdicts |
| Danger | `#ff5a5a` (coral) | Phishing verdicts |
| Caution | `#f0c040` (gold) | Review band, warnings |
| Type | `Inter` (UI) + `JetBrains Mono` (URLs, scores, data) | Readability + forensic feel |

Signature moments: 1px EKG scan-line during analysis, asymmetric verdict block,
monospace risk/confidence numerics, and a white print-optimized report theme.

---

## System architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                │
│                      React 18 + Vite + Tailwind                          │
│     Overview  │  Scan  │  History  │  Analytics  │  Model & API  │ Report │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP / REST (fetch)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND                                │
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐   │
│  │    predict.py    │    │    history.py    │    │   model_info.py   │   │
│  │   POST /predict  │    │ GET / DELETE     │    │ GET /model-info   │   │
│  │                  │    │ /history         │    │ GET /health       │   │
│  └────────┬─────────┘    └────────┬─────────┘    └─────────┬─────────┘   │
│           │                       │                        │             │
│           ▼                       ▼                        ▼             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                           SERVICE LAYER                            │  │
│  │  feature_engineering.py — 18 URL-side + 7 page-signal extractors   │  │
│  │  scraper.py             — async HTML fetch, 4s timeout, fail-open  │  │
│  │  prediction.py          — cached singleton model inference        │  │
│  │  explainability.py      — SHAP top-5 contributing signals         │  │
│  │  blocklist.py           — vendored threat-feed pre-filter         │  │
│  └────────────────┬──────────────────┬───────────────────────────────┘  │
│                   │                  │                                   │
│         ┌─────────┴────────┐         └──────────┐                        │
│         ▼                  ▼                    ▼                        │
│  ┌──────────────┐   ┌─────────────┐     ┌──────────────┐                 │
│  │   ML model   │   │  SQLite DB  │     │  Swagger UI  │                 │
│  │ RandomForest │   │ scan_history│     │    /docs     │                 │
│  │ (calibrated) │   │ model_meta  │     │  (themed)    │                 │
│  └──────────────┘   └─────────────┘     └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

Request flow: `POST /predict {"url"}` → threat-feed check → feature extraction →
calibrated inference (@ threshold 0.5) → SHAP explanation → review-band flag →
persist to SQLite → return verdict + evidence. Full contract in [`README.md`](README.md#how-a-scan-works).

---

## Application pages

Six workflows covering the threat-analysis lifecycle:

### 1. Overview (`/`)

Landing bench: system health badge (online/offline), active model chip, quick-scan
bar, latest-scan card (URL, verdict, confidence, age), and live DB/model status.

### 2. Scan (`/scan`) — primary workspace

- Monospace URL input with client-side validation and inline errors.
- EKG scan-line animation during analysis.
- Verdict block: `PHISHING DETECTED` (coral) or `URL IS SAFE` (mint), confidence
  (e.g. `97.3%`), and 0–100 risk meter (`0–33` low · `34–66` medium · `67–100` high).
- Degradation notice (`Analysis based on URL structure only`) when HTML is unreachable.
- **SHAP evidence list** — top-5 signals with raw value, impact bar, direction
  (`increases_risk` / `decreases_risk`), and plain-English explanation.
- **Full 25-feature accordion** — all 18 URL-side + 7 page/redirect values.

### 3. History (`/history`)

Searchable custody log: text search over URL/domain, `All` / `Legitimate` /
`Phishing` pills, verdict badges, risk/confidence columns, timestamps, per-row
`View` (detail modal) and `Delete` (confirm overlay), CSV export, and
`Page X of Y` pagination.

### 4. Analytics (`/analytics`)

Fleet view: total scans, phishing count/rate, average confidence, model accuracy;
model comparison matrix; confusion-matrix heatmap, multi-model ROC curves, and
feature-importance chart (custom SVG, no chart dependency).

### 5. Model & API (`/model-api`)

Active model metadata (algorithm, timestamp, dataset size, metrics), endpoint
registry (`POST /predict`, `GET /history`, `DELETE /history/{id}`,
`GET /model-info`, `GET /health`), and embedded themed Swagger UI for live testing.

### 6. Report (`/report`)

Print/PDF-optimized white theme: audit header + timestamp, target URL/domain,
executive verdict + risk level, top-5 forensic signals, complete 25-feature matrix,
and model signature footer.

---

## Feature engineering (25 signals)

### A. URL structure — 15 always-available signals

| # | Feature | Type | Logic | Threat signal |
|---|---|---|---|---|
| 1 | `url_length` | `int` | `len(url)` | Overlong URLs hide the real destination |
| 2 | `domain_length` | `int` | `len(domain)` | Typosquat / spoofed-brand domains |
| 3 | `num_dots` | `int` | count of `.` | Excessive subdomains (`login.paypal.com.evil.com`) |
| 4 | `num_hyphens` | `int` | count of `-` | Lookalike brand mimicry |
| 5 | `num_digits` | `int` | count of `[0-9]` | Algorithmically generated domains |
| 6 | `num_subdomains` | `int` | subdomain depth | Deep nesting to bury the true host |
| 7 | `has_https` | `bool` | `scheme == "https"` | Missing TLS on sensitive flows |
| 8 | `has_ip_address` | `bool` | dotted-IP regex | Raw-IP hosts bypass domain reputation |
| 9 | `has_at_symbol` | `bool` | `"@" in url` | User-info redirect trick |
| 10 | `has_double_slash_redirect` | `bool` | `"//"` after position 7 | Path redirect abuse |
| 11 | `is_shortened_url` | `bool` | shortener list | Destination obfuscation (bit.ly, t.co, …) |
| 12 | `num_suspicious_chars` | `int` | count of `@ % _ = &` | Encoding / smuggling tricks |
| 13 | `url_entropy` | `float` | Shannon entropy | High randomness in path/params |
| 14 | `has_suspicious_tld` | `bool` | high-risk TLD list | `.xyz`, `.top`, `.tk`, `.gq`, `.ml`, … |
| 15 | `path_length` | `int` | `len(path)` | Deep paths hiding payloads |

### B. Page & redirect — 7 signals (fail-open when unreachable)

| # | Feature | Type | Logic | Threat signal |
|---|---|---|---|---|
| 16 | `has_iframe` | `bool` | `<iframe>` present | Phish form framed inside a clean page |
| 17 | `redirect_count` | `int` | HTTP redirect hops | Multi-hop laundering chains |
| 18 | `num_external_links` | `int` | foreign `<a href>` | Cloned assets pointing off-site |
| 19 | `form_action_suspicious` | `bool` | blank / IP / foreign action | Credentials exfiltrated third-party |
| 20 | `has_javascript_events` | `bool` | `onmouseover` / `onload` tricks | Right-click disable, status-bar spoof |
| 21 | `has_popup_window` | `bool` | `window.open()` | Fake login popups |
| 22 | `has_hidden_elements` | `bool` | `display:none` / `opacity:0` | Hidden credential/SEO traps |

### C. Reputation & keyword — 3 URL-side signals

| # | Feature | Type | Logic | Threat signal |
|---|---|---|---|---|
| 23 | `domain_in_top_list` | `bool` | registrable domain in Cisco Umbrella top-1M (`ml/data/reputation_top1m.csv`) | Exonerates github / wikipedia / google class |
| 24 | `has_auth_keyword` | `bool` | `login\|signin\|verify\|account\|password\|2fa\|otp` in subdomain/path/query | Auth-flow lure |
| 25 | `keyword_domain_mismatch` | `bool` | brand keyword in path but **not** in registrable domain | Classic phish shape (`evil.com/paypal-login`) |

> `html_features_available` travels alongside the vector as metadata (not a model
> input) so the UI can disclose URL-only vs. full analysis. Contract enforced by
> `test_extract_all_contains_contract`.

---

## ML pipeline & benchmarks

Four candidates trained on **1,225,534 URLs** (stratified 80/20, `class_weight="balanced"`,
no SMOTE; `RandomForest(max_depth=25)` size-bounded). Source of truth:
`phishing_detector/backend/ml/comparison_report.json` (trained 2026-09-15).

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Role |
|---|---|---|---|---|---|---|
| **RandomForest** | **93.57%** | **92.72%** | **90.12%** | **91.40** | **0.9829** | **Selected** |
| XGBoost | 91.04% | 92.95% | 82.63% | 87.49 | 0.9660 | Runner-up |
| Logistic Regression | 80.42% | 77.20% | 68.61% | 72.65 | 0.8806 | Interpretable baseline |
| SVM (calibrated linear) | 80.28% | 76.41% | 69.41% | 72.74 | 0.8793 | Benchmark (RBF infeasible at this scale) |

**Selection:** highest F1, ROC-AUC breaks ties. RandomForest also pairs natively
with SHAP `TreeExplainer` for fast local explanations. Retrain via `ml/train.py`;
benchmarks via `ml/evaluate.py`; artifacts: `models/best_model.pkl` +
`ml/comparison_report.json`.

---

## Calibration

Raw forest scores rank well but are overconfident, so the shipped artifact is
**isotonic-calibrated** (`ml/calibrate.py`, no retrain) — prefit on 122,553 held-out
rows recovered deterministically from the training run's own split (reproduced to
~2e-04; wrong-split controls deviate ~1e-02, so the set is provably held-out).

| Metric (held-out) | Raw | Calibrated |
|---|---|---|
| Accuracy | 93.60% | 93.68% |
| Precision / Recall / F1 | 92.77 / 90.14 / 91.44 | 94.49 / 88.49 / 91.39 |
| ROC-AUC | 0.9831 | 0.9830 |
| Brier → lower is better | 0.0490 | **0.0464** |
| Log-loss → lower is better | 0.1686 | **0.1560** |

Threshold stays **0.5** (the frozen gate assumes it). Measured alternatives and the
abstain-band analysis live in `ml/calibration_report.json`; preview operating
points with `eval_gate.py --threshold <t>`.

---

## Trust layers

| Layer | Where | Behavior |
|---|---|---|
| **Threat-feed pre-filter** | `app/services/blocklist.py` + `ml/data/feed_blocklist.csv` | Normalized exact-URL match outranks the model (phishing, risk 100) with `blocklist_hit` / `blocklist_source`. No domain expansion — shared hosts stay safe. Refresh: `python ml/refresh_blocklist.py`. Toggle: `BLOCKLIST_ENABLED=false`. |
| **Review band** | `needs_review`, defaults `[0.40, 0.60]` | Advisory-only flag for analysts (~3.3% of traffic at ~45% error). Never changes the verdict. |
| **Operating point** | `DECISION_THRESHOLD=0.5`, echoed by every response + `/model-info` | Change deliberately; gate assumes 0.5. |
| **Acceptance gate** | `eval_gate.py` on frozen 40 URLs + `ml/data/eval_gate.json` | Exit 0 ships: ≥85% frozen accuracy, `github.com/login` p < 0.30, zero top-site misses. |
| **Retrain readiness** (unserved) | `ml/v3_signals.py`, `ml/rdap.py`, `ml/collect_html.py` | `on_free_host` (13.1% phish vs 1.4% legit), RDAP `domain_age_days` (cached, fail-open), resumable HTML corpus — training-side only, 25-feature serving contract untouched. |

---

## Tech stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11 · Node.js 20.19+ | Backend runtime · frontend toolchain |
| Backend | FastAPI (ASGI/Uvicorn) | Async REST API |
| ML | scikit-learn, XGBoost, SHAP | Training, inference, explainability |
| Data | Pandas, NumPy, tldextract | Manipulation + domain parsing |
| DB / ORM | SQLite + SQLAlchemy | Scan history + model metadata |
| Scraping | BeautifulSoup4, Requests | DOM feature extraction (fail-open) |
| Frontend | React 18, Vite 7 | Interactive bench UI |
| Styling | Tailwind CSS, Lucide icons | Design system |
| Charts | Custom SVG | Dependency-free analytics visuals |
| Validation | Pydantic v2 (+ pydantic-settings) | Strict API schemas + config |

All backend deps are `==`-pinned: pickled artifacts can break or silently drift
across sklearn/XGBoost/SHAP versions — retrain before upgrading.

---

## Data contracts

### `scan_history`

`id` (PK) · `url` (2048, indexed) · `domain` (255, indexed) · `prediction`
(`phishing`/`legitimate`) · `confidence` (0–1) · `risk_score` (0–100) ·
`risk_level` (`low`/`medium`/`high`) · `features_json` (25 signals) ·
`top_features_json` (SHAP top-5) · `model_version` (FK) · `scanned_at` (indexed) ·
plus `needs_review`, `blocklist_hit`, `blocklist_source`, `decision_threshold`.

### `model_metadata`

`id` (PK) · `model_name` · `version` (unique) · `accuracy`, `precision`, `recall`,
`f1_score`, `roc_auc` · `dataset_size` · `file_path` · `is_active` (indexed).

### API

`POST /predict` · `GET /history` · `DELETE /history/{id}` ·
`GET /model-info` · `GET /health` · `GET /docs` (themed Swagger).
Full request/response shapes with examples: [`README.md`](README.md#how-a-scan-works).

---

## Run it locally

Full commands live in [`README.md`](README.md#quickstart). Summary:

```powershell
# Backend
cd phishing_detector\backend
uv venv --python 3.11 .venv; .\.venv\Scripts\Activate.ps1
uv pip install --python .venv\Scripts\python.exe -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000   # → localhost:8000/docs

# Frontend
cd frontend; npm install; npm run dev       # → localhost:5173
```

Tests: `python -m pytest tests/ -q` (backend) · `npm run build` (frontend check).

---

## Repository map

```text
PhishGuard/
├── README.md                             # Start here — install, run, train, test
├── OVERVIEW.md                           # This file — architecture & design
├── frontend/                             # React 18 + Vite 7 + Tailwind forensic bench UI
│
│   NOTE: training data (*.csv, except the three companions in ml/data),
│   the trained artifact (*.pkl), the SQLite database (*.db),
│   backend/.env, and college-only docs/ + tools/ are local-only and
│   gitignored — README.md shows how to regenerate each of them.
│
└── phishing_detector/
    └── backend/                          # FastAPI backend service
        ├── requirements.txt              # ==-pinned runtime deps
        ├── phishguard.db                 # SQLite file (local-only, gitignored)
        ├── models/
        │   └── best_model.pkl            # Trained artifact (local-only, gitignored)
        ├── ml/                           # Pipeline scripts
        │   ├── train.py                  # Training & evaluation
        │   ├── calibrate.py              # Isotonic calibration (no retrain)
        │   ├── evaluate.py               # Benchmarks
        │   ├── calibration_report.json   # Calibration metrics + thresholds
        │   ├── data/
        │   │   ├── eval_gate.json        # Frozen 40-URL acceptance set
        │   │   ├── hard_negatives.csv    # Curated top-site logins (versioned)
        │   │   └── feed_blocklist.csv    # Threat-feed snapshot (versioned)
        │   └── comparison_report.json    # Training metrics (source of truth)
        ├── eval_gate.py                  # Frozen acceptance gate (exit 0 = ship)
        └── app/
            ├── main.py                   # App factory, CORS, themed /docs
            ├── core/                     # Config + logging
            ├── models/                   # SQLAlchemy models
            ├── schemas/                  # Pydantic schemas
            ├── routers/                  # /predict, /history, /model-info
            └── services/                 # Features, scraper, inference, SHAP, feed
```

---

*PhishGuard — Intelligent Phishing Website Detection System.*
