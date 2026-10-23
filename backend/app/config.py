"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database. SQLite for local dev; swap to Postgres in production, e.g.
    #   postgresql+asyncpg://user:pass@host:5432/addyourline
    database_url: str = "sqlite+aiosqlite:///./addyourline.db"

    # Public base URL used to build invitation / shared-story links.
    public_base_url: str = "http://localhost:5173"

    # Comma-separated list of allowed CORS origins for the browser frontend.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Gameplay limits.
    max_name_length: int = 40
    max_turn_length: int = 600  # characters for a two-sentence contribution
    allowed_turn_counts: str = "10,20,30"

    # Simple per-IP rate limiting (requests per window) for write endpoints.
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_turn_count_set(self) -> set[int]:
        return {int(t.strip()) for t in self.allowed_turn_counts.split(",") if t.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
