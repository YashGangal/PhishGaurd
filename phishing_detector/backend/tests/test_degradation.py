"""Degradation-path and explainer-fallback tests (URL-only operation)."""

from app.services.explainability import FEATURE_NAMES, top_features
from app.services.feature_engineering import extract_all
from app.services.prediction import load_bundle, model_metadata


def test_predict_url_only_fallback(client):
    """With HTML scraping disabled, /predict degrades to URL-only features."""

    response = client.post("/predict", json={"url": "https://secure-login.example.xyz/verify"})
    assert response.status_code == 200
    body = response.json()
    assert body["html_features_available"] is False
    assert len(body["features"]) == 26
    assert len(body["top_features"]) == 5
    for item in body["top_features"]:
        assert item["name"] in FEATURE_NAMES
        assert item["direction"] in ("increases_risk", "decreases_risk")


def test_shap_fallback_top_features():
    """The deterministic fallback explains without SHAP and covers all features."""

    # object() has no predict_proba, so top_features deterministically takes
    # the fallback path (no SHAP sampling overhead, no version fragility).
    values = extract_all("http://192.168.0.1/login?user=test")
    impacts = top_features(object(), values)
    assert len(impacts) == 5
    names = {item["name"] for item in impacts}
    assert names <= set(FEATURE_NAMES)
    # domain_length must be explainable (regression: it was missing weights).
    all_names = {item["name"] for item in top_features(object(), {"domain_length": 60})}
    assert "domain_length" in all_names


def test_heuristic_metadata_reports_no_trained_scores():
    """Fallback metadata must not attribute trained-model scores to itself."""

    bundle = load_bundle()
    assert bundle.loaded_from_artifact is False
    info = model_metadata()
    assert info["model_name"] == "HeuristicFallback"
    assert info["accuracy"] == 0.0
    assert info["dataset_size"] == 0


def test_health_reports_degraded_or_ok_shape(client):
    """Health exposes the documented status/model/database shape."""

    body = client.get("/health").json()
    assert body["status"] in ("ok", "degraded")
    assert isinstance(body["model_loaded"], bool)
    assert body["database_connected"] is True
