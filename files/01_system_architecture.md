# 01 — System Architecture (REVISED v1.1)

## Changes from v1.0
- Risk score thresholds updated: `0-33` low / `34-66` medium / `67-100` high (was `<40 / 40-70 / >70`)
- Added `html_features_available` flag in prediction response flow

---

## 1. High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                              CLIENT                                  │
│                     React 18 + Vite + Tailwind                       │
│   Overview │ Scan URL │ History │ Analytics │ Model & API │ Report      │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ HTTPS (fetch)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                              │
│                                                                        │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐                    │
│  │ predict.py │   │ history.py │   │model_info.py│                   │
│  │ POST       │   │ GET /GET/  │   │ GET /health │                   │
│  │ /predict   │   │ DELETE     │   │ GET /model- │                   │
│  │            │   │ /history   │   │ info        │                   │
│  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘                    │
│        │                │                │                           │
│        ▼                ▼                ▼                           │
│  ┌──────────────────────────────────────────────┐                    │
│  │              SERVICE LAYER                    │                    │
│  │                                                │                    │
│  │  feature_engineering.py  (22 pure functions)   │                    │
│  │  prediction.py           (model load + infer)  │                    │
│  │  explainability.py       (SHAP top-5 features)  │                    │
│  │  scraper.py              (optional HTML fetch) │                    │
│  └───────────────┬────────────────────────────────┘                    │
│                  │                                                     │
│        ┌─────────┴─────────┐                                          │
│        ▼                   ▼                                          │
│  ┌───────────┐       ┌───────────┐                                    │
│  │  ML MODEL │       │  SQLite   │                                    │
│  │ best_     │       │ ScanHist- │                                    │
│  │ model.pkl │       │ ory /     │                                    │
│  │           │       │ ModelMeta │                                    │
│  └───────────┘       └───────────┘                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Request Lifecycle (POST /predict)

```
User enters URL
      │
      ▼
Frontend validates format (basic regex) ──▶ POST /predict {url}
      │
      ▼
Pydantic HttpUrl validation (FastAPI)
      │
      ▼
feature_engineering.extract_all(url, html?) ─▶ 22-feature vector
      │
      ▼
scraper.py attempts HTML fetch (4s timeout)
      │
      ├──▶ Success ──▶ html_features_available = true
      │
      └──▶ Fail/Timeout ──▶ html_features_available = false
              HTML features default to 0/False
      │
      ▼
prediction.load_model() (cached singleton) ─▶ predict_proba()
      │
      ▼
risk_score = round(confidence * 100)
risk_level = low (0-33) / medium (34-66) / high (67-100)
      │
      ▼
explainability.top_features(model, vector) ─▶ top 5 SHAP contributions
      │
      ▼
Persist row to ScanHistory (SQLite)
      │
      ▼
Return JSON { scan_id, prediction, confidence, risk_score,
              risk_level, html_features_available, features, top_features }
      │
      ▼
Frontend renders ConfidenceCircle + RiskBadge + FeatureBar list
```

## 3. Component Responsibilities

| Layer | Responsibility | Does NOT do |
|---|---|---|
| Frontend | Rendering, client-side validation, state, charts | Feature extraction, scoring |
| Routers | HTTP contract, status codes, request/response shaping | Business logic |
| Services | Feature extraction, inference, SHAP, scraping | HTTP concerns |
| ML artifacts | Trained model + preprocessing pipeline | Persistence |
| SQLite | Durable history + model metadata | Business logic |

## 4. Deployment Topology (target)

```
┌────────────┐        ┌────────────┐        ┌──────────────┐
│  Vercel /  │  HTTPS │  Render /  │  file  │  SQLite (or   │
│  Netlify   ├───────▶│  Railway   ├───────▶│  MongoDB)     │
│  (frontend)│        │ (FastAPI)  │        │  volume       │
└────────────┘        └────────────┘        └──────────────┘
```

Notes:
- No third-party threat-intelligence APIs anywhere in the chain — matches the "no paid APIs" constraint.
- `scraper.py` is optional and only invoked when HTML-based features are requested; URL-only prediction must work without a live fetch, so the system degrades gracefully if a target site is unreachable.
- **Risk level thresholds:** `low = 0-33`, `medium = 34-66`, `high = 67-100`.
