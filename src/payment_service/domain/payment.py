from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from payment_service.domain.enums import Currency, PaymentStatus


@dataclass(slots=True)
class Payment:
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

    def can_transition_to(self, new_status: PaymentStatus) -> bool:
        if self.status != PaymentStatus.PENDING:
            return False
        return new_status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED)
