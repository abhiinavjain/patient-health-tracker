from __future__ import annotations

import warnings
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-change-me-dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+psycopg://pht:pht@localhost:5432/pht"
    jwt_secret: str = DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: list[str] = ["http://localhost:3000"]
    # Where healthml model artifacts live; defaults to healthml's own setting (ml/artifacts).
    healthml_artifacts: str | None = None
    # Allow anyone to self-register as a patient (clinicians/admins are created by an admin).
    allow_patient_signup: bool = True
    # Failed-login throttling (per account): this many failures within the window -> temporary lockout.
    login_max_failures: int = 5
    login_window_minutes: int = 15

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, v: str) -> str:
        """Hosted Postgres (Neon, Render, Heroku) hands out postgres:// URLs; SQLAlchemy needs the driver named."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.jwt_secret == DEV_SECRET:
        if s.env != "dev":
            raise RuntimeError("JWT_SECRET must be set outside dev")
        warnings.warn("Using the built-in development JWT secret", stacklevel=2)
    return s
