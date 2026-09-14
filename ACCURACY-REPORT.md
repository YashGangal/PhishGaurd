# PhishGuard Live Accuracy Test — Report (2026-09-14)

## How it was tested
- **Serving model:** `randomforest_v1_2026-09-14_141646` (RandomForest, trained on 1,225,480 URLs; held-out acc 91.97%, F1 89.35%).
- **Mode:** URL-only (`ENABLE_HTML_SCRAPING=false`, the current default) — only the URL string was analyzed, no page was fetched. Raw per-URL results: `accuracy-test-results.json`.
- **Test set (24 URLs):** 12 known-phishing (Google Safe Browsing test pages + classic confirmed-phishing patterns: suspicious TLDs, brand typosquatting, free-hosting, raw-IP host) and 12 well-known legitimate sites, deliberately including 3 tricky legitimate login pages (`github.com/login`, `docs.python.org`, `login.microsoftonline.com`).

## Score
| Metric | Result |
|---|---|
| Overall accuracy | **20/24 = 83.3%** |
| Phishing recall (caught 11/12) | **91.7%** |
| Legitimate specificity (cleared 9/12) | **75.0%** |
| Precision (11 true alarms / 14 alarms) | **78.6%** |

**Rating: 7/10.** Strong on textbook phishing signals (11/12 caught, including raw-IP, `.tk/.gq/.ml` brands, blogspot and free-hosting kits), but it cries wolf on legitimate login pages and is overconfident when wrong.

## The 4 misses
| Expected → Got | Conf / Risk | URL | Diagnosis |
|---|---|---|---|
| phishing → legitimate | 0.55 / 46 medium | `https://testsafebrowsing.appspot.com/s/phishing.html` | Borderline call — and note the `http://` twin of the same page WAS caught. The `has_https` feature pushed a known-bad page to the safe side. HTTPS ≠ safe. |
| legitimate → phishing | **0.94 / 94 high** | `https://github.com/login` | Worst error: a top-50 legit site flagged with 94% confidence. `/login` path + short domain trips URL-only signals. Overconfidence here is the real problem, not just the error. |
| legitimate → phishing | 0.68 / 68 high | `https://docs.python.org/3/` | Benign docs page flagged — `docs` subdomain + digit path pattern-matches phishing kits. |
| legitimate → phishing | 0.77 / 77 high | `https://login.microsoftonline.com/` | Real Microsoft login flagged — `login` subdomain looks like credential-harvesting to a URL-only model. |

## How to make it more accurate (in priority order)
1. **Turn on the HTML pass** (`ENABLE_HTML_SCRAPING=true`, after the scraper fixes in this cleanup). All 3 false positives are login pages a DOM check would resolve instantly: real GitHub/Microsoft pages have same-domain forms and sane link graphs; phishing kits don't. This is the single biggest lever — the model was trained with 7 HTML features it currently never gets.
2. **Hard-negative retraining:** add legitimate login/auth pages (github, microsoftonline, bank logins) to the training set and retrain. The 1.2M-row set is clearly light on this category — the model never learned what a *real* login page looks like.
3. **Calibrate confidence:** 0.94 on `github.com/login` means the probabilities are overconfident. Wrap the winner in `CalibratedClassifierCV` (like the SVM candidate already is) and add an abstain band (e.g. risk 40–60 → "uncertain, review manually") instead of forcing a verdict.
4. **Add mismatch features:** brand-keyword-in-URL-but-not-in-domain (`paypal` in `evil-download.top`), domain age/WHOIS, TLS certificate validity. These directly target the `https://…phishing.html` miss class.
5. **Tune the operating threshold:** 0.5 is arbitrary. For a forensic tool, false alarms erode trust faster than misses — pick the threshold off the ROC curve (e.g. fix FP rate ≤5%) instead of the default.
6. **Layer a blocklist pre-filter** (Google Safe Browsing API) in front of the ML verdict for known-bad URLs, and consider an RF+XGBoost ensemble — XGBoost was close behind (F1 85.2%) and ensembles smooth out RF's overconfident corners.
7. **Make this test permanent:** fold the 24-URL set into `tests/` as a regression gate (with the GSB pages as anchors) and re-run it after every retrain — accuracy should be plotted over time in `comparison_report.json`, not re-discovered manually.
