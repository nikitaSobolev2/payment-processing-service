import pytest
from pydantic import ValidationError

from payment_service.application.dtos import CreatePaymentRequestDTO
from payment_service.domain.enums import Currency


def test_create_payment_request_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        CreatePaymentRequestDTO(
            amount=-1,
            currency=Currency.RUB,
            description="d",
            metadata={},
            webhook_url="https://example.com/hook",
        )
