# 04 — Feature Engineering Spec

25 features total: 18 URL-side signals (always available, no network call)
and 7 HTML/webpage features (only computed when a live fetch succeeds — the
system must still predict from URL-only features if the page can't be reached).

Every extractor in `feature_engineering.py` is a pure function of signature
`(url: str) -> T` or `(html: str) -> T`, returns a safe default on malformed
input, and has a matching unit test in `tests/test_features.py`.

## A. URL-Structure Features (15)

| # | Feature | Type | Extraction Logic |
|---|---|---|---|
| 1 | `url_length` | `int` | `len(url)` |
| 2 | `domain_length` | `int` | `len(tldextract.extract(url).domain)` |
| 3 | `num_dots` | `int` | count of `.` in the full URL |
| 4 | `num_hyphens` | `int` | count of `-` in the domain/path |
| 5 | `num_digits` | `int` | count of `[0-9]` chars in the URL |
| 6 | `num_subdomains` | `int` | `len(tldextract.extract(url).subdomain.split('.'))` if non-empty else 0 |
| 7 | `has_https` | `bool` | `urlparse(url).scheme == "https"` |
| 8 | `has_ip_address` | `bool` | regex match: domain is a dotted IPv4/hex/octal literal |
| 9 | `has_at_symbol` | `bool` | `"@" in url` (classic redirect-obfuscation trick) |
| 10 | `has_double_slash_redirect` | `bool` | `"//"` appears after position 7 of the URL (i.e., not just the scheme separator) |
| 11 | `is_shortened_url` | `bool` | domain matches a known-shortener list (bit.ly, tinyurl.com, t.co, goo.gl, ...) |
| 12 | `num_suspicious_chars` | `int` | count of `@ % _ = &` in the URL |
| 13 | `url_entropy` | `float` | Shannon entropy of the URL string, rounded to 2 dp |
| 14 | `has_suspicious_tld` | `bool` | TLD in a known-abused list (`.xyz`, `.top`, `.tk`, `.gq`, `.ml`, ...) |
| 15 | `path_length` | `int` | `len(urlparse(url).path)` |

## B. HTML/Webpage Features (7)

Computed by `scraper.py` fetching the page (short timeout, e.g. 4s) and parsing
with BeautifulSoup4. If the fetch fails or times out, these 7 default to `0`/`False`
and a `html_features_available: false` flag is included in the response.

| # | Feature | Type | Extraction Logic |
|---|---|---|---|
| 16 | `has_iframe` | `bool` | page contains an `<iframe>` tag |
| 17 | `redirect_count` | `int` | number of redirects followed by `requests` before reaching final URL |
| 18 | `num_external_links` | `int` | count of `<a href>` whose domain differs from the page's own domain |
| 19 | `form_action_suspicious` | `bool` | any `<form action="">` empty, or pointing to a different domain, or to a raw IP |
| 20 | `has_javascript_events` | `bool` | presence of `onmouseover`, `onload`, `onclick`-style handlers tied to redirect/hide behavior |
| 21 | `has_popup_window` | `bool` | script contains `window.open(` |
| 22 | `has_hidden_elements` | `bool` | any element with `display:none`, `visibility:hidden`, or `opacity:0` inline style |

## C. Reputation & Keyword Features (3, appended for v2 — never renumber A/B)

| # | Feature | Type | Extraction Logic |
|---|---|---|---|
| 23 | `domain_in_top_list` | `bool` | registrable domain in `ml/data/reputation_top1m.csv` (Cisco Umbrella top-1M); missing file = always `False` (warns, never crashes) |
| 24 | `has_auth_keyword` | `bool` | `login\|signin\|verify\|account\|password\|2fa\|otp` in subdomain/path/query |
| 25 | `keyword_domain_mismatch` | `bool` | brand keyword in subdomain/path but NOT in the registrable domain (the `evil.com/paypal-login` shape) |

## D. Preprocessing Pipeline (Phase 2 of Methodology)

1. Combine URL + HTML feature vectors into one row per sample.
2. Deduplicate on `url`.
3. Impute missing HTML features with `0`/`False` for rows where scraping failed (train the model to be robust to URL-only input, since production traffic will include unreachable sites).
4. Encode `prediction` as binary (`1 = phishing`, `0 = legitimate`).
5. Balance classes with `class_weight="balanced"` (SMOTE is flag-gated off by default: `USE_SMOTE = False` in `ml/train.py`) on the training split only (never on test data).
6. 80/20 train/test split, stratified on the label.

## E. Output Contract

`extract_all(url, html=None) -> dict[str, int|float|bool]` returns all 25 keys
above (using this document's exact names), plus `html_features_available: bool`.
This dict is what gets JSON-encoded into `ScanHistory.features_json`.
