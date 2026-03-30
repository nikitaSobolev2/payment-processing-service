from __future__ import annotations

from dataclasses import dataclass

from payment_service.domain.payment import Payment


@dataclass(frozen=True)
class MarkProcessedResult:
    payment: Payment
    did_transition: bool
