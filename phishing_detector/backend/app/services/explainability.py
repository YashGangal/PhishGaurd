"""Model explanation helpers with SHAP and deterministic fallback support."""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "url_length", "domain_length", "num_dots", "num_hyphens", "num_digits", "num_subdomains",
    "has_https", "has_ip_address", "has_at_symbol", "has_double_slash_redirect", "is_shortened_url",
    "num_suspicious_chars", "url_entropy", "has_suspicious_tld", "path_length", "has_iframe",
    "redirect_count", "num_external_links", "form_action_suspicious", "has_javascript_events",
    "has_popup_window", "has_hidden_elements",
    # Appended for v2 (never renumber above): reputation + keyword signals.
    "domain_in_top_list", "has_auth_keyword", "keyword_domain_mismatch",
]

# Fallback weights for features SHAP cannot score; v2 additions included so the
# deterministic path covers the full vector.
_FALLBACK_EXTRA_WEIGHTS = {
    "domain_in_top_list": -0.20,
    "has_auth_keyword": 0.10,
    "keyword_domain_mismatch": 0.28,
}


def _tree_base(model: Any) -> Any | None:
    """Unwrap to a tree model for fast exact SHAP (incl. calibrated wrappers)."""

    if hasattr(model, "feature_importances_"):
        return model
    for calibrated in getattr(model, "calibrated_classifiers_", []) or []:
        inner = getattr(calibrated, "estimator", getattr(calibrated, "base_estimator", None))
        if inner is not None and hasattr(inner, "feature_importances_"):
            return inner
    return None


def _fallback_impacts(values: dict[str, int | float | bool]) -> dict[str, float]:
    """Estimate signed feature contributions when SHAP is unavailable."""

    weights = {
        "url_length": 0.004, "domain_length": 0.02, "num_dots": 0.06, "num_hyphens": 0.04, "num_digits": 0.025,
        "num_subdomains": 0.08, "has_https": -0.12, "has_ip_address": 0.25, "has_at_symbol": 0.22,
        "has_double_slash_redirect": 0.2, "is_shortened_url": 0.12, "num_suspicious_chars": 0.08,
        "url_entropy": 0.035, "has_suspicious_tld": 0.15, "path_length": 0.012, "has_iframe": 0.12,
        "redirect_count": 0.08, "num_external_links": 0.01, "form_action_suspicious": 0.18,
        "has_javascript_events": 0.1, "has_popup_window": 0.14, "has_hidden_elements": 0.1,
        **_FALLBACK_EXTRA_WEIGHTS,
    }
    return {name: float(values.get(name, 0)) * weight for name, weight in weights.items()}


def top_features(model: Any, values: dict[str, int | float | bool]) -> list[dict[str, Any]]:
    """Return the five largest absolute feature contributions."""

    impacts = _fallback_impacts(values)
    try:
        import shap

        vector = np.array([[float(bool(values[name])) if isinstance(values[name], bool) else float(values[name]) for name in FEATURE_NAMES]])
        base = _tree_base(model)
        if base is not None:
            explainer = shap.TreeExplainer(base)
        else:
            explainer = shap.KernelExplainer(model.predict_proba, np.zeros((1, len(FEATURE_NAMES))))
        raw = explainer.shap_values(vector, l1_reg="num_features(10)")
        if isinstance(raw, list):
            raw = raw[-1]
        shap_values = np.asarray(raw).reshape(-1)
        impacts = {name: float(value) for name, value in zip(FEATURE_NAMES, shap_values)}
    except ImportError:
        logger.debug("shap_not_installed")
    except Exception:
        logger.debug("shap_computation_failed", exc_info=True)

    ordered = sorted(impacts.items(), key=lambda item: abs(item[1]), reverse=True)[:5]
    return [
        {
            "name": name,
            "value": values.get(name, 0),
            "impact_score": round(abs(impact), 4),
            "direction": "increases_risk" if impact >= 0 else "decreases_risk",
        }
        for name, impact in ordered
    ]
