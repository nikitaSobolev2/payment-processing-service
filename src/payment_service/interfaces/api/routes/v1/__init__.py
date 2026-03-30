"""API version 1."""

from payment_service.interfaces.api.routes.v1.payments import router as payments_router

__all__ = ["payments_router"]
