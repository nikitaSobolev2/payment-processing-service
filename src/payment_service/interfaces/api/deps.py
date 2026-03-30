from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from payment_service.application.facades.payment_facade import PaymentFacade
from payment_service.config.settings import Settings, get_settings
from payment_service.constants.errors import HttpErrorDetail

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_api_key(
    api_key: Annotated[str, Depends(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=HttpErrorDetail.INVALID_OR_MISSING_API_KEY,
        )


def get_facade(request: Request) -> PaymentFacade:
    return request.app.state.facade
