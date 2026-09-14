# PhishGuard Scenario Document and Problem Statement

## Problem Statement

Phishing websites imitate trusted services to collect credentials, payment information, or other sensitive data. Static blacklists can lag behind short-lived or newly generated domains. Paid reputation services can reduce implementation effort, but they introduce cost, network dependence, rate limits, and limited transparency into why a URL was flagged.

PhishGuard addresses this gap with a self-contained, explainable workflow that evaluates URL structure and optional webpage characteristics, returns a phishing or legitimate assessment, shows risk and evidence, and stores an auditable scan record. The workflow remains useful when the target site is offline, blocked, or too slow to fetch.

## Primary Scenario

1. A user opens the Overview or Scan URL workspace and enters an absolute HTTP(S) URL.
2. The frontend validates the input and sends `POST /predict`.
3. FastAPI validates the request, attempts a bounded page fetch, extracts 15 URL features and 7 optional HTML features, and records whether HTML enrichment was available.
4. The active Random Forest model or configured heuristic fallback returns a probability.
5. PhishGuard maps the probability to a prediction, confidence, 0-100 risk score, and low/medium/high risk tier.
6. SHAP or the deterministic fallback ranks the top five contributing signals.
7. The scan is persisted in SQLite and the frontend renders the verdict, evidence, full feature matrix, and degradation note if needed.

## Exception Scenarios

| Condition | Expected behavior |
|---|---|
| Invalid URL | HTTP 422; no history row is created. |
| Target unavailable | URL-only analysis continues; `html_features_available=false`. |
| Model unavailable | Use the fallback when enabled, otherwise HTTP 503. |
| Unknown history id | HTTP 404. |

## Included Diagrams

- `PhishGuard_Use_Case_Diagram.png`
- `PhishGuard_Activity_Diagram.png`
- `PhishGuard_Flow_Chart.png`

The complete requirements specification, diagrams, data dictionary, API summary, acceptance criteria, risks, constraints, and future work are in `PhishGuard_SRS.docx`.
