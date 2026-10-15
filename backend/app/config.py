"""Environment configuration (SPEC §16)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_cloud_project: str | None = None
    google_cloud_location: str = "asia-south1"
    google_genai_use_vertexai: bool = False
    google_api_key: str | None = None  # local dev only
    gemini_model: str = "gemini-2.5-flash"

    max_order_inr: int = 5000
    allowed_origins: str = "http://localhost:5173"

    # Local-only escape hatch: accept requests without a Firebase ID token and
    # treat them as user "dev-user". Never set this on Cloud Run.
    auth_disabled: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
