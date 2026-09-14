"""URL prediction endpoint."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.database import ModelMetadata, ScanHistory, get_db
from app.schemas.schemas import PredictRequest, PredictResponse
from app.services.feature_engineering import extract_all
from app.services.prediction import model_metadata, predict
from app.services.scraper import fetch_page

router = APIRouter(tags=["prediction"])

logger = logging.getLogger(__name__)


def _domain(url: str) -> str:
    """Return a safe hostname for persistence and response shaping."""

    return (urlparse(url).hostname or "").lower()


def _ensure_model_metadata(db: Session) -> ModelMetadata:
    """Create or reuse the metadata row for the currently active model."""

    info = model_metadata()
    row = db.query(ModelMetadata).filter(ModelMetadata.version == info["version"]).first()
    if row is None:
        db.query(ModelMetadata).filter(ModelMetadata.is_active.is_(True)).update({"is_active": False})
        model_path = get_settings().model_path
        candidate = model_path if model_path.is_absolute() else Path(__file__).resolve().parents[2] / model_path
        row = ModelMetadata(
            model_name=info["model_name"], version=info["version"], algorithm=info["algorithm"],
            accuracy=info["accuracy"], precision=info["precision"], recall=info["recall"],
            f1_score=info["f1_score"], roc_auc=info["roc_auc"], dataset_size=info["dataset_size"],
            file_path=str(candidate), trained_at=info["trained_at"], is_active=True,
            notes="Offline heuristic fallback" if info["version"].startswith("heuristic") else None,
        )
        db.add(row)
        db.flush()
    return row


@router.post("/predict", response_model=PredictResponse)
def predict_url(payload: PredictRequest, db: Session = Depends(get_db)) -> PredictResponse:
    """Extract URL features, classify the URL, explain the result, and persist it."""

    url = str(payload.url)
    try:
        scrape = fetch_page(url, get_settings().scraper_timeout_seconds) if get_settings().enable_html_scraping else None
        features = extract_all(url, scrape.html if scrape else None, scrape.redirect_count if scrape else 0)
        result = predict(features)
        metadata = _ensure_model_metadata(db)
        scanned_at = datetime.now(timezone.utc)
        row = ScanHistory(
            url=url, domain=_domain(url), prediction=result.prediction, confidence=result.confidence,
            risk_score=result.risk_score, risk_level=result.risk_level,
            features_json=json.dumps(features), top_features_json=json.dumps(result.top_features),
            model_version=metadata.version, scanned_at=scanned_at.replace(tzinfo=None),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    except FileNotFoundError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model artifact not available")
    except Exception as exc:
        db.rollback()
        logger.exception("prediction_failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prediction failed") from exc

    return PredictResponse(
        scan_id=row.id, url=row.url, domain=row.domain, prediction=row.prediction,
        confidence=row.confidence, risk_score=row.risk_score, risk_level=row.risk_level,
        html_features_available=bool(features["html_features_available"]), model_version=row.model_version,
        features=features, top_features=result.top_features, scanned_at=scanned_at,
    )
