from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from payment_service.domain.enums import Currency

_MINOR_EXPONENT: ClassVar[dict[Currency, int]] = {
    Currency.RUB: 2,
    Currency.USD: 2,
    Currency.EUR: 2,
}


@dataclass(frozen=True, slots=True)
class Money:
    """Monetary amount as integer minor units (e.g. kopecks, cents) — no floating point."""

    minor_units: int
    currency: Currency

    def __post_init__(self) -> None:
        if self.minor_units < 0:
            msg = "minor_units must be non-negative"
            raise ValueError(msg)

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: Currency) -> Money:
        exp = _MINOR_EXPONENT[currency]
        step = Decimal(1) / (Decimal(10) ** exp)
        quantized = amount.quantize(step)
        scale = Decimal(10) ** exp
        minor = int((quantized * scale).to_integral_value())
        return cls(minor_units=minor, currency=currency)

    def to_decimal(self) -> Decimal:
        exp = _MINOR_EXPONENT[self.currency]
        scale = Decimal(10) ** exp
        return Decimal(self.minor_units) / scale
