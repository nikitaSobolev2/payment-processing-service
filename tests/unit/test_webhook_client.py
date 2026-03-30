from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from payment_service.application.dtos import WebhookPayloadDTO
from payment_service.config.settings import Settings
from payment_service.domain.enums import Currency, PaymentStatus
from payment_service.infrastructure.webhook.client import WebhookClient


@pytest.mark.asyncio
async def test_webhook_notify_retries_configured_times_then_returns_without_raising():
    settings = Settings(
        api_key="k",
        database_url="postgresql+asyncpg://localhost/db",
        webhook_max_retries=3,
        webhook_backoff_base_seconds=0.0,
    )
    payload = WebhookPayloadDTO(
        payment_id=uuid4(),
        status=PaymentStatus.SUCCEEDED,
        amount=Decimal("1.00"),
        currency=Currency.RUB,
        description="d",
        metadata={},
        processed_at=None,
    )
    client = httpx.AsyncClient()
    wc = WebhookClient(settings, client=client)
    mock_post = AsyncMock(side_effect=httpx.HTTPError("boom"))
    with patch.object(client, "post", mock_post):
        await wc.notify("https://example.com/hook", payload)
    assert mock_post.await_count == 3
    await wc.aclose()


@pytest.mark.asyncio
async def test_webhook_notify_skips_http_when_circuit_denies():
    settings = Settings(
        api_key="k",
        database_url="postgresql+asyncpg://localhost/db",
        webhook_max_retries=3,
        webhook_backoff_base_seconds=0.0,
    )
    payload = WebhookPayloadDTO(
        payment_id=uuid4(),
        status=PaymentStatus.SUCCEEDED,
        amount=Decimal("1.00"),
        currency=Currency.RUB,
        description="d",
        metadata={},
        processed_at=None,
    )
    circuit = AsyncMock()
    circuit.should_attempt = AsyncMock(return_value=False)
    circuit.record_failure = AsyncMock()
    client = httpx.AsyncClient()
    wc = WebhookClient(settings, client=client, circuit=circuit)
    mock_post = AsyncMock()
    with patch.object(client, "post", mock_post):
        await wc.notify("https://example.com/hook", payload)
    mock_post.assert_not_called()
    circuit.should_attempt.assert_awaited_once()
    circuit.record_failure.assert_not_called()
    await wc.aclose()
