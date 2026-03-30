from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from payment_service.domain.enums import PaymentStatus
from payment_service.domain.mark_processed_result import MarkProcessedResult
from payment_service.domain.payment import Payment


class PaymentRepositoryPort(Protocol):
    async def get_by_idempotency_key(self, key: str) -> Payment | None: ...

    async def get_by_id(self, payment_id: UUID) -> Payment | None: ...

    async def get_by_id_for_update(self, payment_id: UUID) -> Payment | None: ...

    async def save_new_payment_with_outbox_and_snapshot(
        self,
        *,
        payment: Payment,
        outbox_event_type: str,
        outbox_payload: dict,
        snapshot_version: int,
    ) -> Payment: ...

    async def mark_processed_with_snapshot(
        self,
        *,
        payment_id: UUID,
        new_status: PaymentStatus,
        processed_at: datetime,
    ) -> MarkProcessedResult | None: ...
