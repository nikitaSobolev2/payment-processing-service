from __future__ import annotations

import json
from uuid import UUID

from redis.asyncio import Redis

from payment_service.application.dtos import PaymentDetailDTO


class PaymentCacheService:
    def __init__(self, client: Redis, ttl_seconds: int, key_prefix: str = "payment:") -> None:
        self._client = client
        self._ttl = ttl_seconds
        self._prefix = key_prefix

    def _key(self, payment_id: UUID) -> str:
        return f"{self._prefix}{payment_id}"

    async def get(self, payment_id: UUID) -> PaymentDetailDTO | None:
        raw = await self._client.get(self._key(payment_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return PaymentDetailDTO.model_validate(data)

    async def set(self, detail: PaymentDetailDTO) -> None:
        payload = detail.model_dump(mode="json")
        await self._client.set(self._key(detail.id), json.dumps(payload, default=str), ex=self._ttl)

    async def invalidate(self, payment_id: UUID) -> None:
        await self._client.delete(self._key(payment_id))
