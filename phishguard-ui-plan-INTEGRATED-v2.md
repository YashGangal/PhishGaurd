# PhishGuard UI Plan — Integrated v2.0 (FINAL)

## Intent

Design a premium, editorial-grade web interface for the **Intelligent Phishing Website Detection System**. The product must feel like a professional security forensics tool — authoritative, calm under pressure, and visually distinctive. It avoids both generic "SaaS template" aesthetics and cheap "cyberpunk" clichés (neon green on black, matrix rain, skull icons).

The target feeling: **opening a high-end security audit report** — think Bloomberg Terminal meets Apple Design, with the clarity of a medical diagnostic interface.

**Working assumptions — editable**

- Platform: responsive web application. Desktop-first for analysis workflows, fully usable on mobile.
- Visual posture: **"Obsidian Vault"** — deep, warm dark surfaces with a single disciplined accent.
- Product name: **PhishGuard**.
- Content policy: only genuine API values or clearly labelled example/empty/loading states. No fabricated metrics.

---

## Design Philosophy: "Obsidian Vault"

### Why This Aesthetic

Most student projects look identical because they use:
- Default Tailwind slate/blue palettes
- Centered hero sections with giant rounded buttons
- Generic gradient backgrounds
- Stock icons scattered without purpose

**PhishGuard avoids this by committing to a single visual language:**

> **Forensic minimalism.** Every pixel serves the analysis. Color is earned, not decorative. Space is used editorially — asymmetric, intentional, confident.

### Visual Identity

| Token | Value | Usage |
|-------|-------|-------|
| **Background** | `#08080f` | Page canvas — deep warm black, not harsh pure black |
| **Surface** | `#0f0f1a` | Cards, panels — slightly lifted, no border needed |
| **Elevated** | `#16162a` | Hover states, active inputs, modal backgrounds |
| **Border** | `#1e1e33` | 1px hairlines — structural, not decorative |
| **Border Hover** | `#2a2a45` | Subtle lift on interaction |
| **Accent** | `#00e5c0` | Primary action, safe verdict, scan pulse — mint-cyan, medical and precise |
| **Accent Dim** | `rgba(0, 229, 192, 0.08)` | Subtle glow backgrounds |
| **Danger** | `#ff5a5a` | Phishing verdict — coral red, aggressive but not clownish |
| **Danger Dim** | `rgba(255, 90, 90, 0.08)` | Danger glow backgrounds |
| **Warning** | `#f0c040` | Risk indicators — muted gold |
| **Text Primary** | `#e8eaf6` | Headings, labels — soft white with hint of lavender |
| **Text Secondary** | `#6b6b8d` | Metadata, captions — desaturated slate-purple |
| **Text Data** | `#a0a0c0` | Raw values, feature names — slightly elevated from captions |
| **Font UI** | `Inter, system-ui, sans-serif` | Navigation, buttons, body — clean and neutral |
| **Font Data** | `'JetBrains Mono', 'Fira Code', monospace` | URLs, confidence scores, feature values — technical authority |
| **Font Display** | `Inter` (weight 700–800, tight tracking) | Page titles — bold, compact, architectural |

### Shape Language

- **Main containers:** `border-radius: 0` — sharp, architectural, serious
- **Small elements (buttons, badges, inputs):** `border-radius: 6px` — just enough to feel crafted, not bubbly
- **No drop shadows on cards** — use 1px borders and subtle background elevation instead
- **Scan line:** A 1px horizontal `#00e5c0` line that animates across the result panel during analysis — like a document scanner or EKG readout

### Motion Principles

- **No continuous animations** — no floating particles, no breathing gradients, no spinning globes
- **Purposeful motion only:**
  - Input focus: border color transition 200ms
  - Result reveal: staggered fade-up (50ms delay per section)
  - Verdict badge: subtle scale pop (0.95 → 1.0, 300ms ease-out) when result arrives
  - Scan line: horizontal traverse during analysis, then dissolves
- **Respect `prefers-reduced-motion`** — disable all animations for users who request it

---

## Information Architecture

1. **Overview** — scan entry point, latest verdict, quick recent activity.
2. **Scan URL** — focused URL analysis workspace and progressive result view.
3. **History** — searchable, filterable stored scan results with row detail.
4. **Analytics** — **static** model evaluation charts (from training phase) + live counters only.
5. **Model & API** — model metadata, health status, and integration affordances.
6. **Report** — printable/downloadable scan summary (browser print-to-PDF).

**Delivery priority:**
- P0: Scan URL (core screen)
- P0: History
- P1: Overview
- P1: Model & API
- P2: Analytics (static)
- P3: Report (print view)

---

## Primary Screen: Scan Workspace

### Layout Structure (Desktop)

```
┌────────────────────────────────────────────────────────────────────┐
│  NAV (200px fixed) │  MAIN CONTENT AREA (fluid)                  │
│                    │                                             │
│  [PHISHGUARD]      │  ── HEADER ──                               │
│  ─────────────     │  Scan Analysis          [Model: Online] [●]  │
│  Overview          │                                             │
│  Scan URL    ←──active                                          │
│  History           │  ── INPUT PANEL ──                          │
│  Analytics         │  ┌─────────────────────────────────────┐   │
│  Model & API       │  │  Enter URL to analyze                │   │
│  ─────────────     │  │  [https://...                    ]   │   │
│  [Report]          │  │  Paste a URL. We'll inspect it.     │   │
│                    │  │  [      ANALYZE URL      ]           │   │
│                    │  └─────────────────────────────────────┘   │
│                    │                                             │
│                    │  ── RESULT PANEL (appears after scan) ──   │
│                    │  ┌─────────────────────────────────────┐   │
│                    │  │  [SCAN LINE ANIMATION — 1px teal]   │   │
│                    │  │                                     │   │
│                    │  │  VERDICT: PHISHING                  │   │
│                    │  │  Risk Score: 92/100                 │   │
│                    │  │  Confidence: 97.3%                  │   │
│                    │  │  Model: xgboost_v1  |  Scanned: now │   │
│                    │  │                                     │   │
│                    │  │  ── TOP SIGNALS ──                  │   │
│                    │  │  [01] No HTTPS Encryption    +82%   │   │
│                    │  │  [02] Suspicious Keywords    +64%   │   │
│                    │  │  [03] IP in Hostname         +51%   │   │
│                    │  │                                     │   │
│                    │  │  [Scan Another] [Copy Result]       │   │
│                    │  └─────────────────────────────────────┘   │
│                    │                                             │
└────────────────────────────────────────────────────────────────────┘
```

### Component Specifications

#### App Shell

- **Left nav (desktop):** 200px fixed width, `bg-[#08080f]`, right border `1px solid #1e1e33`
  - Logo: "PHISHGUARD" in `Inter 700`, `tracking-[0.2em]`, `text-[#e8eaf6]`, uppercase
  - Nav items: `text-sm`, `text-[#6b6b8d]`, hover `text-[#e8eaf6]`, active item has `border-l-2 border-[#00e5c0] pl-4` and `text-[#e8eaf6]`
  - Bottom section: "Report" button, model status chip
- **Top bar (mobile):** Hamburger menu, logo centered, status chip right

#### Header

- Page title: `text-2xl font-bold text-[#e8eaf6]` — "Scan Analysis"
- Subtitle: `text-sm text-[#6b6b8d]` — "Submit a URL for machine-learning threat assessment"
- Status badge (right-aligned):
  - Online: `bg-[#00e5c0]/10 text-[#00e5c0] border border-[#00e5c0]/20` with a 6px pulsing dot
  - Offline: `bg-[#ff5a5a]/10 text-[#ff5a5a] border border-[#ff5a5a]/20`

#### URL Input Panel

- Container: `bg-[#0f0f1a]`, `border: 1px solid #1e1e33`, `border-radius: 0` (sharp), padding 32px
- Label: "Target URL" in `text-xs uppercase tracking-wider text-[#6b6b8d] font-semibold`
- Input field:
  - `bg-[#08080f]`, `border: 1px solid #1e1e33`, `border-radius: 6px`
  - Font: `JetBrains Mono`, `text-[#e8eaf6]`
  - Placeholder: `https://example.com` in `text-[#6b6b8d]`
  - Focus: `border-color: #00e5c0`, subtle `box-shadow: 0 0 0 3px rgba(0,229,192,0.1)`
  - Validation: Inline text below input in `text-xs` — red for invalid URL, neutral for empty
- Analyze button:
  - `bg-[#00e5c0]`, `color: #08080f`, `font-weight: 700`, `border-radius: 6px`, `padding: 12px 32px`
  - Hover: `brightness(1.1)`
  - Disabled: `opacity: 0.4`, `cursor: not-allowed`
  - Loading state: Button text becomes "Analyzing..." with subtle shimmer

#### Result Panel

**Container:**
- `bg-[#0f0f1a]`, `border: 1px solid #1e1e33`
- Appears with `opacity 0 → 1`, `translateY(8px) → 0`, 400ms ease-out

**Scan Line:**
- During analysis: a 1px tall `#00e5c0` line traverses left-to-right across the panel over 2s, then fades
- CSS: `linear-gradient` mask with animated position
- **Disabled when `prefers-reduced-motion: reduce`**

**Verdict Section:**
- Large display: "PHISHING DETECTED" or "URL IS SAFE"
- Font: `Inter 800`, `text-3xl`, `tracking-tight`
- Color: `#ff5a5a` for phishing, `#00e5c0` for safe
- **Non-color cue:** Prefix with a geometric icon — octagon with X for danger, shield check for safe
- Sub-line: "Confidence: 97.3%" in `JetBrains Mono`, `text-[#a0a0c0]`

**Risk Score:**
- Displayed as a large numeric: `92` with `/100` in `text-[#6b6b8d]`
- Positioned beside the verdict, not below — asymmetric layout
- Color coding:
  - 0–33: `#00e5c0` (Safe)
  - 34–66: `#f0c040` (Caution)
  - 67–100: `#ff5a5a` (Danger)

**Metadata Row:**
- `Model: xgboost_v1 | Scanned: 2026-07-22 14:32 UTC`
- Font: `JetBrains Mono 12px`, `text-[#6b6b8d]`
- Separated by a `|` with `color: #1e1e33`
- **If `html_features_available: false`, add note:** "Analysis based on URL structure only."

**Signal List ("Evidence"):**
- Section title: "CONTRIBUTING SIGNALS" in `text-xs uppercase tracking-wider text-[#6b6b8d]`
- Each signal is a **forensic evidence row**:
  ```
  ┌────────────────────────────────────────────────────────┐
  │  [01]  No HTTPS Encryption                    +82%    │
  │  ──────────────────────────────────────────────────────│
  │  The URL does not use HTTPS. Data is transmitted      │
  │  unencrypted. Value: 0 (expected: 1)                  │
  └────────────────────────────────────────────────────────┘
  ```
  - Number badge: `bg-[#1e1e33]`, `text-[#a0a0c0]`, `font-mono`, `border-radius: 4px`, `padding: 2px 8px`
  - Label: `text-[#e8eaf6]`, `font-medium`
  - Impact bar: horizontal bar, `height: 4px`, filled proportionally to `impact_score`, color matches verdict
  - Impact percentage: `font-mono text-[#a0a0c0]`
  - Explanation: `text-sm text-[#6b6b8d]`, revealed on row hover or via expand icon

**Action Bar:**
- "Scan Another" — secondary button: `bg-transparent`, `border: 1px solid #1e1e33`, `text-[#e8eaf6]`
- "Copy Result" — icon button with tooltip
- "View Full Report" — only enabled when report is available

---

## Secondary Screens

### Overview

- **Welcome block:** Large type — "PhishGuard" display title, subline "Machine-learning threat detection for URLs."
- **Quick scan:** Compact version of the Scan URL input (no result panel)
- **Latest scan card:** If history exists, show the most recent scan as a condensed card (URL truncated, verdict badge, confidence, time ago)
- **Empty state:** "No scans yet. Submit a URL to begin." with a subtle geometric pattern (CSS-only, no images)
- **Model status:** Small panel showing `/health` status, last trained date, active model name

### History

- **Search bar:** Full-width input with search icon, placeholder "Search by URL or domain..."
- **Filters:**
  - Verdict: All / Safe / Phishing (pill buttons, active has `bg-[#1e1e33] border border-[#2a2a45]`)
  - Date range: Last 24h / 7 days / 30 days / All
  - "Clear Filters" text button
- **Desktop table:**
  - Columns: URL (truncated with `...` + copy icon), Verdict (badge), Confidence, Risk Score, Scanned At, Actions
  - Row hover: `bg-[#16162a]`
  - Verdict badges:
    - Safe: `bg-[#00e5c0]/10 text-[#00e5c0] border border-[#00e5c0]/20`
    - Phishing: `bg-[#ff5a5a]/10 text-[#ff5a5a] border border-[#ff5a5a]/20`
  - Actions: "View" (opens detail modal), "Delete" (trash icon, requires confirmation)
- **Mobile cards:** Stacked cards, each showing URL, verdict badge top-right, confidence and date below
- **Pagination:** Simple prev/next with page numbers, `font-mono`
- **Delete confirmation:** Modal overlay — "Delete this scan from history?" with "Cancel" and "Delete" (danger style)
- **URL wrapping:** Long URLs use `overflow-wrap: anywhere` and `word-break: break-all` at safe delimiters

### Analytics

**CRITICAL: This page uses STATIC assets from the training phase, not live aggregated queries.**

- **Stat cards (top row):**
  - Total Scans: live count from `/history` length
  - Model Accuracy: static value from training report (e.g., "97.2%")
  - Phishing Detected: live count from history filter
  - Avg Confidence: calculated from history data
- **Model Comparison Chart:** Static image or HTML table showing the 4-model comparison (Logistic Regression, Random Forest, XGBoost, SVM) with Accuracy, Precision, Recall, F1, ROC-AUC
- **Confusion Matrix:** Static heatmap image exported from Jupyter notebook
- **ROC Curve:** Static line chart image
- **Feature Importance:** Horizontal bar chart of top 10 features (can be live if model exposes `feature_importances_`)
- **Label clearly:** "Model Evaluation (Training Phase)"
- **Empty state:** "Train models to see evaluation charts."

### Model & API

- **Active Model Card:**
  - Name, algorithm, training date, feature count
  - Metrics grid: 5 small cards (Accuracy, Precision, Recall, F1, ROC-AUC)
  - "Retrain" button (placeholder for future)
- **API Endpoints List:**
  - `POST /predict` — with a "Try it" button that opens a small inline URL input
  - `GET /history` — description + parameters
  - `GET /model-info` — description
  - `GET /health` — description
  - Each endpoint: method badge (`POST` in `bg-[#00e5c0]/10 text-[#00e5c0]`), path in `font-mono`, description
- **Health Monitor:** Live ping to `/health` every 30s, showing response time in ms

### Report

- **Print-optimized view:** White background, black text, clean typography
- **Sections:**
  1. Header: "PhishGuard Analysis Report" + logo + generation timestamp
  2. Target URL: Full URL in monospace
  3. Verdict: Large text with color
  4. Risk Assessment: Score + level + confidence
  5. Contributing Signals: Table with rank, feature, value, impact
  6. Model Information: Name, version, training date
  7. Footer: "Generated by PhishGuard ML System"
- **Actions:** "Print" (browser print dialog), "Download as PDF" (print-to-PDF)
- **Phase 2 stretch:** Backend PDF generation if time permits

---

## Component and State Inventory

| Component | Required States |
|-----------|----------------|
| URL Analyzer | idle, typed, invalid, submitting, result, request-error |
| Verdict Display | safe, phishing, indeterminate |
| Confidence/Risk | real numeric, loading, unavailable |
| Signal List | populated, loading, empty, error |
| History Table | loading, populated, filtered-empty, error, delete-confirm |
| API Health Chip | checking, online, offline, degraded |
| Report Control | unavailable, ready, print-view |
| Scan Line | hidden, scanning, complete |

---

## Data Contract (Finalized — Aligned with API Contract v1.1)

### POST /predict

```json
{
  "url": "https://evil-bank.com/login",
  "prediction": "phishing",
  "confidence": 0.973,
  "risk_score": 92,
  "risk_level": "high",
  "html_features_available": false,
  "model_version": "xgboost_v1",
  "scanned_at": "2026-07-22T14:32:00Z",
  "features": {
    "url_length": 58,
    "num_dots": 4,
    "...": "... remaining of 22 features"
  },
  "top_features": [
    {
      "feature": "has_https",
      "label": "No HTTPS Encryption",
      "value": 0,
      "impact_score": 0.82,
      "direction": "increases_risk",
      "explanation": "The URL does not use HTTPS, making data transmission insecure and susceptible to interception."
    }
  ]
}
```

**Notes:**
- `prediction` is **binary only**: `"legitimate" | "phishing"`
- `risk_level` derived from `risk_score`: low (0–33), medium (34–66), high (67–100)
- `confidence` is 0.0–1.0, displayed as percentage
- `top_features` limited to 5 items, sorted by `impact_score` descending
- `html_features_available` indicates whether HTML features were successfully fetched

### GET /history

```json
{
  "items": [
    {
      "scan_id": 145,
      "url": "https://example.com",
      "prediction": "legitimate",
      "confidence": 0.88,
      "risk_level": "low",
      "scanned_at": "2026-07-22T12:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_items": 237,
    "total_pages": 24
  }
}
```

### GET /model-info

```json
{
  "model_name": "XGBoost",
  "version": "xgb_v1_2026-07-22",
  "accuracy": 0.972,
  "precision": 0.965,
  "recall": 0.958,
  "f1_score": 0.961,
  "roc_auc": 0.991,
  "dataset_size": 42000,
  "trained_at": "2026-07-20T09:00:00Z"
}
```

### GET /health

```json
{
  "status": "ok",
  "model_loaded": true,
  "database_connected": true
}
```

---

## Responsive Behavior

### Desktop (≥1024px)
- Fixed left nav (200px)
- Content area fluid
- Result panel: Verdict left, Risk Score right (asymmetric)
- History: Full table

### Tablet (768–1023px)
- Collapsible left nav (icon-only, 64px)
- Content area wider
- Result panel: Verdict top, Risk Score below
- History: Table with fewer columns (hide domain, show on row expand)

### Mobile (<768px)
- Top bar with hamburger menu
- Bottom sheet or overlay nav
- Result panel: Stacked vertically
- History: Card list, not table
- Input panel: Full width, button below input (not beside)
- All touch targets ≥ 44px
- Long URLs wrap safely at `.`, `/`, `-` delimiters

---

## Accessibility Requirements

- **Color is not the only indicator:** Verdicts use text + icon + shape, not just color
- **Keyboard navigation:** All interactive elements reachable via Tab, visible focus ring (`outline: 2px solid #00e5c0`)
- **Screen readers:**
  - Verdict announced as "Alert: Phishing detected" or "Status: URL is safe"
  - Signal list as a description list (`<dl>`)
  - Progress during scan: `aria-live="polite"` region
- **Reduced motion:** If `prefers-reduced-motion: reduce`, disable scan line animation and result stagger
- **URL wrapping:** Long URLs break at safe delimiters (`/`, `.`, `-`) using `overflow-wrap: anywhere` and `word-break: break-all` as fallback
- **Contrast ratios:** All text meets WCAG AA (4.5:1 for normal, 3:1 for large text)

---

## Delivery Sequence

1. Confirm API contract and product name
2. Build responsive app shell and Scan URL screen with functional input validation and result state
3. Add History with filters, persisted row detail, and deletion confirmation
4. Add Model & API, then Analytics (static only)
5. Implement report print view
6. Test keyboard flow, mobile layout, loading/error states, and representative long URLs

---

## Risks and Decisions

| Risk | Mitigation |
|------|------------|
| **"Too dark" for academic presentation** | Print/report view is white. Screenshots look premium and distinctive. |
| **Tailwind custom colors require config** | All colors defined in `tailwind.config.js` extend section. No arbitrary values scattered in JSX. |
| **Static analytics feel incomplete** | Clearly label all static charts as "Model Evaluation (Training Phase)" — academically honest. |
| **Mobile table density** | Mobile uses cards, not tables. Test with real long URLs. |
| **Report PDF generation** | Phase 1: browser print-to-PDF. Phase 2: backend PDF generation if time permits. |
| **HTML scraping failures** | `html_features_available` flag lets frontend communicate partial analysis transparently. |

---

## Acceptance Criteria

- [ ] User can submit a valid URL, see a loading state with scan line animation, and receive a clear binary verdict
- [ ] Verdict uses text + icon + color (not color alone)
- [ ] Every result shows confidence percentage, risk score (0–100), and at least 3 contributing signals
- [ ] Invalid URLs show inline validation error without page reload
- [ ] API failure shows retry option, never a fabricated result
- [ ] History supports search, verdict filter, date filter, pagination, and deletion with confirmation
- [ ] Mobile layout is usable with 44px+ touch targets and card-based history
- [ ] Analytics page clearly distinguishes live counters from static training evaluation charts
- [ ] All animations respect `prefers-reduced-motion`
- [ ] No generic gradient backgrounds, no stock illustrations, no neon cyberpunk clichés
- [ ] `html_features_available` is communicated to the user when false

---

## Next Step

Reply with **"build from phishing-detection-ui-plan.md"** (and any edits) to generate the first high-fidelity responsive prototype.
