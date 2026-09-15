# PhishGuard — Intelligent Phishing URL Detection

Paste a URL, get a verdict: **phishing** or **legitimate**, with a 0–100 risk
score, confidence, and the top signals that decided it — every scan persisted
to a searchable custody log.

| | |
|---|---|
| **Serving model** | Calibrated RandomForest · 93.7% accuracy · F1 91.4 · ROC-AUC 0.983 |
| **Acceptance gate** | 3/3 passing (90.0% on frozen 40-URL set, `github.com/login` p=0.06, zero top-site misses) |
| **Live fire-test** | Round 3 through the API: **12/15** (6/6 legitimate, 6/9 phishing) |
| **Backend** | FastAPI · scikit-learn · SHAP explainability · SQLite custody log |
| **Frontend** | React 18 + Vite 7 + Tailwind forensic bench UI (dark evidence-room + daylight lab) |
| **Tests** | 49 backend tests green · `npm audit`: 0 vulnerabilities |

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
  "prediction": "legitimate",   // "phishing" | "legitimate" — never anything else
  "confidence": 0.937,
  "risk_score": 6,              // 0–100
  "risk_level": "low",          // "low" | "medium" | "high"
  "needs_review": false,        // calibrated p inside [0.40, 0.60]?
  "blocklist_hit": false,       // exact match in the threat-feed snapshot?
  "blocklist_source": null,     // e.g. "urlhaus-online" when hit
  "decision_threshold": 0.5,
  "model_version": "randomforest_v2_2026-09-15_064718_calibrated",
  "scanned_at": "2026-09-15T05:37:07Z",
  "top_features": [
    {"name": "domain_in_top_list", "value": true,
     "impact_score": 0.31, "direction": "decreases_risk"}
    // …4 more
  ],
  "features": {"url_length": 24, "domain_length": 6 /* …25 total */}
}
```

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | **3.11** | Pinned by `phishing_detector/backend/.python-version`. ⚠️ Not 3.14 — `scikit-learn` has no prebuilt wheels there and `pip install` tries to compile from source |
| [`uv`](https://docs.astral.sh/uv/) | any recent | Reproducible installs (the venv has no `pip`; it is uv-managed) |
| Node.js | 20.19+ (tested on 24.x; required by Vite 7) | Frontend only |
| RAM | 8 GB to serve · 16 GB to train | The artifact is ~0.8 GB and loads fully into memory |
| OS | Windows (PowerShell) primarily | macOS/Linux differ only in venv activation |

## 2. Backend setup

```powershell
cd phishing_detector\backend
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env     # real values stay local-only, gitignored
uvicorn app.main:app --reload --port 8000
```

> Never run bare `pip install` inside `.venv`: uv-managed venvs ship
> **without** `pip`, so Windows silently falls through `PATH` to another
> Python (e.g. 3.14) — which then fails building `scikit-learn` from
> source, since pinned wheels exist only for 3.11. Always use the
> `uv pip install --python …` form above.

If Python 3.11 is already installed, the equivalent standard-library setup is:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux equivalent: `source .venv/bin/activate`, then the same `uvicorn` command.

Why versions are pinned — do not casually bump them (`requirements.txt` is fully `==`-pinned, and that is load-bearing):

- `scikit-learn==1.5.1` / `xgboost==2.1.0`: the trained artifact (`models/best_model.pkl`) is a pickle. Unpickling a model saved under one sklearn/XGBoost version with a different version can fail outright or, worse, silently change predictions. Retrain before upgrading.
- `shap==0.46.0`: the explainer calls version-fragile APIs (`KernelExplainer` + `l1_reg="num_features(10)"`); other SHAP releases change that surface.
- Everything else (`numpy`, `pandas`, `fastapi`, `pydantic`, …) is pinned so a fresh `git clone` resolves the exact tested matrix. `requirements-dev.txt` (`pytest`, `httpx`) is the only split — test tooling, never imported by the app.

The backend starts with an offline deterministic fallback classifier so the API can be demonstrated before a dataset is supplied. Swagger UI: `http://localhost:8000/docs`.

## 3. Frontend setup

```powershell
cd frontend
npm install   # first time only
npm run dev   # → http://localhost:5173 (proxies /api → :8000)
```

## 4. Verify everything

| Check | How | Healthy result |
|---|---|---|
| Backend alive | `GET localhost:8000/health` | `{"status":"ok","model_loaded":true,…}` |
| Real model loaded | `GET localhost:8000/model-info` | `"model_name":"RandomForest"` — **not** `HeuristicFallback` |
| Prediction works | `POST localhost:8000/predict` → `{"url":"https://github.com/login"}` | `legitimate`, `risk_score` 6, 5 `top_features` |
| UI | open `http://localhost:5173` | Overview bench loads; scan a URL end to end |

> `/model-info` says `HeuristicFallback`? No trained artifact was found —
> train one ([§5](#5-train-a-model)) then restart the backend. Scans still
> work meanwhile, but verdicts come from uncalibrated rules.

## 5. Train a model

Place the dataset in `phishing_detector/backend/ml/data/` (create the folder
if needed). The trainer uses the **largest** `.csv` it finds there
(excluding `hard_negatives.csv`, which is always appended as extra
legitimate rows) — so keep only the dataset you want to train on.

```powershell
New-Item -ItemType Directory -Force ml\data
```

| File in `ml/data/` | Purpose | Committed? |
|---|---|---|
| `phish_urls.csv` | Labeled dataset, `url,label` columns | No (`*.csv` gitignored — supply your own) |
| `reputation_top1m.csv` | Cisco Umbrella top-1M (`rank,domain` rows) powering `domain_in_top_list`. Missing file = feature always false (warns, never crashes) | No |
| `hard_negatives.csv` | `url,label` rows (all `0`) of top-site login pages, auto-appended every retrain | **Yes** (curated, tiny) |
| `eval_gate.json` | Frozen 40-URL acceptance set | **Yes** |
| `feed_blocklist.csv` | Vendored threat-feed snapshot (see §7) | **Yes** |

The CSV must contain a URL column (`url` or `domain`) and a label column
(`label`, `class`, `type`, `prediction`, or `status`) — names are
case-insensitive; feature columns are extracted automatically, never supplied:

| Label → | Phishing (1) | Legitimate (0) |
|---|---|---|
| Accepted values | `1`, `phishing`, `malicious`, `bad` | anything else (`0`, `legitimate`, `benign`, …) |

```csv
url,label
https://example.com/login,phishing
https://google.com,legitimate
https://bank-secure-update.tk/signin,phishing
https://github.com,legitimate
```

Include both classes; duplicates are removed automatically.

```powershell
cd phishing_detector\backend
.\.venv\Scripts\Activate.ps1
python -m ml.train            # hours on 1.2M rows; progress on console
```

What it does: extracts 25 features per URL (+ the `html_features_available`
flag, which is metadata, not a model input) → stratified 80/20 split →
skips SMOTE by default (`USE_SMOTE = False`; `class_weight="balanced"`
already handles imbalance) → trains Logistic Regression, Random Forest
(`max_depth=25`, artifact-size bounded), XGBoost, and a calibrated linear
SVM (RBF would never finish at this scale) → evaluates accuracy, precision,
recall, F1, ROC-AUC → selects on F1, ROC-AUC breaks ties → writes
`models/best_model.pkl` + `ml/comparison_report.json`.
**Restart the backend afterwards** — the model loads once at startup.

## 6. Calibrate, gate, ship

Raw forest scores rank well but are overconfident — calibrate before shipping:

```powershell
.\.venv\Scripts\Activate.ps1
python ml/calibrate.py                          # minutes; isotonic prefit on held-out rows
python eval_gate.py --model models\candidat.pkl # score any artifact without serving it
```

`ml/calibrate.py` recovers the training run's own 20% test split
deterministically and **aborts unless the raw model reproduces the report
accuracy on it** — so the calibration set is provably held-out. It writes
the candidate + `ml/calibration_report.json` only if all bars hold (Brier +
log-loss improve, F1 within tolerance, no regression). Swap the passing
candidate into `models/best_model.pkl` (keep the old file as backup),
restart the API, and re-run the gate on the default path:

```powershell
python eval_gate.py    # exit 0 ships: ≥85% on the frozen 40, github/login < 0.30, zero top-site misses
```

## 7. Threat-feed pre-filter

Before the ML verdict, `/predict` checks the URL against the vendored
snapshot (`ml/data/feed_blocklist.csv`). A hit outranks the model
(phishing, risk 100) with provenance in `blocklist_hit` /
`blocklist_source`; matching is normalized exact-URL only — never
domain-wide, so shared hosts can't nuke legitimate sites. Refresh weekly
(old snapshots keep working, they just miss newly listed URLs):

```powershell
.\.venv\Scripts\Activate.ps1
python ml/refresh_blocklist.py
```

Disable without deleting anything: `BLOCKLIST_ENABLED=false`.

## 8. Review band & decision threshold

- `needs_review` flags calibrated probabilities inside [`REVIEW_BAND_LOW`,
  `REVIEW_BAND_HIGH`] (defaults 0.40–0.60). Advisory only — the verdict
  never changes because of it (~3.5% of traffic at ~45% error: route those
  exhibits to an analyst).
- `DECISION_THRESHOLD` (default 0.5, the frozen gate's assumption) moves the
  operating point. Measured candidates live in `ml/calibration_report.json`;
  preview with `eval_gate.py --threshold <t>` (the official verdict always
  uses 0.5 unless the flag is passed).
- `/model-info` reports the active threshold; every `/predict` response
  echoes it.

## 9. Configuration

`phishing_detector/backend/.env`, copied from `.env.example`:

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./phishguard.db` | SQLite file, auto-created (and auto-migrated) on startup |
| `MODEL_PATH` | `models/best_model.pkl` | Trained artifact, resolved relative to `backend/` |
| `MODEL_METADATA_PATH` | `ml/comparison_report.json` | Training report backing `/model-info` |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origin |
| `ENABLE_HTML_SCRAPING` | `false` | Fetch target pages for 7 DOM features (off = URL-only mode) |
| `SCRAPER_TIMEOUT_SECONDS` | `4.0` | Per-fetch timeout |
| `ALLOW_HEURISTIC_FALLBACK` | `true` | Rule-based verdicts when no artifact exists |
| `LOG_LEVEL` | `INFO` | Backend log verbosity |
| `BLOCKLIST_PATH` | `ml/data/feed_blocklist.csv` | Threat-feed snapshot (see §7) |
| `BLOCKLIST_ENABLED` | `true` | Exact-match pre-filter before the ML verdict |
| `DECISION_THRESHOLD` | `0.5` | Verdict operating point (frozen gate assumes 0.5) |
| `REVIEW_BAND_LOW` / `REVIEW_BAND_HIGH` | `0.4` / `0.6` | Advisory low-margin flag (never changes verdicts) |

## 10. Testing

```powershell
# Backend — 49 tests: API contract, features, degradation, feed/review/
# threshold, v3 signals, HTML collector, legacy-DB migration
cd phishing_detector\backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -q

# One file / one test:
pytest tests\test_features.py -v
pytest tests\test_api.py::test_predict_and_history -v

# Frontend — production build doubles as the template check
cd frontend
npm run build
```

## 11. Next-retrain signals (not served yet)

`ml/v3_signals.py` holds append-only candidates — `on_free_host` (13.1% of
phishing vs 1.4% of legitimate on 100k-row samples) and `domain_age_days`
(RDAP via `ml/rdap.py`, disk-cached, fail-open). Training-side only: the
25-feature serving contract is untouched. To train with them, set
`USE_V3_SIGNALS = True` (+ `RDAP_ENABLED = True` in `ml/v3_signals.py`),
run the full train, then promote the names everywhere v2 did
(`FEATURE_NAMES`, tests, frontend, docs) before shipping. `ml/collect_html.py`
crawls dataset URLs into a resumable sharded JSONL corpus for the future
HTML retrain (`--max-urls 50000` first, then scale).

## 12. Project structure

```
PhishGuard/
├── README.md                        # this file — start here
├── OVERVIEW.md                      # system design + architecture deep-dive
├── frontend/                        # React 18 + Vite 7 + Tailwind
│   └── src/{pages,components,services,utils}  # 6 pages, api client, verdict system
├── phishing_detector/backend/
│   ├── app/{routers,services,models,schemas,core,static}  # API + inference
│   ├── models/                      # best_model.pkl lives here after training (local-only)
│   ├── ml/{train,calibrate,evaluate} # pipeline + calibration + benchmarks
│   ├── ml/{refresh_blocklist,collect_html,rdap,v3_signals}  # feeds + retrain readiness
│   ├── ml/{comparison,calibration}_report.json  # training + calibration evidence
│   ├── ml/data/{eval_gate.json,hard_negatives.csv,feed_blocklist.csv}
│   ├── tests/                       # 49-test pytest suite
│   ├── eval_gate.py                 # frozen acceptance gate (exit 0 = ship)
│   ├── requirements{,-dev}.txt      # pinned deps (see §2 why)
│   └── .env.example                 # copy to .env (see §9)
├── docs/                            # SRS sources (template, diagrams, scenario, SRS)
└── tools/                           # SRS builder (output: submission packet)
```

Training data (`*.csv` except the three companions above), `*.pkl`
artifacts, `*.db` files, and `.env` are local-only and gitignored — the
sections above show how to regenerate each of them.

## 13. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| `pip install` fails building `scikit-learn` | You're on Python 3.14+ (or bare `pip` silently used another Python — `.venv` has no `pip`). Use 3.11 via `uv` (§2) |
| `:5173` won't bind / stale UI | Kill leftover `node.exe …vite` processes, `npm run dev` fresh, hard-refresh (Ctrl+Shift+R) |
| `/model-info` says `HeuristicFallback` | No artifact at `MODEL_PATH` → train (§5) or fix `.env`, restart backend |
| First start hangs | Normal: loading ~0.8 GB. Wait for `application_started`; don't start a second instance |
| Every `/predict` is 500 | Read the backend traceback; tests catch the classic causes (`test_extract_all_contains_contract` guards feature counts) |
| `/history` empty after scans | History lives in `phishguard.db` next to the backend — deleting it wipes history (recreates + auto-migrates on restart) |
| `LIGHT` toggle stuck | Theme persists in `localStorage` (`phishguard-theme`) — clear site data for a fresh look |
| Tests fail on feature counts | Expected when adding extractors — bump the count asserts in `test_api.py` / `test_degradation.py` and the list in `test_features.py` |

## 14. API quick reference

| Method | Route | Purpose |
|---|---|---|
| POST | `/predict` | `{"url"}` → verdict, confidence, risk 0–100, SHAP top-5, 25-feature vector, review/feed flags; persisted |
| GET | `/history?page=&per_page=&prediction=` | Newest-first custody log + pagination (with review/feed flags) |
| DELETE | `/history/{scan_id}` | Strike one record (204) |
| GET | `/model-info` | Model metrics, training timestamp, active threshold |
| GET | `/health` | `status`, `model_loaded`, `database_connected` |
| GET | `/docs` | Themed Swagger console |

## 15. Further reading

- `OVERVIEW.md` — full architecture, 25-feature matrix, calibration analysis
- `docs/` — SRS sources: template, diagrams, scenario, specification
