"""Contract tests for the Phase 1 API."""

def test_health(client):
    """Health reports both database and fallback model readiness."""

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database_connected"] is True


def test_predict_and_history(client):
    """A valid URL is classified, persisted, and returned in history."""

    response = client.post("/predict", json={"url": "https://secure-login.example.xyz/verify"})
    assert response.status_code == 200
    body = response.json()
    assert body["scan_id"] > 0
    assert len(body["features"]) == 23
    assert len(body["top_features"]) == 5
    history = client.get("/history")
    assert history.status_code == 200
    assert history.json()["pagination"]["total_items"] == 1


def test_invalid_url_is_rejected(client):
    """Pydantic rejects missing schemes and malformed URL inputs."""

    response = client.post("/predict", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_delete_missing_scan(client):
    """Deleting an unknown scan returns 404."""

    assert client.delete("/history/99999").status_code == 404
