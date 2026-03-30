from decimal import Decimal

import pytest

from payment_service.domain.enums import Currency
from payment_service.domain.money import Money


def test_money_from_decimal_to_decimal_roundtrip():
    m = Money.from_decimal(Decimal("100.50"), Currency.RUB)
    assert m.minor_units == 10050
    assert m.currency is Currency.RUB
    assert m.to_decimal() == Decimal("100.50")


def test_money_rejects_negative_minor_units():
    with pytest.raises(ValueError, match="minor_units"):
        Money(minor_units=-1, currency=Currency.EUR)
