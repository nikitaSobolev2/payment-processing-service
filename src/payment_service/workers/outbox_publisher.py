"""Poll outbox and publish to RabbitMQ (transactional outbox relay)."""

from __future__ import annotations

import asyncio
import logging
import uuid

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_service.config.settings import get_settings
from payment_service.infrastructure.db.repositories.outbox_repository import (
    OutboxRepository,
)
from payment_service.infrastructure.db.session import create_engine_and_session_factory
from payment_service.infrastructure.messaging.constants import (
    EXCHANGE_PAYMENTS_EVENTS,
    ROUTING_KEY_PAYMENTS_NEW,
)
from payment_service.workers.shutdown import (
    install_shutdown_handlers,
    wait_until_shutdown_or_sleep,
)

logger = logging.getLogger(__name__)


def build_payments_exchange() -> RabbitExchange:
    return RabbitExchange(
        EXCHANGE_PAYMENTS_EVENTS,
        type=ExchangeType.TOPIC,
        durable=True,
    )


async def _publish_claimed_items(
    work_items: list[tuple[uuid.UUID, object]],
    *,
    broker: RabbitBroker,
    exchange: RabbitExchange,
    session_factory: async_sessionmaker[AsyncSession],
    shutdown: asyncio.Event,
) -> None:
    for outbox_id, payload in work_items:
        if shutdown.is_set():
            break
        try:
            await broker.publish(
                payload,
                exchange=exchange,
                routing_key=ROUTING_KEY_PAYMENTS_NEW,
            )
        except Exception:
            logger.exception("Outbox publish failed for outbox id %s", outbox_id)
            async with session_factory() as session, session.begin():
                repo = OutboxRepository(session)
                await repo.release_claim(outbox_id)
            continue
        async with session_factory() as session, session.begin():
            repo = OutboxRepository(session)
            await repo.finalize_publish(outbox_id)


async def run_loop() -> None:
    settings = get_settings()
    engine, session_factory = create_engine_and_session_factory(settings)
    shutdown = asyncio.Event()
    install_shutdown_handlers(shutdown)

    broker = RabbitBroker(settings.rabbitmq_url)
    exchange = build_payments_exchange()
    interval = settings.outbox_poll_interval_ms / 1000.0
    batch_size = max(1, settings.outbox_batch_size)

    async def one_iteration() -> bool:
        """Returns True if the outer loop should stop."""
        try:
            async with session_factory() as session, session.begin():
                repo = OutboxRepository(session)
                claimed = await repo.claim_batch_for_publish(batch_size)
                work_items = [(row.id, row.payload) for row in claimed]

            if not work_items:
                return await wait_until_shutdown_or_sleep(
                    shutdown,
                    min(interval, 0.05),
                )

            await _publish_claimed_items(
                work_items,
                broker=broker,
                exchange=exchange,
                session_factory=session_factory,
                shutdown=shutdown,
            )
        except Exception:
            logger.exception("Outbox batch failed")

        if shutdown.is_set():
            return True
        return await wait_until_shutdown_or_sleep(shutdown, interval)

    try:
        async with broker:
            await broker.declare_exchange(exchange)
            while not shutdown.is_set():
                if await one_iteration():
                    break
    finally:
        await engine.dispose()
        logger.info("shutdown complete")


def main() -> None:
    logging.basicConfig(level=get_settings().log_level.upper())
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
