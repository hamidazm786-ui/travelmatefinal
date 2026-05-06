# app/core/config.py
# ============================================================
#  Central configuration — reads from .env via pydantic-settings
# ============================================================

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Server
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    allowed_origins: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:8080,http://127.0.0.1:8080"
        ),
        alias="ALLOWED_ORIGINS"
    )

    # Groq
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama3-70b-8192", alias="GROQ_MODEL")
    groq_fallback_model: str = Field(default="mixtral-8x7b-32768", alias="GROQ_FALLBACK_MODEL")

    # Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    # Tavily
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    tavily_max_results: int = Field(default=8, alias="TAVILY_MAX_RESULTS")
    tavily_search_depth: str = Field(default="advanced", alias="TAVILY_SEARCH_DEPTH")

    # File Upload
    max_file_size_mb: int = Field(default=10, alias="MAX_FILE_SIZE_MB")
    allowed_file_types: str = Field(default="pdf,txt,docx,png,jpg,jpeg", alias="ALLOWED_FILE_TYPES")

    # Rate Limiting
    rate_limit_requests: int = Field(default=30, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Security
    secret_key: str = Field(default="dev-secret-key", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/travelmate",
        alias="DATABASE_URL",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def allowed_extensions(self) -> List[str]:
        return [e.strip() for e in self.allowed_file_types.split(",")]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton — imported everywhere as `from app.core.config import get_settings`"""
    return Settings()
