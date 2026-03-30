from unittest.mock import AsyncMock

import pytest

from payment_service.config.settings import Settings
from payment_service.infrastructure.webhook.circuit_breaker import WebhookCircuitBreaker
from payment_service.infrastructure.webhook.url_key import webhook_circuit_redis_key


def _settings() -> Settings:
    return Settings(
        api_key="k",
        database_url="postgresql+asyncpg://localhost/db",
        webhook_cb_failure_threshold=3,
        webhook_cb_open_seconds=10,
        webhook_cb_key_ttl_seconds=60,
    )


@pytest.mark.asyncio
async def test_should_attempt_returns_true_when_eval_returns_1():
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=1)
    cb = WebhookCircuitBreaker(redis, _settings())
    url = "https://example.com/hook"
    assert await cb.should_attempt(url) is True
    redis.eval.assert_awaited()
    call_args = redis.eval.await_args
    assert call_args[0][1] == 1
    assert call_args[0][2] == webhook_circuit_redis_key(url)


@pytest.mark.asyncio
async def test_should_attempt_returns_false_when_eval_returns_0():
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=0)
    cb = WebhookCircuitBreaker(redis, _settings())
    assert await cb.should_attempt("https://example.com/hook") is False


@pytest.mark.asyncio
async def test_record_success_invokes_eval():
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=1)
    cb = WebhookCircuitBreaker(redis, _settings())
    await cb.record_success("https://example.com/hook")
    assert redis.eval.await_count == 1


@pytest.mark.asyncio
async def test_record_failure_invokes_eval():
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=1)
    cb = WebhookCircuitBreaker(redis, _settings())
    await cb.record_failure("https://example.com/hook")
    assert redis.eval.await_count == 1
