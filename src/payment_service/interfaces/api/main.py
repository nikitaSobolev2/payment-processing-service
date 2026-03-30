from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from payment_service.config.settings import get_settings
from payment_service.infrastructure.wiring import build_payment_facade_dependencies
from payment_service.interfaces.api.routes.v1 import payments_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    deps = build_payment_facade_dependencies(settings)
    app.state.facade = deps.facade
    app.state.engine = deps.engine
    app.state.redis = deps.redis_client
    yield
    await deps.webhook.aclose()
    await deps.redis_client.aclose()
    await deps.engine.dispose()


app = FastAPI(
    title="Payment processing service",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(payments_router, prefix="/api/v1")
