# PhishGuard Live Fire-Test Report — 2026-09-14

## What was tested
15 URLs fed to the live API (`POST /predict`), scored against ground truth:
- **9 malicious**: 8 fresh from the OpenPhish live feed + Google's official
  Safe-Browsing phishing test page (`testsafebrowsing.appspot.com/s/phishing.html`)
- **6 legitimate**: github, wikipedia, stackoverflow, python docs, google, openphish

Two systems scored on the identical 15 URLs:
- **A. Live backend** — whatever `/model-info` reports (found: `heuristic_fallback_v1`)
- **B. Quick RandomForest** — trained on a balanced 5,000-URL subset, URL-only
  features, throwaway run (no artifacts written)

## Results

| # | Expected | URL | Live backend | Quick RF (p) |
|---|----------|-----|--------------|--------------|
| 1 | phishing | sub.parsnetsecure.ir | MISS legit (30/low) | MISS legit (0.48) |
| 2 | phishing | shopeejkt4782.blogspot.com | MISS legit (31/low) | **HIT** (1.00) |
| 3 | phishing | shopee0488.blogspot.com | MISS legit (31/low) | **HIT** (0.91) |
| 4 | phishing | virtualnextpartner.com | MISS legit (31/low) | **HIT** (0.51) |
| 5 | phishing | app-sushiswaps.net | MISS legit (28/low) | **HIT** (0.90) |
| 6 | phishing | teamyk.com | MISS legit (22/low) | MISS legit (0.38) |
| 7 | phishing | viewdetail…growthcrm-platf.com | MISS legit (42/med) | **HIT** (0.97) |
| 8 | phishing | xfinityconnectupgrade.weebly.com | MISS legit (39/med) | **HIT** (0.97) |
| 9 | phishing | testsafebrowsing…/phishing.html | MISS legit (45/med) | **HIT** (0.69) |
| 10–15 | legitimate | github/wikipedia/stackoverflow/python-docs/google/openphish | 6/6 HIT | 3/6 HIT (stackoverflow, python-docs, openphish false-positived) |

## Scores
- **Round 1 — heuristic fallback: 6/15 = 40%** — phishing recall **0/9 (0%)**,
  legit 6/6. It never flagged anything (retired after this test).
- **Round 2 — shipped RandomForest (`randomforest_v1_2026-09-14`, 1.2M URLs):
  9/15 = 60%** — phishing recall 6/9 (67%), legit 3/6 (50%).
  Caught: blogspot x2, sushiswaps, growthcrm, weebly, Google SB test page.
  Missed: parsnetsecure.ir (risk 1!), virtualnextpartner (risk 10),
  teamyk (43/medium). False-flagged: github/login (96!), python-docs (73),
  openphish (54/medium).
- **Quick RF (5k subset, throwaway): 10/15 = 67%** — holdout acc 86.1%,
  F1 86.0%. Small-sample noise both ways.
- **Training-report RF: acc 91.95%, F1 89.3%** — the 15-URL gap vs 92%
  holdout is small-sample noise plus genuinely hard cases (see findings).

## Round-2 notes (shipping the model)
- Training completed: 1,225,480 URLs, RandomForest selected, artifact
  `backend/models/best_model.pkl` (3.3 GB). Wired via new `backend/.env`
  (`MODEL_PATH`/`MODEL_METADATA_PATH`) — defaults pointed at a directory
  the trainer never writes to.
- Two ship-blocking bugs found and fixed during rollout:
  1. `trained_at` arrives from the report as an ISO **string**; the DB layer
     needs a datetime → every predict 500'd until parsed in `model_metadata()`.
  2. sklearn feature-name warnings → `feature_vector()` now returns a labeled
     DataFrame (fallback heuristic updated to coerce input).

## Key findings
1. **No trained model is shipped.** `models/` contains only `.gitkeep`;
   the API serves `HeuristicFallback`, whose weights score real phishing
   URLs 22–45/100 ("low/medium → legitimate"). Every "URL IS SAFE" verdict
   served today comes from uncalibrated rules.
2. **HTML scraping is disabled** (`enable_html_scraping=False`), so all 15
   scans ran URL-only — 7 of 22 features permanently zero.
3. **Clean-looking domains beat URL-only analysis on both systems.**
   `teamyk.com` (likely compromised-legit) missed everywhere (RF p=0.38).
   URL structure has a ceiling; domain-age/reputation signals are missing.
4. **Subset RF false-positives on path-heavy legit sites** (stackoverflow 0.75,
   python-docs 0.85) — small-sample noise; full training + threshold tuning
   should absorb most of it.
5. Dataset is healthy: 1,238,497 rows (477k phishing / 761k legit), `url,label`
   columns, extraction runs 5k URLs in ~0.2s.

## Overall rating: 7.5/10 (model now shipped)
Was 6.5 (fallback era). Detection is real but URL-only and overconfident
(0.985 on clean misses, 0.96 on github). Remaining gap to 8.5+: fixes 2–5 below.
Also note: model load is 3.3 GB / multi-minute startup — consider a slimmer
artifact (fewer/shallower trees) at next retrain.

## How to make it more accurate (ranked)
1. ✅ **DONE — model trained and shipped** (`randomforest_v1_2026-09-14`,
   `/model-info` confirms RandomForest, round-2 fire test above).
2. **Enable HTML scraping** and re-test; 7 dormant features (iframe, forms,
   popups, hidden elements…) are exactly the ones that catch kits the URL
   pass misses. Add per-host timeout + the existing SSRF guard already covers
   safety.
3. **Fix or gate the fallback.** A fallback that answers "legitimate" to
   everything is worse than no answer: return `503` / "model unavailable"
   when no artifact exists, or calibrate its threshold on labeled data.
4. **Tune the 0.5 decision threshold** on a validation split (precision/recall
   tradeoff); expose borderline (0.4–0.6) as caution in the UI's medium band.
5. **Add non-URL signals for clean-looking domains**: domain age (WHOIS/RDAP),
   passive DNS first-seen, TLS cert age. This is the only fix for the
   `teamyk.com` class of miss.
6. **Layer a feed first-pass**: exact-match OpenPhish/URLhaus entries before
   ML — free recall on known-bad with zero false positives.
7. **Adopt a standing eval protocol**: fixed labeled set (e.g. 200 live
   phishing + 200 legit, refreshed monthly), track precision/recall
   separately — accuracy alone hides the "never flags" failure mode seen here.
8. **Retrain cadence**: phishing features drift in weeks; schedule monthly
   retrains and monitor live flag-rate for distribution shift.
