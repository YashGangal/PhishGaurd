"""Shared API test fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.database import Base, get_db
from app.services import prediction as prediction_service
from app.services import blocklist as blocklist_service
from app.core.config import get_settings

# StaticPool keeps a single shared connection so the in-memory SQLite
# database is visible to every thread the TestClient uses.
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Pin the heuristic bundle so tests never load the multi-GB trained artifact
# and never depend on a stale/hand-patched environment.
prediction_service._cached_bundle = prediction_service._default_bundle()


def _override_get_db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create and drop tables for each test using in-memory SQLite."""

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def isolate_blocklist(monkeypatch):
    """Keep tests hermetic: no test reads the real 13k-row snapshot by default."""

    monkeypatch.setattr(get_settings(), "blocklist_enabled", False)
    blocklist_service.clear_cache()
    yield
    blocklist_service.clear_cache()


@pytest.fixture()
def client():
    """Provide a TestClient with clean tables for each test."""

    with TestClient(app) as test_client:
        yield test_client
