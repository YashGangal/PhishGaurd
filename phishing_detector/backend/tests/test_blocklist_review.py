"""Feed blocklist, review band, and threshold tests."""

import csv

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.services import blocklist as blocklist_module
from app.services.blocklist import Blocklist, normalize_url
from app.services.prediction import apply_feed_match, in_review_band, predict
from app.services.feature_engineering import extract_all


def test_normalize_url():
    """Feed rows and scanned URLs normalize identically."""

    assert normalize_url("HTTP://Example.COM/Path/?a=1#frag") == "http://example.com/Path?a=1"
    assert normalize_url("https://example.com:443/x/") == "https://example.com/x"
    assert normalize_url("http://example.com:8080/x") == "http://example.com:8080/x"
    assert normalize_url("  https://example.com  ") == "https://example.com"
    assert normalize_url("") is None
    assert normalize_url("# comment") is None
    assert normalize_url(None) is None
    assert normalize_url("ftp://example.com/x") is None
    assert normalize_url("not a url") is None


def test_blocklist_exact_match_only(tmp_path):
    """Matching is verbatim (plus normalization), never domain-wide."""

    feed = tmp_path / "feed.csv"
    with feed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["url", "source", "added_on"])
        writer.writeheader()
        writer.writerow({"url": "http://evil.example/phish?k=1", "source": "unit", "added_on": "2026-09-15"})
    matcher = Blocklist(feed)
    assert matcher.available is True
    assert matcher.check("http://evil.example/phish?k=1").source == "unit"
    assert matcher.check("HTTP://EVIL.EXAMPLE/phish?k=1#x") is not None
    assert matcher.check("http://evil.example/phish?k=2") is None
    assert matcher.check("http://evil.example/other") is None
    assert matcher.check("http://sub.evil.example/phish?k=1") is None


def test_blocklist_missing_file_is_fail_open(tmp_path):
    """An absent snapshot disables matching instead of crashing."""

    matcher = Blocklist(tmp_path / "nope.csv")
    assert matcher.available is False
    assert matcher.check("http://evil.example/phish") is None
    assert Blocklist(None).check("http://evil.example/phish") is None


def test_feed_hit_overrides_legit_verdict(client, tmp_path, monkeypatch):
    """A feed-listed URL is convicted even when the model votes legitimate."""

    feed = tmp_path / "feed.csv"
    with feed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["url", "source", "added_on"])
        writer.writeheader()
        writer.writerow({"url": "https://example.com/", "source": "unit-feed", "added_on": "2026-09-15"})
    settings = get_settings()
    monkeypatch.setattr(settings, "blocklist_path", feed)
    monkeypatch.setattr(settings, "blocklist_enabled", True)
    blocklist_module.clear_cache()
    try:
        # Control: without the feed this URL is heuristic-legitimate (p=0.22).
        assert predict(extract_all("https://example.com/")).prediction == "legitimate"
        response = client.post("/predict", json={"url": "https://example.com/"})
        assert response.status_code == 200
        body = response.json()
        assert body["prediction"] == "phishing"
        assert body["confidence"] == 1.0
        assert body["risk_score"] == 100
        assert body["blocklist_hit"] is True
        assert body["blocklist_source"] == "unit-feed"
        assert body["needs_review"] is False
        assert len(body["top_features"]) == 5
        history = client.get("/history")
        flagged = [item for item in history.json()["items"] if item["url"] == "https://example.com/"]
        assert flagged and flagged[0]["blocklist_hit"] is True
    finally:
        blocklist_module.clear_cache()


def test_review_band_boundaries():
    """The advisory band is inclusive on both ends."""

    assert in_review_band(0.3999) is False
    assert in_review_band(0.4) is True
    assert in_review_band(0.5) is True
    assert in_review_band(0.6) is True
    assert in_review_band(0.6001) is False


def test_review_band_never_changes_verdict():
    """Band membership is advisory metadata, not a third verdict."""

    values = extract_all("https://login.secure-example.xyz/path-123?a=1&b=2")
    result = predict(values)
    assert result.prediction == "phishing"
    assert result.needs_review is True


def test_decision_threshold_moves_operating_point(client, monkeypatch):
    """A higher threshold converts the same borderline URL to legitimate."""

    url = "https://login.secure-example.xyz/path-123?a=1&b=2"
    assert client.post("/predict", json={"url": url}).json()["prediction"] == "phishing"
    monkeypatch.setattr(get_settings(), "decision_threshold", 0.9)
    body = client.post("/predict", json={"url": url}).json()
    assert body["prediction"] == "legitimate"
    assert body["decision_threshold"] == 0.9


def test_settings_reject_nonsense_operating_points():
    """Invalid thresholds/bands fail at config load, not at predict time."""

    with pytest.raises(ValidationError):
        Settings(decision_threshold=1.0)
    with pytest.raises(ValidationError):
        Settings(decision_threshold=0.0)
    with pytest.raises(ValidationError):
        Settings(review_band_low=0.7, review_band_high=0.6)


def test_model_info_reports_threshold(client):
    """Operators can see the active operating point."""

    assert client.get("/model-info").json()["decision_threshold"] == 0.5


def test_apply_feed_match_keeps_explanation():
    """Feed overrides keep the SHAP evidence for analysts."""

    values = extract_all("https://example.com/")
    forced = apply_feed_match(predict(values))
    assert forced.prediction == "phishing"
    assert forced.risk_score == 100
    assert len(forced.top_features) == 5


def test_legacy_database_migrates_new_columns(tmp_path, monkeypatch):
    """A pre-v3 SQLite file gains the new columns on startup, loss-free."""

    import sqlalchemy as sa

    legacy = tmp_path / "legacy.db"
    old_engine = sa.create_engine(f"sqlite:///{legacy}")
    with old_engine.begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE scan_history (id INTEGER PRIMARY KEY, url VARCHAR(2048) NOT NULL, "
            "domain VARCHAR(255) NOT NULL, prediction VARCHAR(20) NOT NULL, confidence FLOAT NOT NULL, "
            "risk_score INTEGER NOT NULL, risk_level VARCHAR(10) NOT NULL, features_json TEXT NOT NULL, "
            "top_features_json TEXT NOT NULL, model_version VARCHAR(50) NOT NULL, "
            "scanned_at DATETIME NOT NULL)"
        ))
        connection.execute(sa.text(
            "CREATE TABLE model_metadata (id INTEGER PRIMARY KEY, model_name VARCHAR(50) NOT NULL, "
            "version VARCHAR(50) NOT NULL, algorithm VARCHAR(50) NOT NULL)"
        ))
        connection.execute(sa.text(
            "INSERT INTO scan_history (url, domain, prediction, confidence, risk_score, risk_level, "
            "features_json, top_features_json, model_version, scanned_at) VALUES "
            "('https://example.com/', 'example.com', 'legitimate', 0.8, 20, 'low', '{}', '[]', 'v1', '2026-01-01')"
        ))
    old_engine.dispose()

    import app.models.database as database_module

    fresh_engine = sa.create_engine(f"sqlite:///{legacy}")
    monkeypatch.setattr(database_module, "engine", fresh_engine)
    try:
        database_module.init_db()
        columns = {column["name"] for column in sa.inspect(fresh_engine).get_columns("scan_history")}
        assert {"needs_review", "blocklist_hit", "blocklist_source"} <= columns
        session_factory = sa.orm.sessionmaker(bind=fresh_engine)
        session = session_factory()
        try:
            row = session.execute(sa.text("SELECT url, needs_review, blocklist_hit FROM scan_history")).one()
            assert row[0] == "https://example.com/"
            assert row[1] in (0, False) and row[2] in (0, False)
        finally:
            session.close()
        # Second startup is a no-op (idempotent).
        database_module.init_db()
    finally:
        fresh_engine.dispose()
