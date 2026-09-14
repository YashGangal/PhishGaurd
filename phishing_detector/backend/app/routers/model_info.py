"""Health and active-model metadata endpoints."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.schemas import HealthResponse, ModelInfoResponse
from app.services.prediction import load_bundle, model_metadata

router = APIRouter(tags=["system"])

logger = logging.getLogger(__name__)


@router.get("/model-info", response_model=ModelInfoResponse)
def get_model_info() -> ModelInfoResponse:
    """Return metadata for the model currently serving predictions."""

    return ModelInfoResponse(**model_metadata())


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """Return liveness and model/database readiness state."""

    database_connected = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("health_database_probe_failed", exc_info=exc)
        database_connected = False
    model_loaded = True
    try:
        load_bundle()
    except Exception as exc:
        logger.warning("health_model_probe_failed", exc_info=exc)
        model_loaded = False
    return HealthResponse(status="ok" if database_connected and model_loaded else "degraded", model_loaded=model_loaded, database_connected=database_connected)
