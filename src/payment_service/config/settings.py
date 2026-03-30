from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(..., description="Static API key for X-API-Key header")
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = Field(
        ...,
        alias="DATABASE_URL",
        description="SQLAlchemy async URL, e.g. postgresql+asyncpg://...",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl_seconds: int = Field(default=120, alias="REDIS_CACHE_TTL_SECONDS")

    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", alias="RABBITMQ_URL")

    outbox_poll_interval_ms: int = Field(default=200, alias="OUTBOX_POLL_INTERVAL_MS")
    outbox_batch_size: int = Field(default=50, alias="OUTBOX_BATCH_SIZE")

    webhook_max_retries: int = Field(default=3, alias="WEBHOOK_MAX_RETRIES")
    webhook_backoff_base_seconds: float = Field(default=1.0, alias="WEBHOOK_BACKOFF_BASE_SECONDS")
    webhook_backoff_max_seconds: float = Field(
        default=30.0,
        alias="WEBHOOK_BACKOFF_MAX_SECONDS",
    )
    webhook_connect_timeout_seconds: float = Field(
        default=5.0,
        alias="WEBHOOK_CONNECT_TIMEOUT_SECONDS",
    )
    webhook_read_timeout_seconds: float = Field(
        default=15.0,
        alias="WEBHOOK_READ_TIMEOUT_SECONDS",
    )

    webhook_cb_failure_threshold: int = Field(default=5, alias="WEBHOOK_CB_FAILURE_THRESHOLD")
    webhook_cb_open_seconds: int = Field(default=60, alias="WEBHOOK_CB_OPEN_SECONDS")
    webhook_cb_key_ttl_seconds: int = Field(default=300, alias="WEBHOOK_CB_KEY_TTL_SECONDS")

    gateway_min_delay_seconds: float = Field(default=2.0, alias="GATEWAY_MIN_DELAY_SECONDS")
    gateway_max_delay_seconds: float = Field(default=5.0, alias="GATEWAY_MAX_DELAY_SECONDS")
    gateway_success_probability: float = Field(default=0.9, alias="GATEWAY_SUCCESS_PROBABILITY")

    consumer_max_attempts: int = Field(default=3, alias="CONSUMER_MAX_ATTEMPTS")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
