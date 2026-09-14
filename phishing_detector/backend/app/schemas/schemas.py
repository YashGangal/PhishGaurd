"""Pydantic request and response models for the public API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

PredictionLabel = Literal["phishing", "legitimate"]
RiskLevel = Literal["low", "medium", "high"]


class PredictRequest(BaseModel):
    """Request body for URL prediction."""

    url: HttpUrl


class TopFeature(BaseModel):
    """A feature contribution returned by the explainability service."""

    name: str
    value: int | float | bool
    impact_score: float
    direction: Literal["increases_risk", "decreases_risk"]


class PredictResponse(BaseModel):
    """Full prediction response persisted by the API."""

    model_config = ConfigDict(protected_namespaces=())

    scan_id: int
    url: str
    domain: str
    prediction: PredictionLabel
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    html_features_available: bool
    model_version: str
    features: dict[str, int | float | bool]
    top_features: list[TopFeature]
    scanned_at: datetime


class HistoryItem(BaseModel):
    """Compact scan result for a paginated history response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, protected_namespaces=())

    scan_id: int = Field(validation_alias="id", serialization_alias="scan_id")
    url: str
    prediction: PredictionLabel
    confidence: float
    risk_level: RiskLevel
    scanned_at: datetime


class Pagination(BaseModel):
    """Pagination metadata."""

    page: int
    per_page: int
    total_items: int
    total_pages: int


class HistoryResponse(BaseModel):
    """Paginated history response."""

    items: list[HistoryItem]
    pagination: Pagination


class ModelInfoResponse(BaseModel):
    """Active model metadata."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    version: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    dataset_size: int
    trained_at: datetime


class HealthResponse(BaseModel):
    """Liveness/readiness response."""

    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok", "degraded"]
    model_loaded: bool
    database_connected: bool
