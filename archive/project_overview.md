# 📄 PhishGuard Project Overview

> **Intelligent Phishing Website Detection System Using Machine Learning, Explainable AI (SHAP), and FastAPI**

> [!NOTE]
> For the complete, detailed system documentation including architecture diagrams, API contracts, feature extraction specs, and ML benchmarks, refer to [OVERVIEW.md](file:///d:/MINI_PROJECT/PhishGuard/OVERVIEW.md).

---

## 🛡️ About the Project

**PhishGuard** is an intelligent cybersecurity web application designed to detect phishing websites in real time using structural URL analysis and HTML content characteristics. Unlike traditional blacklist-based systems that fail against zero-day phishing attacks or expensive commercial tools that rely on paid APIs, PhishGuard utilizes a custom-trained **Supervised Machine Learning Pipeline** combined with **Explainable AI (SHAP)** to deliver high-accuracy classification with human-interpretable risk breakdown.

The system features:
- **FastAPI REST API** backend serving machine learning predictions.
- **Obsidian Vault Design System** React frontend for security forensic analysis.
- **22-Feature Hybrid Vector** (15 URL structure + 7 HTML DOM features).
- **Explainable AI Engine** providing SHAP-based feature importance for every prediction.
- **Graceful System Degradation** fallback to URL-only features if target sites are offline.
- **SQLite Database** persisting scan history and model auditing metadata.

---

## 📱 Application Pages Overview

PhishGuard features **6 primary application pages**, designed for different stages of the threat analysis lifecycle:

### 1. 🏠 Overview Page (`/`)
- **Executive Summary**: System introduction, live health status indicator, and active ML model chip.
- **Quick Scan Input**: Compact URL entry field for instant analysis directly from the home view.
- **Recent Scan Card**: Highlight of the most recent scan result with quick status verdict and confidence level.

### 2. 🔍 Scan URL Workspace (`/scan`) — *Primary Core*
- **URL Input Panel**: Monospace input box with real-time format validation and submission handling.
- **EKG Scan Line Animation**: Mint pulse line animating across the panel during live analysis.
- **Verdict & Risk Score Display**: High-visibility verdict (`PHISHING DETECTED` in Coral Red or `URL IS SAFE` in Mint Green) accompanied by a 0–100 risk score meter:
  - 🟢 **0–33**: Low Risk (Safe)
  - 🟡 **34–66**: Medium Risk (Caution)
  - 🔴 **67–100**: High Risk (Danger)
- **Degradation Banner**: Displays `"Analysis based on URL structure only"` if webpage HTML could not be fetched.
- **Contributing Signal List (SHAP Evidence)**: Top 5 feature impact indicators showing exact raw values, risk contribution bars, and plain-English explanations.
- **Full 22-Feature Matrix**: Accordion expanding all 15 URL and 7 HTML extracted values.

### 3. 📜 History Page (`/history`)
- **Search & Filtering**: Search bar by URL/domain + filter pills (`All`, `Legitimate`, `Phishing`).
- **Data Table**: Tabular view displaying URL, Verdict pill badge, Risk Score, Confidence %, and Timestamp.
- **Interactive Actions**: View scan detail modal or delete entries with a confirmation overlay.
- **CSV Export**: One-click download of the complete scan history.

### 4. 📈 Analytics Page (`/analytics`)
- **Stat Metric Cards**: Total Scans, Phishing Detected Count/%, Average Confidence, and Model Accuracy.
- **Model Evaluation Matrix**: Comparison table across Logistic Regression, Random Forest, XGBoost, and SVM.
- **Visual Charts**: Static Confusion Matrix, ROC Curves, and Top Suspicious Feature Importance distribution.

### 5. ⚙️ Model & API Page (`/api-docs`)
- **Model Metadata**: Information on the active model (e.g., Random Forest), trained dataset size (572k+ URLs), and metrics.
- **API Endpoint Cards**: Documentation and trial interface for `POST /predict`, `GET /history`, `DELETE /history/{id}`, `GET /model-info`, `GET /health`.
- **Embedded Swagger UI**: Interactive iframe embedding FastAPI's `/docs` page.

### 6. 🖨️ Detailed Scan Report Page (`/report`)
- **Print/PDF Export View**: High-contrast, clean print layout formatted for generating downloadable PDF audit reports.

---

## 🏗️ System Architecture & Technology Stack

```text
User ──▶ React 18 Frontend (Obsidian Vault Theme) ──▶ FastAPI REST Backend
                                                           │
                                      ┌────────────────────┴────────────────────┐
                                      ▼                                         ▼
                         Feature Engineering (22 Features)          ML Prediction Model (Random Forest / XGBoost)
                                      │                                         │
                                      └────────────────────┬────────────────────┘
                                                           ▼
                                               Explainable AI (SHAP Engine)
                                                           │
                                                           ▼
                                                SQLite DB & JSON Response
```

| Layer | Technologies Used |
|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS, Chart.js, Lucide Icons |
| **Backend** | Python 3.11, FastAPI, Uvicorn, Pydantic |
| **Machine Learning** | Scikit-learn, XGBoost, SHAP, Pandas, NumPy |
| **Feature Extraction** | tldextract, BeautifulSoup4, Requests, urllib |
| **Database** | SQLite, SQLAlchemy ORM |

---

## 📊 Machine Learning Model Comparison

Model benchmarking evaluated across **572,182 URLs**:

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Status |
|---|---|---|---|---|---|---|
| 🌲 **Random Forest** | **89.34%** | **82.53%** | **83.71%** | **83.12%** | **0.9500** | 🏆 **Selected Active Model** |
| ⚡ **XGBoost** | 87.61% | 81.07% | 78.87% | 79.95% | 0.9365 | Candidate |
| 📈 **Logistic Regression** | 82.49% | 74.46% | 67.15% | 70.62% | 0.8659 | Baseline |
| 🎯 **SVM** | 82.40% | 74.10% | 67.36% | 70.57% | 0.8655 | Baseline |

---

## 🔗 Project Documentation Index

- 📘 [OVERVIEW.md](file:///d:/MINI_PROJECT/PhishGuard/OVERVIEW.md) — Master Comprehensive Project Guide
- 🏗️ [01 System Architecture](file:///d:/MINI_PROJECT/PhishGuard/files/01_system_architecture.md)
- 🗄️ [02 Database Schema](file:///d:/MINI_PROJECT/PhishGuard/files/02_database_schema.md)
- 🔌 [03 API Contract](file:///d:/MINI_PROJECT/PhishGuard/files/03_api_contract.md)
- 🧪 [04 Feature Engineering Spec](file:///d:/MINI_PROJECT/PhishGuard/files/04_feature_engineering_spec.md)
- 📊 [05 Model Comparison Matrix](file:///d:/MINI_PROJECT/PhishGuard/files/05_model_comparison_matrix.md)
- 🎨 [06 Frontend Component Tree](file:///d:/MINI_PROJECT/PhishGuard/files/06_frontend_component_tree.md)
- 💅 [PhishGuard UI Plan](file:///d:/MINI_PROJECT/PhishGuard/phishguard-ui-plan-INTEGRATED-v2.md)
