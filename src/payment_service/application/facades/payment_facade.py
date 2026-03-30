from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.application.dtos import (
    CreatePaymentRequestDTO,
    CreatePaymentResponseDTO,
    OutboxPayloadDTO,
    PaymentDetailDTO,
    payment_to_webhook_payload,
)
from payment_service.domain.enums import PaymentStatus
from payment_service.domain.money import Money
from payment_service.domain.payment import Payment
from payment_service.infrastructure.cache.redis_cache import PaymentCacheService
from payment_service.infrastructure.db.repositories.payment_repository import (
    PaymentRepository,
)
from payment_service.infrastructure.gateway.emulator import GatewayEmulator
from payment_service.infrastructure.messaging.constants import EVENT_PAYMENTS_NEW
from payment_service.infrastructure.time import utc_now
from payment_service.infrastructure.webhook.client import WebhookClient


def _payment_to_detail(p: Payment) -> PaymentDetailDTO:
    return PaymentDetailDTO(
        id=p.id,
        amount=p.amount.to_decimal(),
        currency=p.amount.currency,
        description=p.description,
        metadata=p.metadata,
        status=p.status,
        idempotency_key=p.idempotency_key,
        webhook_url=p.webhook_url,
        created_at=p.created_at,
        processed_at=p.processed_at,
    )


def _new_payment_from_create(
    body: CreatePaymentRequestDTO,
    idempotency_key: str,
    *,
    payment_id: UUID,
    created_at: datetime,
) -> tuple[Payment, dict]:
    payment = Payment(
        id=payment_id,
        amount=Money.from_decimal(body.amount, body.currency),
        description=body.description,
        metadata=body.metadata,
        status=PaymentStatus.PENDING,
        idempotency_key=idempotency_key,
        webhook_url=str(body.webhook_url),
        created_at=created_at,
        processed_at=None,
    )
    payload = OutboxPayloadDTO(payment_id=payment_id).model_dump(mode="json")
    return payment, payload


class PaymentFacade:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: PaymentCacheService | None,
        gateway: GatewayEmulator,
        webhook: WebhookClient,
    ) -> None:
        self._session_factory = session_factory
        self._cache = cache
        self._gateway = gateway
        self._webhook = webhook

    async def _refresh_detail_cache(self, payment_id: UUID, p: Payment) -> None:
        if self._cache:
            await self._cache.invalidate(payment_id)
            await self._cache.set(_payment_to_detail(p))

    async def _notify_webhook_for_payment(self, p: Payment) -> None:
        payload = payment_to_webhook_payload(p)
        await self._webhook.notify(p.webhook_url, payload)

    async def create_payment(
        self,
        body: CreatePaymentRequestDTO,
        idempotency_key: str,
    ) -> CreatePaymentResponseDTO:
        now = utc_now()
        payment_id = uuid.uuid4()
        payment, outbox_payload = _new_payment_from_create(
            body,
            idempotency_key,
            payment_id=payment_id,
            created_at=now,
        )
        async with self._session_factory() as session, session.begin():
            repo = PaymentRepository(session)
            saved = await repo.save_new_payment_with_outbox_and_snapshot(
                payment=payment,
                outbox_event_type=EVENT_PAYMENTS_NEW,
                outbox_payload=outbox_payload,
                snapshot_version=1,
            )
        detail = _payment_to_detail(saved)
        if self._cache:
            await self._cache.set(detail)
        return CreatePaymentResponseDTO(
            payment_id=saved.id,
            status=saved.status,
            created_at=saved.created_at,
        )

    async def get_payment(self, payment_id: UUID) -> PaymentDetailDTO | None:
        if self._cache:
            cached = await self._cache.get(payment_id)
            if cached is not None:
                return cached
        async with self._session_factory() as session:
            repo = PaymentRepository(session)
            row = await repo.get_by_id(payment_id)
        if row is None:
            return None
        detail = _payment_to_detail(row)
        if self._cache:
            await self._cache.set(detail)
        return detail

    async def process_payment_message(self, payment_id: UUID) -> None:
        async with self._session_factory() as session:
            repo = PaymentRepository(session)
            current = await repo.get_by_id(payment_id)
        if current is None or current.status != PaymentStatus.PENDING:
            return

        gateway_ok = await self._gateway.process_payment()
        new_status = PaymentStatus.SUCCEEDED if gateway_ok else PaymentStatus.FAILED
        processed_at = utc_now()

        async with self._session_factory() as session, session.begin():
            repo = PaymentRepository(session)
            result = await repo.mark_processed_with_snapshot(
                payment_id=payment_id,
                new_status=new_status,
                processed_at=processed_at,
            )

        if result is None or not result.did_transition:
            return

        updated = result.payment
        await self._refresh_detail_cache(payment_id, updated)
        await self._notify_webhook_for_payment(updated)
