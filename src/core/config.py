"""Kompler application configuration."""

import os
from functools import lru_cache

from dotenv import load_dotenv

# Force load .env with override (system env vars can shadow .env values)
load_dotenv(override=True)

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://kompler:kompler_dev@localhost:5432/kompler"
    database_url_sync: str = "postgresql://kompler:kompler_dev@localhost:5432/kompler"
    redis_url: str = "redis://localhost:6379/0"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "kompler-documents"

    # Anthropic
    anthropic_api_key: str = ""
    claude_classify_model: str = "claude-3-haiku-20240307"
    claude_extract_model: str = "claude-sonnet-4-20250514"
    claude_qa_model: str = "claude-sonnet-4-20250514"

    # Application
    environment: str = "dev"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # AI Settings
    confidence_threshold: float = 0.6
    max_agent_retries: int = 2
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    # Metering
    credit_cost_classify: float = 0.5
    credit_cost_extract: float = 2.0
    credit_cost_deep: float = 5.0
    credit_cost_qa: float = 0.0  # Q&A is always free

    # Cache
    semantic_cache_threshold: float = 0.90
    content_hash_enabled: bool = True

    # Graph
    entity_resolution_threshold: float = 0.85
    entity_resolution_ambiguous: float = 0.70

    # Security
    api_keys: str = "dev-key-1"
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # Rate Limits per tier
    rate_limit_starter: str = "60/minute"
    rate_limit_pro: str = "300/minute"
    rate_limit_business: str = "1000/minute"

    # Webhooks
    webhook_timeout_seconds: int = 10
    webhook_max_retries: int = 3

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = "dev"

    @property
    def api_keys_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    return Settings()
