"""Model loading, inference, confidence, and risk-score generation."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import pickle
import threading
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.services.explainability import FEATURE_NAMES, top_features

logger = logging.getLogger(__name__)

_cached_bundle: "ModelBundle | None" = None
_bundle_lock = threading.Lock()


class HeuristicModel:
    """Offline fallback classifier used before a trained artifact is produced."""

    def predict_proba(self, matrix) -> np.ndarray:
        """Return deterministic probabilities from suspicious URL signals."""

        matrix = np.asarray(matrix)
        scores = []
        for row in matrix:
            score = float(row[0]) * 0.004 + float(row[2]) * 0.06 + float(row[5]) * 0.08
            score += float(row[7]) * 0.25 + float(row[8]) * 0.22 + float(row[9]) * 0.2
            score += float(row[10]) * 0.12 + float(row[11]) * 0.08 + float(row[13]) * 0.15
            score += float(row[18]) * 0.18 + float(row[20]) * 0.14 + float(row[21]) * 0.1
            score -= float(row[6]) * 0.12
            phishing = 1.0 / (1.0 + np.exp(-(score - 0.55) * 2.4))
            scores.append([1.0 - phishing, phishing])
        return np.asarray(scores)


@dataclass(frozen=True)
class ModelBundle:
    """Loaded model and metadata used by prediction requests."""

    model: Any
    version: str
    metadata: dict[str, Any]
    loaded_from_artifact: bool


def _default_bundle() -> ModelBundle:
    """Build the safe offline fallback model bundle."""

    return ModelBundle(
        model=HeuristicModel(),
        version="heuristic_fallback_v1",
        metadata={"model_name": "HeuristicFallback", "algorithm": "deterministic-rules", "dataset_size": 0},
        loaded_from_artifact=False,
    )


def load_bundle() -> ModelBundle:
    """Load the trained pickle bundle with caching."""

    global _cached_bundle
    if _cached_bundle is not None:
        return _cached_bundle

    with _bundle_lock:
        if _cached_bundle is not None:
            return _cached_bundle

        path = get_settings().model_path
        candidate = path if path.is_absolute() else Path(__file__).resolve().parents[2] / path
        if not candidate.exists():
            if get_settings().allow_heuristic_fallback:
                logger.warning("model_artifact_missing", extra={"path": str(candidate)})
                _cached_bundle = _default_bundle()
                return _cached_bundle
            raise FileNotFoundError("Model artifact not available")

        try:
            with candidate.open("rb") as handle:
                artifact = pickle.load(handle)
            if isinstance(artifact, dict):
                model = artifact["model"]
                version = artifact.get("version", "trained_v1")
                metadata = artifact.get("metadata", {})
            else:
                model, version, metadata = artifact, "trained_v1", {}
            if not hasattr(model, "predict_proba"):
                raise ValueError("Model artifact has no predict_proba")
        except (OSError, pickle.UnpicklingError, EOFError, ValueError, KeyError, AttributeError) as exc:
            logger.warning("model_artifact_unloadable", extra={"path": str(candidate)}, exc_info=exc)
            if get_settings().allow_heuristic_fallback:
                _cached_bundle = _default_bundle()
                return _cached_bundle
            raise FileNotFoundError("Model artifact not available") from exc

        _cached_bundle = ModelBundle(model, version, metadata, True)

        logger.info("model_loaded", extra={"version": _cached_bundle.version})
        return _cached_bundle


def _serving_feature_names(model: Any) -> list[str]:
    """Return the feature names the loaded model was trained on.

    New features are appended at the end of FEATURE_NAMES, so an older
    artifact (e.g. v1, 22 features) is served exactly its own prefix.
    This keeps artifact rollback working without a code change.
    """

    declared = getattr(model, "n_features_in_", len(FEATURE_NAMES))
    try:
        count = int(declared)
    except (TypeError, ValueError):
        count = len(FEATURE_NAMES)
    if count <= 0 or count > len(FEATURE_NAMES):
        count = len(FEATURE_NAMES)
    return FEATURE_NAMES[:count]


def feature_vector(values: dict[str, int | float | bool], names: list[str] | None = None) -> pd.DataFrame:
    """Convert named features to a labeled frame in model order (no sklearn name warnings)."""

    columns = names or FEATURE_NAMES
    row = {name: (float(bool(values[name])) if isinstance(values[name], bool) else float(values[name])) for name in columns}
    return pd.DataFrame([row], columns=columns)


def risk_level(risk_score: int) -> str:
    """Map a 0-100 risk score to the documented level thresholds."""

    if risk_score <= 33:
        return "low"
    if risk_score <= 66:
        return "medium"
    return "high"


@dataclass(frozen=True)
class PredictionResult:
    """Computed model output."""

    prediction: str
    confidence: float
    risk_score: int
    risk_level: str
    top_features: list[dict[str, Any]]


def predict(values: dict[str, int | float | bool]) -> PredictionResult:
    """Classify features using the active model and generate explanations."""

    bundle = load_bundle()
    probabilities = np.asarray(bundle.model.predict_proba(feature_vector(values, _serving_feature_names(bundle.model))))[0]
    phishing_probability = float(probabilities[1])
    prediction = "phishing" if phishing_probability >= 0.5 else "legitimate"
    confidence = phishing_probability if prediction == "phishing" else 1.0 - phishing_probability
    score = int(round(phishing_probability * 100))
    return PredictionResult(prediction, round(confidence, 4), score, risk_level(score), top_features(bundle.model, values))


def model_metadata() -> dict[str, Any]:
    """Return metadata for the active model."""

    bundle = load_bundle()
    metadata = dict(bundle.metadata)
    if bundle.loaded_from_artifact:
        # Only a real artifact may report trained metrics. Merging the report
        # for the heuristic fallback would attribute RandomForest scores to it.
        report_path = get_settings().model_metadata_path
        candidate = report_path if report_path.is_absolute() else Path(__file__).resolve().parents[2] / report_path
        if candidate.exists():
            try:
                report = json.loads(candidate.read_text(encoding="utf-8"))
                selected = next((item for item in report.get("models", []) if item.get("name") == report.get("selected_model")), {})
                metadata = {**selected, **metadata, "dataset_size": report.get("dataset_size", metadata.get("dataset_size", 0))}
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning("metadata_report_parse_failed", extra={"path": str(candidate)}, exc_info=exc)

    trained_at = metadata.get("trained_at", datetime.now(timezone.utc))
    if isinstance(trained_at, str):
        try:
            trained_at = datetime.fromisoformat(trained_at[:-1] + "+00:00" if trained_at.endswith("Z") else trained_at)
        except ValueError:
            logger.warning("metadata_trained_at_unparseable", extra={"value": trained_at})
            trained_at = datetime.now(timezone.utc)

    model_name = metadata.get("model_name", metadata.get("name", "HeuristicFallback"))
    return {
        "model_name": model_name,
        "algorithm": metadata.get("algorithm", model_name),
        "version": bundle.version,
        "accuracy": float(metadata.get("accuracy", 0.0)),
        "precision": float(metadata.get("precision", 0.0)),
        "recall": float(metadata.get("recall", 0.0)),
        "f1_score": float(metadata.get("f1_score", 0.0)),
        "roc_auc": float(metadata.get("roc_auc", 0.0)),
        "dataset_size": int(metadata.get("dataset_size", 0)),
        "trained_at": trained_at,
    }
