from datetime import UTC, datetime
from uuid import uuid4

from payment_service.domain.enums import Currency, PaymentStatus
from payment_service.domain.money import Money
from payment_service.domain.payment import Payment


def test_payment_can_transition_from_pending_to_succeeded():
    p = Payment(
        id=uuid4(),
        amount=Money(minor_units=1000, currency=Currency.RUB),
        description="x",
        metadata={},
        status=PaymentStatus.PENDING,
        idempotency_key="k1",
        webhook_url="https://example.com/hook",
        created_at=datetime.now(UTC),
        processed_at=None,
    )
    assert p.can_transition_to(PaymentStatus.SUCCEEDED) is True


def test_payment_cannot_transition_from_succeeded():
    p = Payment(
        id=uuid4(),
        amount=Money(minor_units=100, currency=Currency.USD),
        description="x",
        metadata={},
        status=PaymentStatus.SUCCEEDED,
        idempotency_key="k2",
        webhook_url="https://example.com/hook",
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
    )
    assert p.can_transition_to(PaymentStatus.FAILED) is False
