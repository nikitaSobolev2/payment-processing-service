from __future__ import annotations

from dataclasses import dataclass

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from payment_service.application.facades.payment_facade import PaymentFacade
from payment_service.config.settings import Settings
from payment_service.infrastructure.cache.redis_cache import PaymentCacheService
from payment_service.infrastructure.db.session import create_engine_and_session_factory
from payment_service.infrastructure.gateway.emulator import GatewayEmulator
from payment_service.infrastructure.webhook.circuit_breaker import WebhookCircuitBreaker
from payment_service.infrastructure.webhook.client import WebhookClient


@dataclass(frozen=True)
class PaymentFacadeDependencies:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis_client: redis.Redis
    cache: PaymentCacheService
    gateway: GatewayEmulator
    webhook: WebhookClient
    facade: PaymentFacade


def build_payment_facade_dependencies(settings: Settings) -> PaymentFacadeDependencies:
    engine, session_factory = create_engine_and_session_factory(settings)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    cache = PaymentCacheService(redis_client, settings.redis_cache_ttl_seconds)
    gateway = GatewayEmulator(settings)
    circuit = WebhookCircuitBreaker(redis_client, settings)
    webhook = WebhookClient(settings, circuit=circuit)
    facade = PaymentFacade(session_factory, cache, gateway, webhook)
    return PaymentFacadeDependencies(
        engine=engine,
        session_factory=session_factory,
        redis_client=redis_client,
        cache=cache,
        gateway=gateway,
        webhook=webhook,
        facade=facade,
    )
