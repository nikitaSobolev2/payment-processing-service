from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.infrastructure.db.models import OutboxModel
from payment_service.infrastructure.time import utc_now

# Rows claimed but never finalized (crash after commit) are reclaimed after this age.
_STALE_CLAIM_SECONDS = 300


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_batch_for_publish(self, limit: int) -> list[OutboxModel]:
        stale_before = utc_now() - timedelta(seconds=_STALE_CLAIM_SECONDS)
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.published_at.is_(None))
            .where(
                or_(
                    OutboxModel.claimed_at.is_(None),
                    OutboxModel.claimed_at < stale_before,
                ),
            )
            .order_by(OutboxModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        res = await self._session.execute(stmt)
        rows = list(res.scalars().all())
        now = utc_now()
        for row in rows:
            row.claimed_at = now
        return rows

    async def finalize_publish(self, outbox_id: uuid.UUID) -> None:
        stmt = select(OutboxModel).where(OutboxModel.id == outbox_id).with_for_update()
        res = await self._session.execute(stmt)
        row = res.scalar_one_or_none()
        if row is None:
            return
        row.published_at = utc_now()
        row.claimed_at = None

    async def release_claim(self, outbox_id: uuid.UUID) -> None:
        stmt = select(OutboxModel).where(OutboxModel.id == outbox_id).with_for_update()
        res = await self._session.execute(stmt)
        row = res.scalar_one_or_none()
        if row is not None and row.published_at is None:
            row.claimed_at = None
