# 05 — Model Comparison Matrix

Targets, not measured results — `ml/evaluate.py` will fill in actual numbers
after training and overwrite this table's "Actual" columns (or generate
`ml/comparison_report.json`, which the frontend Analytics page reads from).

## 1. Candidate Models

| Model | Algorithm Type | Target Accuracy | Target Precision | Target Recall | Target F1 | Target ROC-AUC | Train Speed | Inference Speed | Interpretability |
|---|---|---|---|---|---|---|---|---|---|
| Logistic Regression | Linear, baseline | ≥ 0.90 | ≥ 0.88 | ≥ 0.88 | ≥ 0.88 | ≥ 0.94 | Fastest | Fastest | High (coefficients) |
| Random Forest | Bagged trees | ≥ 0.95 | ≥ 0.94 | ≥ 0.94 | ≥ 0.94 | ≥ 0.98 | Medium | Fast | Medium (feature importance) |
| XGBoost | Gradient-boosted trees | ≥ 0.96 | ≥ 0.95 | ≥ 0.95 | ≥ 0.95 | ≥ 0.99 | Medium-slow | Fast | Medium (SHAP-friendly) |
| SVM (calibrated linear) | Max-margin | ≥ 0.93 | ≥ 0.91 | ≥ 0.90 | ≥ 0.90 | ≥ 0.96 | Slowest at this dataset size | Medium | Low |

## 2. Selection Criteria

Priority order for choosing `best_model.pkl`:

1. **F1-score** is the primary criterion — phishing detection needs balanced precision/recall (missed phishing = harm to users; false positives = broken legitimate sites).
2. **ROC-AUC** as a tie-breaker between close F1 scores.
3. **SHAP compatibility** — tree-based models (Random Forest, XGBoost) get exact, fast `TreeExplainer` support; SVM/Logistic Regression fall back to the slower `KernelExplainer`. This is a practical tie-breaker favoring tree models for the explainability requirement.
4. **Inference latency** — must comfortably serve `POST /predict` in well under 1s for a responsive UI.

**Expected outcome**: XGBoost or Random Forest wins on F1/ROC-AUC and both support `TreeExplainer`, so either is a safe default; Logistic Regression is kept in the comparison report as the interpretable baseline even if not selected as `best_model.pkl`.

## 3. What `ml/comparison_report.json` Will Contain

```json
{
  "trained_at": "2026-07-22T09:00:00Z",
  "dataset_size": 42000,
  "models": [
    {"name": "LogisticRegression", "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0},
    {"name": "RandomForest", "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0},
    {"name": "XGBoost", "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0},
    {"name": "SVM", "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "roc_auc": 0.0}
  ],
  "selected_model": "XGBoost",
  "selection_reason": "highest F1 and ROC-AUC among candidates"
}
```
(Zeros are placeholders — real numbers populate after Phase 1 training.)
