import os
from collections.abc import Generator

import pytest

from payment_service.config.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/payments"),
    )
    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/15"))
    monkeypatch.setenv("RABBITMQ_URL", os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"))
