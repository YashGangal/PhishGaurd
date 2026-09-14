"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API and model services."""

    app_name: str = "PhishGuard API"
    database_url: str = "sqlite:///./phishguard.db"
    model_path: Path = Path("../models/best_model.pkl")
    model_metadata_path: Path = Path("../ml/comparison_report.json")
    cors_origins: str = "http://localhost:5173"
    enable_html_scraping: bool = False
    scraper_timeout_seconds: float = 4.0
    allow_heuristic_fallback: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return comma-separated CORS origins as a trimmed list."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings object."""

    return Settings()
