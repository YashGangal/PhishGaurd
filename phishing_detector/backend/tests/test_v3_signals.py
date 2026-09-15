"""Next-retrain signal tests (free-host list, RDAP client, train flag)."""

import io
import json

import pandas as pd

import ml.train as train_module
from ml.train import load_dataset
from ml.rdap import RDAPClient
from ml.v3_signals import AGE_UNKNOWN, EXTRA_FEATURE_NAMES, extract_extra, on_free_host
from app.services.explainability import FEATURE_NAMES


def test_on_free_host():
    """User content on free hosts flags; apexes and normal sites do not."""

    assert on_free_host("https://shopeejkt4782.blogspot.com/") is True
    assert on_free_host("https://user.github.io/login") is True
    assert on_free_host("https://wordpress-214953-0.cloudclusters.net/x") is True
    assert on_free_host("https://weebly.com/") is False
    assert on_free_host("https://github.io/") is False
    assert on_free_host("https://github.com/login") is False
    assert on_free_host("https://teamyk.com/") is False
    assert on_free_host("") is False
    assert on_free_host(None) is False


def test_extract_extra_defaults_without_client():
    """Without an RDAP client the age sentinel marks unknown, never crashes."""

    result = extract_extra("https://shopeejkt4782.blogspot.com/")
    assert result == {"on_free_host": True, "domain_age_days": AGE_UNKNOWN}
    assert extract_extra("https://github.com/login")["domain_age_days"] == AGE_UNKNOWN


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _rdap_fake(monkeypatch, calls):
    def fake_open(request, timeout=None):
        calls.append(request.full_url)
        if "data.iana.org" in request.full_url:
            return _FakeResponse({"services": [[["com"], ["https://rdap.verisign.com/com/v1/"]]]})
        return _FakeResponse({"events": [{"eventAction": "registration", "eventDate": "2000-01-01T00:00:00Z"}]})
    monkeypatch.setattr("urllib.request.urlopen", fake_open)


def test_rdap_client_resolves_and_caches(tmp_path, monkeypatch):
    """Registration events become ages; repeat reads hit the disk cache."""

    calls: list[str] = []
    _rdap_fake(monkeypatch, calls)
    client = RDAPClient(cache_path=tmp_path / "cache.json", min_interval=0)
    age = client.domain_age_days("example.com")
    assert isinstance(age, int) and age > 9000
    queried = [url for url in calls if "example.com" in url]
    assert queried and queried[0].rstrip("/").endswith("/domain/example.com")
    before = len(calls)
    assert client.domain_age_days("EXAMPLE.com ") == age
    assert len(calls) == before
    assert (tmp_path / "cache.json").exists()


def test_rdap_client_fail_open(tmp_path, monkeypatch):
    """Network/parse/empty failures yield None, never raise."""

    def boom(request, timeout=None):
        raise OSError("down")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    client = RDAPClient(cache_path=tmp_path / "cache.json", min_interval=0)
    assert client.domain_age_days("example.com") is None
    assert client.domain_age_days("") is None
    assert client.domain_age_days("nodot") is None
    assert client.domain_age_days(None) is None


def _tiny_csv(path):
    frame = pd.DataFrame({
        "url": ["https://github.com/", "https://shopeejkt4782.blogspot.com/",
                "https://example.com/", "http://paypal-secure-login-confirm.tk/verify"],
        "label": [0, 1, 0, 1],
    })
    frame.to_csv(path, index=False)
    return path


def test_flag_off_matrix_unchanged(tmp_path):
    """Default training path is bit-identical (25 serving columns)."""

    features, labels = load_dataset(_tiny_csv(tmp_path / "tiny.csv"))
    assert list(features.columns) == FEATURE_NAMES
    assert len(features) == 4 + 54
    assert set(labels.unique()) == {0, 1}


def test_flag_on_adds_extra_columns(tmp_path, monkeypatch):
    """Opt-in v3 matrix appends the two candidate columns in row order."""

    monkeypatch.setattr(train_module, "USE_V3_SIGNALS", True)
    features, _ = load_dataset(_tiny_csv(tmp_path / "tiny.csv"))
    assert list(features.columns) == FEATURE_NAMES + EXTRA_FEATURE_NAMES
    assert features["on_free_host"].tolist()[:4] == [False, True, False, False]
    assert (features["domain_age_days"] == AGE_UNKNOWN).all()
