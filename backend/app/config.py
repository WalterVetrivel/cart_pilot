"""Environment configuration (SPEC §16)."""

import os
from functools import lru_cache
from typing import Literal

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

    firestore_emulator_host: str | None = None

    # "auto": Firestore on Cloud Run or when FIRESTORE_EMULATOR_HOST is set, else in-memory seed data.
    datastore: Literal["auto", "memory", "firestore"] = "auto"
    max_upload_mb: int = 20

    # Local-only escape hatch: accept requests without a Firebase ID token and
    # treat them as user "dev-user". Never set this on Cloud Run.
    auth_disabled: bool = False

    @property
    def use_firestore(self) -> bool:
        if self.datastore != "auto":
            return self.datastore == "firestore"
        return bool(self.firestore_emulator_host or os.environ.get("K_SERVICE"))

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


# Google client libraries (google-genai, ADK, Firestore) read these from the process
# environment, not from our .env file, so copy any values set there across.
_EXPORTED = {
    "GOOGLE_CLOUD_PROJECT": "google_cloud_project",
    "GOOGLE_CLOUD_LOCATION": "google_cloud_location",
    "GOOGLE_GENAI_USE_VERTEXAI": "google_genai_use_vertexai",
    "GOOGLE_API_KEY": "google_api_key",
    "FIRESTORE_EMULATOR_HOST": "firestore_emulator_host",
}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for env_name, field in _EXPORTED.items():
        value = getattr(settings, field)
        if value is not None and env_name not in os.environ:
            os.environ[env_name] = str(value).upper() if isinstance(value, bool) else str(value)
    return settings
