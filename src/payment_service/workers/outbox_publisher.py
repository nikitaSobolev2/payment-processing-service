"""Poll outbox and publish to RabbitMQ (transactional outbox relay)."""

from __future__ import annotations

import asyncio
import logging

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange

from payment_service.config.settings import get_settings
from payment_service.infrastructure.db.repositories.outbox_repository import (
    OutboxRepository,
)
from payment_service.infrastructure.db.session import create_engine_and_session_factory
from payment_service.infrastructure.messaging.constants import (
    EXCHANGE_PAYMENTS_EVENTS,
    ROUTING_KEY_PAYMENTS_NEW,
)

logger = logging.getLogger(__name__)


def build_payments_exchange() -> RabbitExchange:
    return RabbitExchange(
        EXCHANGE_PAYMENTS_EVENTS,
        type=ExchangeType.TOPIC,
        durable=True,
    )


async def run_loop() -> None:
    settings = get_settings()
    _, session_factory = create_engine_and_session_factory(settings)
    broker = RabbitBroker(settings.rabbitmq_url)
    exchange = build_payments_exchange()
    interval = settings.outbox_poll_interval_ms / 1000.0
    batch_size = max(1, settings.outbox_batch_size)

    async with broker:
        await broker.declare_exchange(exchange)
        while True:
            try:
                async with session_factory() as session, session.begin():
                    repo = OutboxRepository(session)
                    claimed = await repo.claim_batch_for_publish(batch_size)
                    work_items = [(row.id, row.payload) for row in claimed]

                if not work_items:
                    await asyncio.sleep(min(interval, 0.05))
                    continue

                for outbox_id, payload in work_items:
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
            except Exception:
                logger.exception("Outbox batch failed")
            await asyncio.sleep(interval)


def main() -> None:
    logging.basicConfig(level=get_settings().log_level.upper())
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
