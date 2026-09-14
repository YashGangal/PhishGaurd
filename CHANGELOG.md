# PhishGuard Cleanup & Hardening — CHANGELOG

Running log of every deletion, move, and fix. Started from `pre-cleanup-snapshot` (full repo, no git history before).

## 0. Safety checkpoint
- `git init` on previously unversioned tree (`.git/` existed but was empty — no commits/branches).
- Commit `pre-cleanup-snapshot: full repo before audit cleanup` + branch `pre-cleanup-snapshot`.
- Verified `.gitignore` already excludes: `__pycache__/`, `*.py[cod]`, `.venv/`, `.env` (keeps `!.env.example`), `*.pkl`, `*.db`, `*.csv`, `.pytest_cache/`, `.coverage`, `htmlcov/`, `node_modules/`, `dist/`. No edit needed; `git status --ignored` confirms venv, node_modules, dist, .env, pkl, db, csv all ignored. Local-only files left untouched on disk.

## Phase 2 — Cleanup
- MOVED `Frontend-Prompt.md` → `archive/Frontend-Prompt.md` (generic agent prompt, not PhishGuard-specific; no code references).
- MOVED `Project Prompt.txt` → `archive/Project Prompt.txt` (v1 genesis spec superseded by INTEGRATED-v2 + `files/* v1.1` + backend README; slate theme / 4 pages / Axios / Demo-mock / RBF-SVM all stale).
- MOVED `project_overview.md` → `archive/project_overview.md` (early abstract that defers to OVERVIEW.md).
- MOVED `files/06_frontend_component_tree.md` → `archive/06_frontend_component_tree.md` (stale: Axios/Demo-mock/ScanProvider/4 routes vs `fetch`/6 routes; superseded by INTEGRATED-v2).
- MOVED `firetest-results.json` → `archive/firetest-results-v1-heuristic.json` (heuristic-era 6/15 evidence; v2 `firetest-results-v2.json` stays at root as current).
- DELETED `phishing_detector/models/` (contained only `.gitkeep`; orphaned scaffold — real artifact dir is `phishing_detector/backend/models/`; zero code references).
- EDITED `OVERVIEW.md`: metrics table now mirrors `comparison_report.json` (1,225,480 URLs; RF 91.95/89.92/88.73/89.32/0.9693; calibrated-linear SVM row); `/api-docs` → `/model-api`; removed Chart.js/Recharts (no chart dep — custom SVG); Axios → fetch; structure map rewritten to archive/ layout + local-only data note.
- EDITED `files/01_system_architecture.md`: page list 4 → 6 pages; Axios → fetch.
- Data files (NOT deleted, local-only, gitignored): `backend/models/best_model.pkl` (~3.4 GB), `backend/ml/data/phish_urls.csv` (73 MB), root `phishing_urls.csv` (32 MB), `backend/phishguard.db` (127 KB), `backend/.env`.
- Dead-code sweep: no commented-out blocks or unused imports found in backend (`grep` clean); no `console.*` in frontend.

## Phase 3 — Backend fixes
- FIXED `app/core/config.py` + `.env.example`: defaults `../models/best_model.pkl` / `../ml/comparison_report.json` → `models/best_model.pkl` / `ml/comparison_report.json` (backend-relative, matching `ml/train.py` output + live `.env`). Without this, any run without `.env` silently fell back to the heuristic classifier.
- FIXED `app/services/scraper.py`: removed invalid `requests.get(..., max_redirects=5)` kwarg (raised `TypeError`, uncaught — would crash `/predict` when scraping enabled). Added: expanded SSRF blocklist (`0.0.0.0/8`, `100.64.0.0/10`, `::/128`, `fe80::/10`), best-effort DNS-resolution check for rebinding domains, 2 MB response cap (Content-Length pre-check + post-read check), hostname-only logging (no query-token leaks).
- FIXED `app/services/explainability.py`: `_fallback_impacts` was missing `domain_length` (21 of 22 weights) — added `0.02`, consistent with per-char signals.
- FIXED `app/services/feature_engineering.py`: `has_double_slash_redirect` used `url[7:]` (assumed `http://` length) — now splits on `://`, scheme-agnostic.
- FIXED `app/services/prediction.py`: thread-safe `load_bundle` (double-checked lock); corrupt/malformed pickle now falls back with a warning (or 503 if fallback disabled) instead of raw 500; validates `predict_proba` presence; `model_metadata()` no longer merges RandomForest report scores onto the heuristic fallback; added `algorithm` to metadata (preserves `deterministic-rules`); `fromisoformat` handles `Z` suffix; catches `UnicodeDecodeError` on report read.
- FIXED `app/routers/predict.py`: `algorithm` column now stores the real algorithm (was duplicating `model_name`); creating a new model version deactivates old `is_active` rows; `file_path` stores the resolved candidate path; scrape+extract moved inside `try`; failures now logged (`prediction_failed`).
- FIXED `app/routers/model_info.py`: health-probe failures now logged instead of swallowed.
- FIXED `ml/train.py`: missing URL/label columns raise descriptive `ValueError` (was bare `StopIteration`); single-class datasets rejected before `stratify` crash; SMOTE `MemoryError`/`ValueError` handled (was `ImportError` only); same-day retrain gets a unique version suffix (avoids `ModelMetadata.version` collision; `best_model.pkl` stays the current-pointer file by design).
- FIXED `ml/evaluate.py`: single-class `roc_auc` guarded (chance-level 0.5) instead of `ValueError` crash.
- FIXED `tests/conftest.py`: `sqlite://` → `sqlite:///:memory:` + `StaticPool` (was flaky across TestClient threads); pins the heuristic bundle so tests never load the 3.4 GB artifact.
- FIXED `tests/test_features.py`: imported 7 non-existent functions (collection `ImportError`, 0 tests ran) — rewritten against `extract_all`; HTML signals asserted via parsed-document output (verified values).
- ADDED `tests/test_degradation.py`: URL-only fallback contract (`html_features_available is False`, 23 features, 5 shaped top-features), SHAP-fallback coverage incl. `domain_length` regression, heuristic-metadata honesty (no trained scores), health shape.
- Result: **25 passed** (was: collection error).

## Phase 4 — Frontend fixes
- FIXED `src/services/api.js`: single env-driven config (`VITE_API_BASE`, `VITE_API_URL`, `VITE_DOCS_URL`); `Content-Type` only sent with a body; malformed 200-body raises a readable error instead of raw `SyntaxError`. ADDED `frontend/.env.example`.
- FIXED `src/pages/ModelAPI.jsx`: 3× hardcoded `http://localhost:8000` → `API_ORIGIN`/`DOCS_URL`; clipboard fallback for non-secure contexts; cleared stacked copy timers; guarded `toUpperCase`; serving-instrument shows MODEL UNREACHABLE on failure.
- FIXED `src/App.jsx`: custody bar reflects reality (`BENCH OFFLINE`/`MODEL OFFLINE` on fetch failure; `String()` guards); documented the 5-slot mobile-bar omission of Report.
- FIXED `src/pages/Overview.jsx`: backend-down vs empty-DB distinguished (`BENCH UNREACHABLE…`); `String()` version guards.
- FIXED `src/pages/Analytics.jsx`: flag-rate no longer renders `0.0%` when `phishing` is still null (requires both counters); version guard.
- FIXED `src/components/VerdictTag.jsx`: risk-level suffix was suppressed exactly for `caution` — now shown for all tiers.
- FIXED `src/utils/verdict.js`: `tierOf` fails closed (unrecognized payload → `caution`, never `safe`).
- FIXED `src/pages/History.jsx`: failed delete keeps the modal open with an error (was silent close); mid-paginate export failure surfaces instead of silently writing a partial CSV.
- FIXED `src/pages/Report.jsx`: `sessionStorage` payload validated (corrupt/old-schema → explicit unreadable state, not a crash); invalid-date and non-number guards.
- FIXED `src/pages/ScanURL.jsx`: `copyResult` guards malformed payloads; idle recent-list distinguishes backend-down.
- FIXED `src/components/ErrorBoundary.jsx`: `componentDidCatch` logging + Try-again (state reset) alongside reload (was reload-only with dead `setState`).
- FIXED `src/components/ScanBeam.jsx`: gradient id via `useId` (was module-global, collided on dual mount).
- FIXED `src/utils/helpers.js`: `downloadCsv` captures the object URL before revoking.
- DEDUPED feature lists into new `src/utils/features.js` (was copy-pasted in ScanURL + Report).
- FIXED `package.json`: added `engines: { node: ">=18" }`; removed `lint` script (referenced uninstalled eslint — failed on fresh install).
- Result: `npm run build` clean (1816 modules, no warnings).

## Phase 5 — Reproducibility
- ADDED `phishing_detector/backend/.python-version` (`3.11`) — README claim now enforced for uv users.
- Backend requirements: already fully `==`-pinned, no prod/dev duplicates, no missing imports (verified import-by-import). Deleted `.venv` entirely; rebuilt fresh via `uv venv --python 3.11` + `uv pip install -r requirements.txt -r requirements-dev.txt` — all pins reproduce exactly (sklearn 1.5.1, numpy 2.0.1, pandas 2.2.2, xgboost 2.1.0, shap 0.46.0, fastapi 0.111.0, …). Full suite in fresh venv: **25 passed**.
- Documented setup + pin rationale (pickle-compat warning) in `phishing_detector/backend/README.md` and root `OVERVIEW.md` quickstart.
- Frontend: `package-lock.json` committed and verified in sync; deleted `node_modules`, `npm ci` from lockfile succeeds, `npm run build` clean. Note: `npm audit` reports 4 vulns (3 moderate, 1 high) in locked deps — left as-is for reproducibility; upgrade deliberately, not incidentally.

## Phase 6 — Tier-1 audit fixes (production-readiness pass)
- RESTORED `FIRETEST-REPORT.md`, `firetest-results-v2.json`, `firetest-urls.json` (accidentally deleted in worktree; still referenced by OVERVIEW/README/IMPROVEMENT-PLAN).
- FIXED `ml/train.py`: `USE_SMOTE = False` was declared but SMOTE ran unconditionally — the flag is now honored (verified: mini-train prints "SMOTE disabled", full v2 artifact was trained with SMOTE off per plan). Rewrote the 1000-line box-drawing UI back to plain ASCII: it crashed with `UnicodeEncodeError` on Windows cp1252 consoles before training a single row.
- REWROTE `eval_gate.py` output to plain ASCII (same crash class — the gate is a documented release workflow and must run on Windows). Gate logic untouched: v2 artifact `randomforest_v2_2026-09-14_164407` passes 3/3 (37/40 = 92.5%, github/login p=0.145, topsite 0 misses).
- STRIPPED spinner/sleep presentation helpers from all 3 test files (they broke `pytest -s` on Windows: 4/4 failed). Assertions kept/extended (26-key contract, reputation/keyword signals). Suite: **29 passed**, incl. `pytest -s`.
- FIXED `prediction.py`: feature vector now slices to the artifact's own `n_features_in_`, so a v1 (22-feature) rollback artifact serves correctly with v2 code.
- FIXED `feature_engineering.py`: duplicate `steam` alternative in `_BRAND_RE`.
- FRONTEND: `features.js` URL list 15 → 18; all `22-feature` copy → 25; Analytics matrix updated to v2 report numbers.
- DOCS: OVERVIEW/files specs/backend README/root README now state 25 features + v2 metrics; IMPROVEMENT-PLAN records the v2 outcome (calibration deferred — gate passes without it); root README uses relative paths and the correct `backend/models/` location.
- IGNORED `*.log`, deleted stale `ml/train-v2.log` + `frontend/dist/`; `hard_negatives.csv` (1.8 KB, curated) is now versioned via a `.gitignore` exception.
- VALIDATED: mini end-to-end train (400 rows + 54 hard negatives → artifact + report, gate 3/3 on the mini model), live API smoke test on :8123 (health/model-info/predict/history/422 all correct), `npm run build` clean (1816 modules).

