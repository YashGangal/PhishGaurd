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


def get_db() -> Generator:
    """Yield a database session and close it after the request."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
