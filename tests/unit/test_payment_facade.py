from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from payment_service.application.facades.payment_facade import PaymentFacade
from payment_service.domain.enums import Currency, PaymentStatus
from payment_service.domain.mark_processed_result import MarkProcessedResult
from payment_service.domain.money import Money
from payment_service.domain.payment import Payment
from payment_service.infrastructure.db.repositories.payment_repository import (
    PaymentRepository,
)


def _pending_payment() -> Payment:
    return Payment(
        id=uuid4(),
        amount=Money.from_decimal(Decimal("10.00"), Currency.RUB),
        description="x",
        metadata={},
        status=PaymentStatus.PENDING,
        idempotency_key="k",
        webhook_url="https://example.com/hook",
        created_at=datetime.now(UTC),
        processed_at=None,
    )


def _session_factory_with_begin() -> MagicMock:
    """async_sessionmaker-style: async with factory() as session, session.begin(): ..."""
    mock_session = MagicMock()
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=begin_cm)

    outer_cm = MagicMock()
    outer_cm.__aenter__ = AsyncMock(return_value=mock_session)
    outer_cm.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=outer_cm)
    return factory


@pytest.mark.asyncio
async def test_process_payment_message_does_not_notify_webhook_when_mark_returns_no_transition():
    session_factory = _session_factory_with_begin()
    gateway = MagicMock()
    gateway.process_payment = AsyncMock(return_value=True)
    webhook = MagicMock()
    webhook.notify = AsyncMock()
    facade = PaymentFacade(session_factory, None, gateway, webhook)

    processed = _pending_payment()
    same = Payment(
        id=processed.id,
        amount=processed.amount,
        description=processed.description,
        metadata=processed.metadata,
        status=PaymentStatus.SUCCEEDED,
        idempotency_key=processed.idempotency_key,
        webhook_url=processed.webhook_url,
        created_at=processed.created_at,
        processed_at=datetime.now(UTC),
    )

    with (
        patch.object(PaymentRepository, "get_by_id", new_callable=AsyncMock) as mock_get,
        patch.object(
            PaymentRepository,
            "mark_processed_with_snapshot",
            new_callable=AsyncMock,
        ) as mock_mark,
    ):
        mock_get.return_value = processed
        mock_mark.return_value = MarkProcessedResult(payment=same, did_transition=False)
        await facade.process_payment_message(processed.id)

    webhook.notify.assert_not_called()


@pytest.mark.asyncio
async def test_process_payment_message_notifies_webhook_when_mark_returns_transition():
    session_factory = _session_factory_with_begin()
    gateway = MagicMock()
    gateway.process_payment = AsyncMock(return_value=True)
    webhook = MagicMock()
    webhook.notify = AsyncMock()
    facade = PaymentFacade(session_factory, None, gateway, webhook)

    processed = _pending_payment()
    updated = Payment(
        id=processed.id,
        amount=processed.amount,
        description=processed.description,
        metadata=processed.metadata,
        status=PaymentStatus.SUCCEEDED,
        idempotency_key=processed.idempotency_key,
        webhook_url=processed.webhook_url,
        created_at=processed.created_at,
        processed_at=datetime.now(UTC),
    )

    with (
        patch.object(PaymentRepository, "get_by_id", new_callable=AsyncMock) as mock_get,
        patch.object(
            PaymentRepository,
            "mark_processed_with_snapshot",
            new_callable=AsyncMock,
        ) as mock_mark,
    ):
        mock_get.return_value = processed
        mock_mark.return_value = MarkProcessedResult(payment=updated, did_transition=True)
        await facade.process_payment_message(processed.id)

    webhook.notify.assert_awaited_once()
