# PhishGuard — Intelligent Phishing URL Detection

Machine-learning phishing detection with SHAP explainability: paste a URL, get a
verdict (phishing / legitimate) with a 0–100 risk score, confidence, and the top
signals that decided it — all persisted to a searchable custody log.

- **Backend:** FastAPI + scikit-learn RandomForest (1.2M URLs, 93.6% accuracy),
  SHAP explanations, SQLite custody log
- **Frontend:** React + Vite + Tailwind forensic UV-bench UI (dark evidence-room
  + daylight lab themes), 6 pages: Overview, Scan, History, Analytics,
  Model & API, printable Report

## Architecture

```
Browser :5173 (React/Vite, proxies /api → :8000)
        │
        ▼
FastAPI :8000 ── POST /predict ──► feature extraction (25 URL signals)
        │                          ──► RandomForest (best_model.pkl, ~0.8 GB)
        │                          ──► SHAP top-5 signals
        └── /history /model-info /health /docs ──► SQLite (phishguard.db)
```

## Prerequisites

| Tool | Required version | Notes |
|---|---|---|
| Python | **3.11** (the bundled `.venv` uses 3.11.15) | ⚠️ Do **not** use Python 3.14 — `scikit-learn` has no prebuilt wheels for it and `pip install` fails trying to compile from source |
| Node.js | 18+ (tested on 24.x) | Frontend only |
| RAM | 8 GB to serve · 16 GB to train | The trained artifact is ~0.8 GB; serving loads it fully into memory |
| OS | Windows (PowerShell) primarily; macOS/Linux commands differ only in venv activation | |

## Quickstart

### 1. Backend (terminal 1)

```powershell
cd phishing_detector\backend

# Use the bundled environment (all dependencies pre-installed)
.\.venv\Scripts\Activate

# Fresh setup only — recreate env + install + configure:
#   python -m venv .venv            # must be Python 3.11, see warning above
#   .\.venv\Scripts\Activate
#   pip install -r requirements.txt
#   Copy-Item .env.example .env     # then edit paths if needed

# Start the API (first start takes a while: it loads the ~0.8 GB model)
uvicorn app.main:app --port 8000
```

macOS/Linux equivalents: `source .venv/bin/activate`, then the same `uvicorn` command.

### 2. Frontend (terminal 2)

```powershell
cd frontend
npm install   # first time only
npm run dev
```

### 3. Verify everything

| Check | How | Healthy result |
|---|---|---|
| Backend alive | `GET http://localhost:8000/health` | `{"status":"ok","model_loaded":true,…}` |
| Real model loaded | `GET http://localhost:8000/model-info` | `"model_name":"RandomForest"`, **not** `HeuristicFallback` |
| Prediction works | `POST http://localhost:8000/predict` body `{"url":"https://github.com/login"}` | verdict + `risk_score` + 5 `top_features` |
| UI | open `http://localhost:5173` | Overview bench loads; scan a URL end-to-end |
| API console | `http://localhost:8000/docs` | Swagger UI in bench-dark theme |

> If `/model-info` reports `HeuristicFallback`, no trained artifact was found —
> see [Training](#training-a-model) then restart the backend. Every scan still
> works, but verdicts come from uncalibrated rules.

## Configuration (`phishing_detector/backend/.env`)

Copied from `.env.example` (gitignored — each machine needs its own):

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./phishguard.db` | SQLite file, auto-created on startup |
| `MODEL_PATH` | `models/best_model.pkl` | Trained artifact, resolved relative to `backend/` |
| `MODEL_METADATA_PATH` | `ml/comparison_report.json` | Training report backing `/model-info` |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origin |
| `ENABLE_HTML_SCRAPING` | `false` | Fetch target pages for 7 DOM features (off: URL-only mode) |
| `ALLOW_HEURISTIC_FALLBACK` | `true` | Serve rule-based verdicts when no artifact exists |

## Training a model

Needs the labeled dataset (`ml/data/phish_urls.csv`, `url,label` columns —
**not** committed, `*.csv` is gitignored) plus companions documented in
`phishing_detector/backend/README.md` (`reputation_top1m.csv`,
`hard_negatives.csv`).

```powershell
cd phishing_detector\backend
.\.venv\Scripts\Activate
python -m ml.train            # hours on 1.2M rows; progress + log to console
```

What it does: extracts 25 features per URL → trains LogisticRegression,
RandomForest, XGBoost, SVM → isotonic-calibrates each on a held-out split →
writes `models/best_model.pkl` + `ml/comparison_report.json` (selects on F1,
then ROC-AUC). **Restart the backend afterwards** — the model loads once at
startup. Then re-run the acceptance gate:

```powershell
python eval_gate.py                                # default: production MODEL_PATH
python eval_gate.py --model models\best_model.pkl  # any candidate artifact
```

Exit 0 = all gates pass (≥85% on the frozen 40-URL set, github/login < 0.30,
zero top-site misses). Full criteria: `IMPROVEMENT-PLAN.md`.

## Testing

```powershell
# Backend (29 tests: API contract, features, degradation paths)
cd phishing_detector\backend
.\.venv\Scripts\Activate
python -m pytest tests/ -q

# Frontend (production build = type/template check)
cd frontend
npm run build
```

## Project structure

```
PhishGuard/
├── README.md                        # this file — start here
├── OVERVIEW.md                      # system design + architecture deep-dive
├── ACCURACY-REPORT.md               # 24-URL live accuracy report + raw results JSON
├── IMPROVEMENT-PLAN.md              # accuracy roadmap (Tier 1 in progress)
├── FIRETEST-REPORT.md               # live fire-test vs real phishing URLs
├── frontend/                        # React 18 + Vite + Tailwind + framer-motion
│   └── src/{pages,components,services,utils}  # 6 pages, api client, verdict system
└── phishing_detector/
    └── backend/
        ├── app/{routers,services,models,schemas,core,static}
        ├── models/                  # best_model.pkl lives here after training
        ├── ml/{train,evaluate,data} # pipeline + companion data (gitignored CSVs)
        ├── tests/                   # pytest suite
        ├── eval_gate.py             # frozen acceptance gate
        ├── requirements.txt         # production deps (pinned — see backend README)
        └── requirements-dev.txt     # pytest, httpx
```

## Troubleshooting

| Symptom | Cause → fix |
|---|---|
| `pip install` fails building `scikit-learn` (meson/no compiler) | You're on Python 3.14+. Switch to the bundled 3.11 `.venv` |
| `vite` won't bind `:5173` / page shows stale UI | Kill leftover servers: stop any `node.exe …vite` process, then `npm run dev` fresh; hard-refresh the browser (Ctrl+Shift+R) |
| `/model-info` says `HeuristicFallback` | No artifact at `MODEL_PATH` → train (above) or fix `.env` paths, then restart backend |
| First backend start hangs for a while | Normal: loading the ~0.8 GB model. Watch for `application_started`; don't start a second instance |
| Every `/predict` returns 500 | Check the backend console traceback; known-fixed causes: unparseable `trained_at` in report, feature-count mismatch after adding extractors (tests catch this: `test_extract_all_contains_contract`) |
| `/history` empty after scans | Scans write to `phishguard.db` next to the backend — deleting that file wipes history (it recreates on restart) |
| Frontend `LIGHT` toggle seems stuck | Theme persists in `localStorage` (`phishguard-theme`); a pre-paint script applies it before React loads — clear site data if testing fresh |
| Tests fail on feature counts | Expected when adding extractors — update the `== 26` assertions in `test_api.py` / `test_degradation.py` and the parametrize list in `test_features.py` |

## API quick reference

| Method | Route | Purpose |
|---|---|---|
| POST | `/predict` | `{"url"}` → verdict, confidence, risk 0–100, SHAP top-5, full 25-feature vector; persisted |
| GET | `/history?page=&per_page=&prediction=` | Newest-first custody log + pagination |
| DELETE | `/history/{scan_id}` | Strike one record (204) |
| GET | `/model-info` | Serving model metrics + training timestamp |
| GET | `/health` | `status`, `model_loaded`, `database_connected` |
| GET | `/docs` | Themed Swagger console |
