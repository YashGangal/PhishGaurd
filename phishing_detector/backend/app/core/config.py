"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API and model services."""

    app_name: str = "PhishGuard API"
    database_url: str = "sqlite:///./phishguard.db"
    # Resolved relative to phishing_detector/backend (see prediction.load_bundle).
    model_path: Path = Path("models/best_model.pkl")
    model_metadata_path: Path = Path("ml/comparison_report.json")
    cors_origins: str = "http://localhost:5173"
    enable_html_scraping: bool = False
    scraper_timeout_seconds: float = 4.0
    allow_heuristic_fallback: bool = True
    log_level: str = "INFO"
    # Threat-feed pre-filter (vendored snapshot, refreshed by ml/refresh_blocklist.py).
    blocklist_path: Path = Path("ml/data/feed_blocklist.csv")
    blocklist_enabled: bool = True
    # Verdict operating point. The frozen acceptance gate assumes 0.5;
    # change deliberately (measured candidates: ml/calibration_report.json).
    decision_threshold: float = 0.5
    # Advisory review band on calibrated phishing probability. Advisory only:
    # the verdict never changes because of it (needs a contract change to
    # enforce), it only flags low-margin calls for analysts.
    review_band_low: float = 0.4
    review_band_high: float = 0.6

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @field_validator("decision_threshold")
    @classmethod
    def _threshold_in_range(cls, value: float) -> float:
        """Fail fast on a nonsense operating point instead of misclassifying."""

        if not 0.0 < value < 1.0:
            raise ValueError("decision_threshold must be strictly between 0 and 1")
        return value

    @field_validator("review_band_high")
    @classmethod
    def _band_ordered(cls, value: float, info) -> float:
        """Fail fast on an inverted review band."""

        low = (info.data or {}).get("review_band_low", 0.4)
        if not 0.0 <= low <= value <= 1.0:
            raise ValueError("require 0 <= review_band_low <= review_band_high <= 1")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Return comma-separated CORS origins as a trimmed list."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings object."""

    return Settings()
