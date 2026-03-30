from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from payment_service.application.dtos import (
    CreatePaymentRequestDTO,
    CreatePaymentResponseDTO,
    PaymentDetailDTO,
)
from payment_service.application.facades.payment_facade import PaymentFacade
from payment_service.constants.errors import HttpErrorDetail
from payment_service.interfaces.api.deps import get_facade, verify_api_key

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreatePaymentResponseDTO,
)
async def create_payment(
    body: CreatePaymentRequestDTO,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    facade: Annotated[PaymentFacade, Depends(get_facade)],
) -> CreatePaymentResponseDTO:
    return await facade.create_payment(body, idempotency_key)


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailDTO,
)
async def get_payment(
    payment_id: UUID,
    facade: Annotated[PaymentFacade, Depends(get_facade)],
) -> PaymentDetailDTO:
    detail = await facade.get_payment(payment_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=HttpErrorDetail.PAYMENT_NOT_FOUND,
        )
    return detail
