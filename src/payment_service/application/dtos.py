from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from payment_service.domain.enums import Currency, PaymentStatus
from payment_service.domain.payment import Payment


class CreatePaymentRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0)
    currency: Currency
    description: str = Field(min_length=1, max_length=4096)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl


class CreatePaymentResponseDTO(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime


class PaymentDetailDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None


class OutboxPayloadDTO(BaseModel):
    """Payload for payments.new events."""

    payment_id: UUID


class WebhookPayloadDTO(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    processed_at: datetime | None


def payment_to_webhook_payload(payment: Payment) -> WebhookPayloadDTO:
    return WebhookPayloadDTO(
        payment_id=payment.id,
        status=payment.status,
        amount=payment.amount.to_decimal(),
        currency=payment.amount.currency,
        description=payment.description,
        metadata=payment.metadata,
        processed_at=payment.processed_at,
    )
