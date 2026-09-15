# PhishGuard Improvement Plan — Tier 1 Batch
**Goal:** fire-test 9/15 → ≥12/15, holdout F1 within 1pt of 89.3%, kill the
reputable-site false-positive class. **One retrain, not three.**
**Status:** SHIPPED 2026-09-15 — v2 retrained, isotonic-calibrated (v3
`randomforest_v2_2026-09-14_164407_calibrated`, 800 MB), gate **3/3**
(36/40 = 90.0%, `github.com/login` p=0.063, topsite-legit 0 misses),
live round-3 fire-test **12/15** (goal met; 6/6 legit, 6/9 phish).
Tier-2 trust layers also shipped (feed pre-filter, review band,
configurable threshold). Only machine-time items remain (full v3/HTML
retrains) — none are release blockers.

## Principles
1. **Measure first.** Nothing ships without beating the gate (Phase 0).
2. **One expensive step.** Full training runs take hours — all changes land in a
   single retrain. Subset runs validate direction first.
3. **Append-only features.** New feature names go at the END of `FEATURE_NAMES`
   so stored `features_json` rows and SHAP indices stay comparable.
4. **No half-on systems.** HTML scraping stays OFF (its features trained as
   all-zero; feeding live values now would create new github-class bugs).

## Phase 0 — Eval gate (est. 30 min, no model changes)
**Why first:** every later claim needs a trusted ruler.

1. Freeze the test set: existing 15 fire-test URLs + ~30 top-site login/account
   pages (github, google, banks, SaaS logins as legitimate; 10 fresh OpenPhish
   URLs as phishing) → `backend/ml/data/eval_gate.json`
   (`[{url, expected}]`, 40 rows frozen 2026-09-14).
2. New script `backend/eval_gate.py`: loads an artifact path (default: production
   `MODEL_PATH`), extracts URL-only features, predicts, prints per-URL table +
   summary. Must run against ANY artifact: `python eval_gate.py --model <pkl>`.
3. Record the baseline in this file (round-2 numbers: 9/15, github p=0.96).

**Gate (candidate ships iff ALL hold):**
- ≥85% on the 40-set (≥34/40) — fire-test subset ≥12/15
- `github.com/login` phishing-probability < 0.30
- Zero misses on the top-site legitimate subset
- Holdout F1 within 1.0pt of 89.3 (no regression on the general task)
- Artifact ≤1 GB (target ≤500 MB), API startup load measured and noted

## Phase 1 — Features (est. 1–2 h, code only)
Three new URL-side features (22 → 25 total):

1. **`domain_in_top_list`** — registrable domain in a top-sites reputation list.
   - New file `backend/ml/data/reputation_top1m.csv` (Cisco Umbrella top-1M,
     `rank,domain` rows; downloaded once, gitignored via `*.csv`; documented
     in `backend/README.md`).
   - Loader in `feature_engineering.py`: module-level frozenset, empty-set
     fallback with a warning if the file is absent (never crash).
   - Expected effect: instant exoneration of github/wikipedia/google class.
2. **`has_auth_keyword`** — `login|signin|verify|account|password|2fa|otp`
   in path/query (case-insensitive).
3. **`keyword_domain_mismatch`** — auth/finance brand keyword
   (`paypal|apple|google|microsoft|amazon|bank|…`, ~40 terms) appears in
   subdomain/path but NOT in the registrable domain — the true phish shape
   (`evil.com/paypal-login`), replacing today's entropy-proxy guessing.
4. Append all three to `FEATURE_NAMES` **at the end** (indices 22–24):
   `domain_in_top_list`, `has_auth_keyword`, `keyword_domain_mismatch`.
5. Update feature-count assertions in `backend/tests/test_features.py`.

**Do NOT:** renumber existing features, enable HTML scraping, touch SHAP code
(new names flow through automatically).

## Phase 2 — Hard negatives (est. 30 min, data only)
- New file `backend/ml/data/hard_negatives.csv` (`url,label` all `0`):
  40–60 top-site login/account/verify pages — the exact neighborhood that is
  80%-phishing in training today.
- `ml/train.py::load_dataset`: concat this file into the frame AFTER dedup,
  before split (a few lines; file is versioned and reusable every retrain).

## Phase 3 — Retrain (est. 1 h active + 4–10 h machine time)
1. **Subset validation first:** 5k-row run with the 3 new features — confirm
   direction (github p drops, holdout F1 sane) before spending hours.
2. **Full run config changes** (in `ml/train.py`):
   - `RandomForest(max_depth=25, min_samples_leaf=2, n_estimators=200, …)` —
     attacks the 3.3 GB artifact; tune on subset if F1 slips.
   - **Drop SMOTE** (recommendation): `class_weight="balanced"` already handles
     imbalance; SMOTE on ~500k minority rows costs hours/RAM for ~zero gain.
     Keep the import behind a flag, default off, note the decision here.
   - **Isotonic calibration** on the validation split (`CalibratedClassifierCV(cv="prefit")`)
     — ends 0.94-on-github overconfidence so scores become meaningful.
   - **Version bump:** current scheme (`{name}_v1_{date}`) would collide with
     today's artifact — bump to `{name}_v2_{date}` so custody rows stay distinct.
3. Run full `python -m ml.train`, record report metrics in this file.
   **v2 outcome (2026-09-14):** RF acc 93.55 / prec 92.34 / rec 90.51 /
   F1 91.41 / ROC-AUC 0.9827 on 1,225,534 rows (+54 hard negatives);
   artifact `randomforest_v2_2026-09-14_164407`, 838 MB.
   SMOTE stayed off (`USE_SMOTE=False`).
   **Calibration DONE 2026-09-15** (`ml/calibrate.py`, no retrain):
   isotonic prefit on 122,553 held-out rows (split recovered
   deterministically; reproduced the report to 5e-05, wrong-split
   controls deviate 1e-02). Half-B eval: Brier 0.0493→0.0465, log-loss
   0.1702→0.1563, F1 0.9145→0.9135, ROC-AUC 0.9829 flat; v3 artifact
   `…_calibrated` (800 MB) passes the gate 3/3 and serves production.

## Phase 4 — Ship (est. 30 min) — DONE 2026-09-15
1. ~~Run `eval_gate.py` against the candidate~~ — v3 passes 3/3
   (36/40, github p=0.063, topsite 0 misses).
2. ~~Back up current `best_model.pkl`, swap candidate in, restart backend,
   confirm `/model-info`~~ — v2 kept as `best_model_v2_uncalibrated.pkl`,
   v3 serves; `/model-info` shows `…_calibrated` + calibrated metrics.
3. ~~Re-run the 15-URL live fire test through the API~~ — round 3: **12/15**
   (goal met), 6/6 legit incl. github + python-docs, SHAP/persistence OK.
4. ~~Frontend sweep (feature count 22 → 25)~~ — done (lists, copy, metrics).
5. ~~Update `FIRETEST-REPORT.md` with round-3 numbers~~ — done.

## Residual gate misses (Tier-2 fuel, NOT release blockers)
All three are structurally legit-looking on URL signals alone (short,
https, no IP/`@`/keywords, absent from the reputation list):
- `sub.parsnetsecure.ir` (p=0.12), `virtualnextpartner.com` (p=0.15) —
  confident-wrong; only page-content or feed signals can catch this class.
- `teamyk.com` (p=0.49) — honest borderline (was 0.55 raw).
- `wordpress-…-0.cloudclusters.net` (p=0.15) — attacker subdomain on a
  reputable shared host: `cloudclusters.net` is IN the top-1M list, so
  `domain_in_top_list` exonerates it. Known blind spot of registrable-
  domain reputation; the principled fix (free-host-aware discounting)
  needs a retrain and is Tier-2.

## Rollback
Old artifact backup + previous `comparison_report.json` restore + restart.
Old custody rows keep working (feature append-only; SHAP reads stored JSON).

## Explicitly parked (not this batch)
- HTML scraping + retrain: collector ready (`ml/collect_html.py`, resumable
  JSONL corpus) — needs the machine-days crawl + full retrain, then the
  v3-signal promotion checklist.
- Threshold change: MEASURED (FPR≤1% at t=0.80/TPR 81%; FPR≤5% at t=0.40;
  Youden J at t=0.37), SHIPPED as `DECISION_THRESHOLD` (default frozen 0.5)
  with `eval_gate.py --threshold` previews — flipping the default further
  needs the gate unfrozen (product decision).
- Abstain band: QUANTIFIED + SHIPPED advisory (`needs_review` in API/DB/UI,
  3.5% traffic at 44.9% error) — enforcing it (withhold verdict) needs a
  contract change (product decision).
- Feed first-pass blocklist: SHIPPED (vendored URLhaus snapshot +
  `ml/refresh_blocklist.py` + exact-match pre-filter; no gate overlap on
  2026-09-15, value is prospective — refresh weekly).
- Domain-age/WHOIS signals: SHIPPED as training-side code (`ml/rdap.py` +
  `ml/v3_signals.py`, RDAP verified live, free-host lift 9.4x measured) —
  needs `USE_V3_SIGNALS` full retrain to take effect.

## Estimates
Active work ≈ 4 h across 2 sessions · machine time ≈ one overnight train ·
Risk: medium (one long run); mitigated by subset validation + gates + rollback.
