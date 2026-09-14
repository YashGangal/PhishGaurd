"""Reusable model evaluation helpers."""

from typing import Any

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


def evaluate_model(model: Any, x_test: Any, y_test: Any) -> dict[str, float]:
    """Calculate the five metrics required by the project contract."""

    predicted = model.predict(x_test)
    probabilities = model.predict_proba(x_test)[:, 1] if hasattr(model, "predict_proba") else model.decision_function(x_test)
    try:
        roc_auc = float(roc_auc_score(y_test, probabilities))
    except ValueError:
        # Single-class test split (or constant scores): ROC-AUC is undefined.
        roc_auc = 0.5
    return {
        "accuracy": float(accuracy_score(y_test, predicted)),
        "precision": float(precision_score(y_test, predicted, zero_division=0)),
        "recall": float(recall_score(y_test, predicted, zero_division=0)),
        "f1_score": float(f1_score(y_test, predicted, zero_division=0)),
        "roc_auc": roc_auc,
    }
