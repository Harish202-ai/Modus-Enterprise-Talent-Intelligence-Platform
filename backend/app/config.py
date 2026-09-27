"""All runtime configuration. Values come from environment variables / `.env` only.

Nothing in this module is a business value (prices, weights, questions, ...) —
those live in MongoDB. This file only knows *where* things are and which
secrets to use.
"""
from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- app ---
    app_name: str = "METI-MC API"
    environment: str = "local"  # local | dev | qa | uat | prod
    log_level: str = "INFO"
    api_prefix: str = "/v1"
    cors_origins: Annotated[List[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- data stores ---
    mongo_uri: str  # MongoDB Atlas connection string — required, no local fallback
    mongo_db: str = "METI"
    redis_uri: str = "redis://localhost:6379/0"

    # --- tenancy ---
    # Slug of the tenant used while the MVP runs single-tenant.
    default_tenant_slug: str = "modus"
    default_tenant_name: str = "Modus Enterprise Transformation"

    # --- auth (Phase 2) ---
    jwt_secret: str = "change-me"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 14
    refresh_cookie_name: str = "meti_refresh"
    # Sign-in attempts per email and per client IP within the window (a successful sign-in resets the email count).
    auth_rate_window_seconds: int = 900
    auth_rate_limit_per_email: int = 5
    auth_rate_limit_per_ip: int = 30

    # --- AI provider (Phase 5b onwards) — see app/ai/provider.py ---
    ai_provider: str = ""  # anthropic | openai (any OpenAI-compatible API: OpenAI, Ollama, Groq, LM Studio …)
    ai_model: str = ""
    ai_api_key: str = ""
    ai_base_url: str = ""  # openai-compatible only, e.g. http://host.docker.internal:11434/v1 for Ollama
    ai_timeout_seconds: int = 90

    # --- voice (Phase 8) — see app/ai/voice_provider.py ---
    # "webspeech" (default) = the browser's built-in Web Speech API, zero-cost, all client-side (no
    # server key needed). A hosted STT/TTS provider can be plugged in later behind the same abstraction.
    voice_provider: str = "webspeech"
    voice_api_key: str = ""
    voice_api_region: str = ""

    # --- uploads (Phase 5) ---
    uploads_dir: str = "uploads"  # Docker: /data/uploads (named volume)
    upload_max_mb_document: int = 10
    upload_max_mb_video: int = 200

    # --- payments (Phase 4, Stripe test mode) ---
    # Open-access switch: when true, the paywall is bypassed for everyone — every candidate can
    # open every assessment and the Detailed Report/Roadmap without buying anything (no Stripe
    # needed). Set FREE_ACCESS=true in the environment to turn the whole app free.
    free_access: bool = False
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    # Where Stripe Checkout sends the browser back to.
    frontend_url: str = "http://localhost:3000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        # Allow a comma-separated string in .env: CORS_ORIGINS=http://a,http://b
        if isinstance(value, str) and not value.strip().startswith("["):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value


    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_provider and self.ai_model and (self.ai_api_key or self.ai_base_url))

    @property
    def payments_configured(self) -> bool:
        return bool(self.stripe_secret_key)

    @property
    def is_dev(self) -> bool:
        return self.environment in ("local", "dev")

    @model_validator(mode="after")
    def _safe_outside_dev(self):
        if not self.is_dev:
            if self.jwt_secret == "change-me" or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be a random string of 32+ characters outside local/dev")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
