# 06 — Frontend Component Tree

## 1. Tree

```
App.jsx
├── ScanProvider (Context — global scan state)
├── Router
│   ├── Navbar
│   │   └── (Logo, nav links, active-route highlight)
│   │
│   ├── Route "/"  → HomePage
│   │   ├── UrlInputForm            (input + scan button, client-side validation)
│   │   ├── ScanResultCard          (shown after a scan resolves)
│   │   │   ├── ConfidenceCircle    (animated SVG ring, 0–100%)
│   │   │   ├── RiskBadge           (pill: low/medium/high, colored)
│   │   │   ├── FeatureAccordion    (expandable full 22-feature list)
│   │   │   │   └── FeatureBar × 22 (horizontal bar per feature)
│   │   │   └── ShapBarChart        (Chart.js horizontal bar — top 5 SHAP)
│   │   └── RecentScansSidebar      (last 5 scans, pulled from GET /history)
│   │
│   ├── Route "/history" → HistoryPage
│   │   ├── FilterDropdown          (All / Legitimate / Phishing)
│   │   ├── ScanTable
│   │   │   └── row → RiskBadge, DeleteButton
│   │   ├── PaginationControls
│   │   └── ExportCsvButton
│   │
│   ├── Route "/analytics" → AnalyticsPage
│   │   ├── StatCard × 4            (Total Scans, Phishing Detected, Avg Confidence, Model Accuracy)
│   │   ├── DistributionPieChart    (Legitimate vs Phishing)
│   │   ├── ScansOverTimeLineChart  (last 7 days)
│   │   └── TopSuspiciousFeaturesBarChart
│   │
│   └── Route "/api-docs" → ApiDocsPage
│       └── SwaggerEmbed (iframe → backend /docs)
│
└── Footer
```

## 2. Shared/Reusable Components (8+)

| Component | Props (key ones) | Used on |
|---|---|---|
| `ConfidenceCircle` | `value: number (0-100)` | Home |
| `RiskBadge` | `level: "low"\|"medium"\|"high"` | Home, History |
| `FeatureBar` | `label, value, direction` | Home |
| `ScanResultCard` | `result: ScanResponse` | Home |
| `Navbar` | — | all pages |
| `Footer` | — | all pages |
| `ToastNotification` | `type: "success"\|"error", message` | global |
| `LoadingSpinner` | `size` | Home, History, Analytics |

## 3. State Management

- `ScanContext` (React Context + `useReducer`) holds: `currentResult`, `recentScans`, `isLoading`, `error`.
- Page-local state (filters, pagination page number) stays local via `useState` — no need to globalize it.
- Zustand is an acceptable swap-in if the context/reducer boilerplate grows unwieldy; not required for this scope.

## 4. API Service Layer (`src/services/api.js`)

```js
// Axios instance
const api = axios.create({ baseURL: "http://localhost:8000" });

export const scanUrl        = (url) => api.post("/predict", { url });
export const getHistory     = (page, filters) => api.get("/history", { params: { page, ...filters } });
export const deleteScan     = (id) => api.delete(`/history/${id}`);
export const getModelInfo   = () => api.get("/model-info");
export const getHealth      = () => api.get("/health");
```

Response/error interceptor normalizes failures into `{ message, isDemoMode }` so
`HomePage` can fall back to a mock prediction and show a "Demo Mode" badge if the
backend is unreachable, per the Phase 3 requirement.

## 5. Responsive Behavior

- Tailwind breakpoints: stack `ScanResultCard` + `RecentScansSidebar` vertically below `md`; side-by-side at `md+`.
- `ScanTable` on History collapses to a card-per-row layout below `sm`.
- Chart components resize via Chart.js's `responsive: true` + `maintainAspectRatio: false`.
