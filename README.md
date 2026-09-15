# PhishGuard — Intelligent Phishing URL Detection

Paste a URL, get a verdict: **phishing** or **legitimate**, with a 0–100 risk
score, confidence, and the top signals that decided it — every scan persisted
to a searchable custody log.

|                     |                                                                                           |
| ------------------- | ----------------------------------------------------------------------------------------- |
| **Serving model**   | Calibrated RandomForest · 93.7% accuracy · F1 91.4 · ROC-AUC 0.983                        |
| **Acceptance gate** | 3/3 passing (90.0% on frozen 40-URL set, `github.com/login` p=0.06, zero top-site misses) |
| **Live fire-test**  | Round 3 through the API: **12/15** (6/6 legitimate, 6/9 phishing)                         |
| **Backend**         | FastAPI · scikit-learn · SHAP explainability · SQLite custody log                         |
| **Frontend**        | React 18 + Vite 7 + Tailwind forensic bench UI (dark evidence-room + daylight lab)        |
| **Tests**           | 49 backend tests green · `npm audit`: 0 vulnerabilities                                   |

## How a scan works

```
Browser :5173 ── POST /predict {"url"} ──► FastAPI :8000
                                                    │
                       ┌────────────────────────────┼────────────────────────────┐
                       │  1. Threat-feed pre-filter │  exact URL match → phishing│
                       │     (vendored URLhaus      │  risk 100 + provenance     │
                       │      snapshot, offline)    │                            │
                       │  2. Feature extraction     │  25 URL signals            │
                       │  3. Calibrated RandomForest│  verdict @ threshold 0.5   │
                       │  4. SHAP top-5 signals     │  what decided it           │
                       │  5. Review band [0.40,0.60]│  advisory flag, never a    │
                       │                            │  verdict change            │
                       └────────────────────────────┼────────────────────────────┘
                                                    ▼
                                    SQLite custody log (scan + features +
                                    SHAP + review/feed flags) ──► /history
```

```jsonc
// POST /predict {"url": "https://github.com/login"} →
{
  "scan_id": 114,
  "url": "https://github.com/login",
  "domain": "github.com",
  "prediction": "legitimate", // "phishing" | "legitimate" — never anything else
  "confidence": 0.937,
  "risk_score": 6, // 0–100
  "risk_level": "low", // "low" | "medium" | "high"
  "needs_review": false, // calibrated p inside [0.40, 0.60]?
  "blocklist_hit": false, // exact match in the threat-feed snapshot?
  "blocklist_source": null, // e.g. "urlhaus-online" when hit
  "decision_threshold": 0.5,
  "model_version": "randomforest_v2_2026-09-14_164407_calibrated",
  "scanned_at": "2026-09-15T05:37:07Z",
  "top_features": [
    {
      "name": "domain_in_top_list",
      "value": true,
      "impact_score": 0.31,
      "direction": "decreases_risk",
    },
    // …4 more
  ],
  "features": { "url_length": 24, "domain_length": 6 /* …25 total */ },
  "html_features_available": false,
}
```

## Prerequisites

| Tool    | Version                                     | Notes                                                                                                    |
| ------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Python  | **3.11** (the bundled `.venv` uses 3.11.15) | ⚠️ Not 3.14 — `scikit-learn` has no prebuilt wheels there and `pip install` tries to compile from source |
| Node.js | 20.19+ (tested on 24.x; required by Vite 7) | Frontend only                                                                                            |
| RAM     | 8 GB to serve · 16 GB to train              | The artifact is ~0.8 GB and loads fully into memory                                                      |
| OS      | Windows (PowerShell) primarily              | macOS/Linux differ only in venv activation                                                               |

## Quickstart

**1 · Backend** (terminal 1)

```powershell
cd phishing_detector\backend

# Use the bundled environment (all dependencies pre-installed)
.\.venv\Scripts\Activate

# Fresh setup only — recreate env + install + configure:
#   python -m venv .venv            # must be Python 3.11, see warning above
#   .\.venv\Scripts\Activate
#  uv pip install --python .venv\Scripts\python.exe -r requirements.txt -r requirements-dev.txt
#   Copy-Item .env.example .env     # then edit paths if needed

# Start the API (first start takes a while: it loads the ~0.8 GB model)
uvicorn app.main:app --port 8000
```

macOS/Linux equivalent: `source .venv/bin/activate`, then the same `uvicorn` command.

**2 · Frontend** (terminal 2)

```powershell
cd frontend
npm install   # first time only
npm run dev
```

**3 · Verify** — open `http://localhost:5173`, scan a URL end to end.
Prefer the terminal?

| Check             | How                                                                  | Healthy result                                              |
| ----------------- | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| Backend alive     | `GET localhost:8000/health`                                          | `{"status":"ok","model_loaded":true,…}`                     |
| Real model loaded | `GET localhost:8000/model-info`                                      | `"model_name":"RandomForest"` — **not** `HeuristicFallback` |
| Prediction works  | `POST localhost:8000/predict` → `{"url":"https://github.com/login"}` | `legitimate`, `risk_score` 6, 5 `top_features`              |
| API console       | `localhost:8000/docs`                                                | Swagger UI in bench-dark theme                              |

> `/model-info` says `HeuristicFallback`? No trained artifact was found —
> see [Training](#training--calibration--gate), then restart the backend.
> Scans still work meanwhile, but verdicts come from uncalibrated rules.

## Configuration

`phishing_detector/backend/.env`, copied from `.env.example`
(gitignored — each machine keeps its own):

| Variable                               | Default                      | Meaning                                                              |
| -------------------------------------- | ---------------------------- | -------------------------------------------------------------------- |
| `DATABASE_URL`                         | `sqlite:///./phishguard.db`  | SQLite file, auto-created (and auto-migrated) on startup             |
| `MODEL_PATH`                           | `models/best_model.pkl`      | Trained artifact, resolved relative to `backend/`                    |
| `MODEL_METADATA_PATH`                  | `ml/comparison_report.json`  | Training report backing `/model-info`                                |
| `CORS_ORIGINS`                         | `http://localhost:5173`      | Allowed frontend origin                                              |
| `ENABLE_HTML_SCRAPING`                 | `false`                      | Fetch target pages for 7 DOM features (off = URL-only mode)          |
| `ALLOW_HEURISTIC_FALLBACK`             | `true`                       | Rule-based verdicts when no artifact exists                          |
| `BLOCKLIST_PATH`                       | `ml/data/feed_blocklist.csv` | Vendored threat snapshot (refresh: `python ml/refresh_blocklist.py`) |
| `BLOCKLIST_ENABLED`                    | `true`                       | Exact-match pre-filter before the ML verdict                         |
| `DECISION_THRESHOLD`                   | `0.5`                        | Verdict operating point (the frozen gate assumes 0.5)                |
| `REVIEW_BAND_LOW` / `REVIEW_BAND_HIGH` | `0.4` / `0.6`                | Advisory low-margin flag (never changes verdicts)                    |

## Training · calibration · gate

The dataset (`ml/data/phish_urls.csv`, `url,label`) is **not** committed
(`*.csv` is gitignored); companions are documented in
`phishing_detector/backend/README.md`.

```powershell
cd phishing_detector\backend
.\.venv\Scripts\Activate

python -m ml.train            # hours on 1.2M rows
# → extracts 25 features per URL → trains LogisticRegression,
#   RandomForest, XGBoost, SVM → writes models/best_model.pkl +
#   ml/comparison_report.json (selects on F1, then ROC-AUC).
#   Restart the backend afterwards — the model loads once at startup.

python ml/calibrate.py        # minutes: isotonic calibration on held-out
# → rows with quality bars (Brier/log-loss must improve, F1 must hold).
#   Writes models/candidate_calibrated.pkl + ml/calibration_report.json.

python eval_gate.py                                # production MODEL_PATH
python eval_gate.py --model models\candidat.pkl    # any candidate artifact
```

Exit 0 ships: **≥85% on the frozen 40-URL set, `github.com/login` < 0.30,
zero top-site misses.** Full criteria: `IMPROVEMENT-PLAN.md`.
Swap a passing candidate into `models/best_model.pkl` (keep the old file
as backup), restart, confirm `/model-info`.

Weekly hygiene: `python ml/refresh_blocklist.py` re-vendors the threat
snapshot. Retrain runbooks (v3 signals, HTML corpus) live in the backend
README.

## Testing

```powershell
# Backend — 49 tests: API contract, features, degradation, feed/review/
# threshold, v3 signals, HTML collector, legacy-DB migration
cd phishing_detector\backend
.\.venv\Scripts\Activate
python -m pytest tests/ -q

# Frontend — production build doubles as the template check
cd frontend
npm run build
```

## Project structure

```
PhishGuard/
├── README.md                        # this file — start here
├── OVERVIEW.md                      # system design + architecture deep-dive
├── IMPROVEMENT-PLAN.md              # Tier-1 roadmap: shipped, with Tier-2 backlog
├── FIRETEST-REPORT.md               # live fire-tests vs real phishing URLs (round 3: 12/15)
├── ACCURACY-REPORT.md               # 24-URL accuracy study + raw results JSON
├── CHANGELOG.md                     # running log of every fix in this repo
├── frontend/                        # React 18 + Vite 7 + Tailwind
│   └── src/{pages,components,services,utils}  # 6 pages, api client, verdict system
├── phishing_detector/backend/
│   ├── app/{routers,services,models,schemas,core,static}  # API + inference
│   ├── models/                      # best_model.pkl (local-only, gitignored)
│   ├── ml/{train,calibrate,evaluate} # pipeline + calibration + benchmarks
│   ├── ml/{refresh_blocklist,collect_html,rdap,v3_signals}  # feeds + retrain readiness
│   ├── ml/{comparison,calibration}_report.json  # training + calibration evidence
│   ├── ml/data/{eval_gate.json,hard_negatives.csv,feed_blocklist.csv}
│   ├── tests/                       # 49-test pytest suite
│   └── eval_gate.py                 # frozen acceptance gate (exit 0 = ship)
├── files/                           # architecture + contract specs
├── docs/ · archive/ · tools/        # SRS sources, history, SRS builder
└── project doc/                     # generated submission packet
```

## Troubleshooting

| Symptom                                     | Cause → fix                                                                                                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `pip install` fails building `scikit-learn` | You're on Python 3.14+. Use the bundled 3.11 `.venv`                                                                                 |
| `:5173` won't bind / stale UI               | Kill leftover `node.exe …vite` processes, `npm run dev` fresh, hard-refresh (Ctrl+Shift+R)                                           |
| `/model-info` says `HeuristicFallback`      | No artifact at `MODEL_PATH` → train (above) or fix `.env`, restart backend                                                           |
| First start hangs                           | Normal: loading ~0.8 GB. Wait for `application_started`; don't start a second instance                                               |
| Every `/predict` is 500                     | Read the backend traceback; tests catch the classic causes (`test_extract_all_contains_contract` guards feature counts)              |
| `/history` empty after scans                | History lives in `phishguard.db` next to the backend — deleting it wipes history (recreates on restart)                              |
| `LIGHT` toggle stuck                        | Theme persists in `localStorage` (`phishguard-theme`) — clear site data for a fresh look                                             |
| Tests fail on feature counts                | Expected when adding extractors — bump the count asserts in `test_api.py` / `test_degradation.py` and the list in `test_features.py` |

## API quick reference

| Method | Route                                  | Purpose                                                                                                  |
| ------ | -------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| POST   | `/predict`                             | `{"url"}` → verdict, confidence, risk 0–100, SHAP top-5, 25-feature vector, review/feed flags; persisted |
| GET    | `/history?page=&per_page=&prediction=` | Newest-first custody log + pagination (now with review/feed flags)                                       |
| DELETE | `/history/{scan_id}`                   | Strike one record (204)                                                                                  |
| GET    | `/model-info`                          | Model metrics, training timestamp, active threshold                                                      |
| GET    | `/health`                              | `status`, `model_loaded`, `database_connected`                                                           |
| GET    | `/docs`                                | Themed Swagger console                                                                                   |

## Further reading

- `OVERVIEW.md` — full architecture, feature matrix, calibration analysis
- `phishing_detector/backend/README.md` — training, calibration, blocklist ops, retrain runbooks
- `IMPROVEMENT-PLAN.md` — what shipped, residual misses, measured Tier-2 backlog
- `FIRETEST-REPORT.md` — all three live fire-test rounds
- `files/` — frozen specs: architecture, schema, API contract, features, model selection
