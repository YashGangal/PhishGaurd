# 02 — Database Schema

Two tables, SQLite by default (swappable for MongoDB later per tech stack notes —
schema below assumes the relational/SQLAlchemy path since that's what Phase 1 builds).

## 1. `ScanHistory`

Stores every prediction made through `POST /predict`.

```python
# app/models/database.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ScanHistory(Base):
    """A single URL scan result, persisted for the History and Analytics pages."""

    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String(2048), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)

    prediction = Column(String(20), nullable=False)        # "phishing" | "legitimate"
    confidence = Column(Float, nullable=False)              # 0.0 - 1.0
    risk_score = Column(Integer, nullable=False)            # 0 - 100
    risk_level = Column(String(10), nullable=False)         # "low" | "medium" | "high"

    features_json = Column(Text, nullable=False)            # JSON-encoded 22-feature vector
    top_features_json = Column(Text, nullable=False)        # JSON-encoded top-5 SHAP contributions

    model_version = Column(String(50), ForeignKey("model_metadata.version"), nullable=False)

    scanned_at = Column(DateTime, default=datetime.utcnow, index=True)

    model = relationship("ModelMetadata", back_populates="scans")
```

## 2. `ModelMetadata`

One row per trained model artifact; `is_active=True` marks the model currently
loaded by `prediction.py`.

```python
class ModelMetadata(Base):
    """Metadata for a trained model artifact, produced by ml/train.py."""

    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String(50), nullable=False)         # "RandomForest", "XGBoost", ...
    version = Column(String(50), unique=True, nullable=False)  # e.g. "rf_v1_2026-07-22"
    algorithm = Column(String(50), nullable=False)

    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    roc_auc = Column(Float, nullable=False)

    dataset_size = Column(Integer, nullable=False)
    file_path = Column(String(255), nullable=False)         # models/best_model.pkl
    trained_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False, index=True)
    notes = Column(Text, nullable=True)

    scans = relationship("ScanHistory", back_populates="model")
```

## 3. Indexing Rationale

| Index | Reason |
|---|---|
| `scan_history.domain` | Powers "top flagged domains" analytics query |
| `scan_history.scanned_at` | Powers "scans over last 7 days" line chart, and pagination ordering |
| `model_metadata.is_active` | Fast lookup of the currently-served model at startup |
| `model_metadata.version` (unique) | Enforces one row per trained artifact, used as FK target |

## 4. Migration Note

Phase 1 can start with `Base.metadata.create_all(engine)` on app startup (fine for
a SQLite-backed mini-project). If the project later needs real migrations, add
Alembic in a follow-up phase — out of scope for this build.
