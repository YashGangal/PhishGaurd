"""SQLite engine, SQLAlchemy models, and request-scoped sessions."""

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.core.config import get_settings

Base = declarative_base()


class ModelMetadata(Base):
    """Metadata for a trained or fallback model artifact."""

    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String(50), nullable=False)
    version = Column(String(50), unique=True, nullable=False)
    algorithm = Column(String(50), nullable=False)
    accuracy = Column(Float, nullable=False, default=0.0)
    precision = Column(Float, nullable=False, default=0.0)
    recall = Column(Float, nullable=False, default=0.0)
    f1_score = Column(Float, nullable=False, default=0.0)
    roc_auc = Column(Float, nullable=False, default=0.0)
    dataset_size = Column(Integer, nullable=False, default=0)
    file_path = Column(String(255), nullable=False)
    trained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    is_active = Column(Boolean, default=False, index=True, nullable=False)
    notes = Column(Text, nullable=True)

    scans = relationship("ScanHistory", back_populates="model")


class ScanHistory(Base):
    """A URL scan result persisted for the History page."""

    __tablename__ = "scan_history"
    __table_args__ = (
        CheckConstraint("prediction IN ('phishing', 'legitimate')", name="ck_prediction"),
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="ck_risk_level"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String(2048), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    prediction = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(10), nullable=False)
    features_json = Column(Text, nullable=False)
    top_features_json = Column(Text, nullable=False)
    model_version = Column(String(50), ForeignKey("model_metadata.version"), nullable=False)
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True, nullable=False)
    needs_review = Column(Boolean, default=False, nullable=False)
    blocklist_hit = Column(Boolean, default=False, nullable=False)
    blocklist_source = Column(String(64), nullable=True)

    model = relationship("ModelMetadata", back_populates="scans")


def _create_engine():
    """Create a SQLite-compatible SQLAlchemy engine from settings."""

    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    eng = create_engine(url, connect_args=connect_args, future=True)

    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()

    return eng


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Create all Phase 1 tables if they do not already exist."""

    Base.metadata.create_all(bind=engine)
    _migrate_scan_history()


def _migrate_scan_history() -> None:
    """Add newer scan_history columns to databases created before them.

    create_all() never alters existing tables, so long-lived SQLite files
    would otherwise break on insert (no such column). Each ALTER is guarded
    by PRAGMA inspection, making startup idempotent on old and new files.
    """

    from sqlalchemy import inspect as sa_inspect, text as sa_text

    if not get_settings().database_url.startswith("sqlite"):
        return
    existing = {column["name"] for column in sa_inspect(engine).get_columns("scan_history")}
    wanted = {
        "needs_review": "BOOLEAN DEFAULT 0 NOT NULL",
        "blocklist_hit": "BOOLEAN DEFAULT 0 NOT NULL",
        "blocklist_source": "VARCHAR(64)",
    }
    with engine.begin() as connection:
        for name, ddl in wanted.items():
            if name not in existing:
                connection.execute(sa_text(f"ALTER TABLE scan_history ADD COLUMN {name} {ddl}"))


def get_db() -> Generator:
    """Yield a database session and close it after the request."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
