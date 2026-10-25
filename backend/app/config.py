"""Application configuration loaded from environment variables."""
import os
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
    max_turn_length: int = 600  # characters for a contribution
    min_words: int = 4  # minimum words per contribution
    allowed_turn_counts: str = "10,20,30"  # quick-pick presets shown in the UI
    # Custom story lengths are allowed within this inclusive range.
    min_turns: int = 2
    max_turns: int = 50
    # Random mode ignores the players' length choice and picks one of these (max 10).
    random_turn_counts: str = "6,8,10"

    # Simple per-IP rate limiting (requests per window) for write endpoints.
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_turn_count_set(self) -> set[int]:
        return {int(t.strip()) for t in self.allowed_turn_counts.split(",") if t.strip()}

    @property
    def random_turn_count_list(self) -> list[int]:
        values = [int(t.strip()) for t in self.random_turn_counts.split(",") if t.strip()]
        return values or [10, 20, 30]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # On hosts that expose the service URL (e.g. Render sets RENDER_EXTERNAL_URL),
    # use it for invite/share links when PUBLIC_BASE_URL wasn't set explicitly.
    # Setting PUBLIC_BASE_URL (e.g. https://addyourline.com) always wins.
    if os.getenv("PUBLIC_BASE_URL") is None:
        external = os.getenv("RENDER_EXTERNAL_URL")
        if external:
            s.public_base_url = external.rstrip("/")
    return s


settings = get_settings()
