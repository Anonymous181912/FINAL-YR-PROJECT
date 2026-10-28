import os
from pathlib import Path
from typing import List
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to backend directory for robust loading regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    omni_route_api_key: str = Field(default="", validation_alias=AliasChoices("OMNIROUTE_API_KEY", "OMNI_ROUTE_API_KEY"))
    omni_route_base_url: str = Field(default="https://api.groq.com/openai/v1", validation_alias=AliasChoices("OMNIROUTE_BASE_URL", "OMNI_ROUTE_BASE_URL"))
    omni_route_model: str = Field(default="qwen/qwen3.8-27b", validation_alias=AliasChoices("OMNIROUTE_MODEL", "OMNI_ROUTE_MODEL"))
    omni_route_timeout: int = Field(default=60, validation_alias=AliasChoices("OMNIROUTE_TIMEOUT", "OMNI_ROUTE_TIMEOUT"))
    # Legacy provider cap, kept for backwards compatibility. LLM_MAX_OUTPUT_TOKENS
    # is the value used by the client because some providers reject 2048 OTPM.
    omni_route_max_tokens: int = Field(default=2048, validation_alias=AliasChoices("OMNIROUTE_MAX_TOKENS", "OMNI_ROUTE_MAX_TOKENS"))
    llm_model: str = Field(default="", validation_alias=AliasChoices("LLM_MODEL"))
    llm_fallback_model: str = Field(default="", validation_alias=AliasChoices("LLM_FALLBACK_MODEL"))
    llm_max_output_tokens: int = Field(default=800, validation_alias=AliasChoices("LLM_MAX_OUTPUT_TOKENS"))

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "healthcare_system"

    secret_key: str = "change_me_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    upload_dir: str = "uploads"
    max_upload_size: int = 10 * 1024 * 1024
    allowed_extensions: str = "pdf,png,jpg,jpeg,txt"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"

    # Phase 0: first-admin seeding (values come from env, never committed).
    admin_email: str = ""
    admin_password: str = ""
    admin_full_name: str = "System Administrator"

    # Phase 0: rate limiting (slowapi). Per-minute budgets per endpoint.
    rate_limit_login: str = "10/minute"
    rate_limit_register: str = "10/minute"
    rate_limit_upload: str = "20/minute"
    rate_limit_chat: str = "30/minute"

    # Phase 2: public verification links + reminders.
    frontend_url: str = "http://localhost:5173"
    notifications_enabled: bool = True
    reminder_interval_hours: int = 24

    # Phase 2: optional SMTP (if unset, in-app notifications only).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # Phase 4: per-feature LLM models (empty = default omni model), upload mode.
    llm_model_interpret: str = ""
    llm_model_chat: str = ""
    sync_upload: bool = True

    # Longitudinal trends: |change_pct| below this is "stable".
    trend_stable_threshold_pct: float = 5.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]


settings = Settings()
