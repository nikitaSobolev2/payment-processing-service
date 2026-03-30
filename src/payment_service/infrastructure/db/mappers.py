from __future__ import annotations

from payment_service.domain.enums import Currency, PaymentStatus, SnapshotReason
from payment_service.domain.money import Money
from payment_service.domain.payment import Payment
from payment_service.infrastructure.db.models import PaymentModel, PaymentSnapshotModel


def payment_model_to_domain(row: PaymentModel) -> Payment:
    return Payment(
        id=row.id,
        amount=Money(minor_units=row.amount_minor, currency=Currency(row.currency)),
        description=row.description,
        metadata=row.metadata_,
        status=PaymentStatus(row.status),
        idempotency_key=row.idempotency_key,
        webhook_url=row.webhook_url,
        created_at=row.created_at,
        processed_at=row.processed_at,
    )


def snapshot_state_from_payment(payment: Payment) -> dict:
    return {
        "id": str(payment.id),
        "amount_minor": payment.amount.minor_units,
        "currency": payment.amount.currency.value,
        "description": payment.description,
        "metadata": payment.metadata,
        "status": payment.status.value,
        "idempotency_key": payment.idempotency_key,
        "webhook_url": payment.webhook_url,
        "created_at": payment.created_at.isoformat(),
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }


def snapshot_model_from_payment(
    payment: Payment, version: int, reason: SnapshotReason
) -> PaymentSnapshotModel:
    return PaymentSnapshotModel(
        payment_id=payment.id,
        version=version,
        state=snapshot_state_from_payment(payment),
        reason=reason.value,
    )
