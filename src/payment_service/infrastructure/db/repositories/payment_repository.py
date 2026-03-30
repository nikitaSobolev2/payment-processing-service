from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.constants.errors import RepositoryError
from payment_service.domain.enums import PaymentStatus, SnapshotReason
from payment_service.domain.mark_processed_result import MarkProcessedResult
from payment_service.domain.payment import Payment
from payment_service.infrastructure.db.mappers import (
    payment_model_to_domain,
    snapshot_model_from_payment,
)
from payment_service.infrastructure.db.models import OutboxModel, PaymentModel, PaymentSnapshotModel


def _payment_domain_to_insert_values(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "amount_minor": payment.amount.minor_units,
        "currency": payment.amount.currency.value,
        "description": payment.description,
        "metadata_": payment.metadata,
        "status": payment.status.value,
        "idempotency_key": payment.idempotency_key,
        "webhook_url": payment.webhook_url,
        "created_at": payment.created_at,
        "processed_at": payment.processed_at,
    }


async def _fetch_payment_row_by_id(
    session: AsyncSession,
    payment_id: UUID,
    *,
    for_update: bool,
) -> PaymentModel | None:
    stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
    if for_update:
        stmt = stmt.with_for_update()
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def _fetch_payment_row_by_idempotency_key(
    session: AsyncSession,
    key: str,
) -> PaymentModel | None:
    stmt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def _apply_processed_state_and_snapshot(
    session: AsyncSession,
    row: PaymentModel,
    payment_id: UUID,
    new_status: PaymentStatus,
    processed_at: datetime,
) -> MarkProcessedResult:
    snapshot_version = await next_snapshot_version(session, payment_id)
    row.status = new_status.value
    row.processed_at = processed_at
    updated = payment_model_to_domain(row)
    snap = snapshot_model_from_payment(
        updated,
        version=snapshot_version,
        reason=SnapshotReason.PROCESSED,
    )
    session.add(snap)
    await session.flush()
    return MarkProcessedResult(payment=updated, did_transition=True)


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        row = await _fetch_payment_row_by_idempotency_key(self._session, key)
        return payment_model_to_domain(row) if row else None

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        row = await _fetch_payment_row_by_id(
            self._session,
            payment_id,
            for_update=False,
        )
        return payment_model_to_domain(row) if row else None

    async def get_by_id_for_update(self, payment_id: UUID) -> Payment | None:
        row = await _fetch_payment_row_by_id(
            self._session,
            payment_id,
            for_update=True,
        )
        return payment_model_to_domain(row) if row else None

    async def save_new_payment_with_outbox_and_snapshot(
        self,
        *,
        payment: Payment,
        outbox_event_type: str,
        outbox_payload: dict,
        snapshot_version: int,
    ) -> Payment:
        ins = (
            insert(PaymentModel)
            .values(**_payment_domain_to_insert_values(payment))
            .on_conflict_do_nothing(
                constraint="uq_payments_idempotency_key",
            )
            .returning(PaymentModel.id)
        )
        result = await self._session.execute(ins)
        new_id = result.scalar_one_or_none()
        if new_id is None:
            existing = await self.get_by_idempotency_key(payment.idempotency_key)
            if existing is None:
                raise RuntimeError(RepositoryError.IDEMPOTENCY_CONFLICT)
            return existing

        outbox = OutboxModel(
            aggregate_id=payment.id,
            event_type=outbox_event_type,
            payload=outbox_payload,
        )
        snap = snapshot_model_from_payment(
            payment,
            version=snapshot_version,
            reason=SnapshotReason.CREATED,
        )
        self._session.add(outbox)
        self._session.add(snap)
        await self._session.flush()
        loaded = await self.get_by_id(payment.id)
        if loaded is None:
            raise RuntimeError(RepositoryError.PAYMENT_MISSING_AFTER_INSERT)
        return loaded

    async def mark_processed_with_snapshot(
        self,
        *,
        payment_id: UUID,
        new_status: PaymentStatus,
        processed_at: datetime,
    ) -> MarkProcessedResult | None:
        row = await _fetch_payment_row_by_id(
            self._session,
            payment_id,
            for_update=True,
        )
        if row is None:
            return None
        domain = payment_model_to_domain(row)
        if not domain.can_transition_to(new_status):
            return MarkProcessedResult(payment=domain, did_transition=False)

        return await _apply_processed_state_and_snapshot(
            self._session,
            row,
            payment_id,
            new_status,
            processed_at,
        )


async def next_snapshot_version(session: AsyncSession, payment_id: UUID) -> int:
    stmt = select(func.coalesce(func.max(PaymentSnapshotModel.version), 0)).where(
        PaymentSnapshotModel.payment_id == payment_id
    )
    res = await session.execute(stmt)
    current = int(res.scalar_one())
    return current + 1
