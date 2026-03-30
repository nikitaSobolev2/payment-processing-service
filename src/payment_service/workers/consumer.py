from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue
from pydantic import BaseModel, ConfigDict

from payment_service.config.settings import Settings, get_settings
from payment_service.infrastructure.messaging.constants import (
    DLQ_ROUTING_KEY,
    EXCHANGE_PAYMENTS_EVENTS,
    QUEUE_DLQ,
    QUEUE_PAYMENTS_NEW,
    ROUTING_KEY_PAYMENTS_NEW,
)
from payment_service.infrastructure.wiring import (
    PaymentFacadeDependencies,
    build_payment_facade_dependencies,
)

logger = logging.getLogger(__name__)


class PaymentNewMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: UUID


def _build_app(settings: Settings, deps: PaymentFacadeDependencies) -> FastStream:
    facade = deps.facade

    broker = RabbitBroker(settings.rabbitmq_url)
    app = FastStream(broker)

    payments_exchange = RabbitExchange(
        EXCHANGE_PAYMENTS_EVENTS,
        type=ExchangeType.TOPIC,
        durable=True,
    )
    payments_queue = RabbitQueue(
        QUEUE_PAYMENTS_NEW,
        durable=True,
        routing_key=ROUTING_KEY_PAYMENTS_NEW,
    )
    dlq_queue = RabbitQueue(QUEUE_DLQ, durable=True)

    max_attempts = settings.consumer_max_attempts

    @broker.subscriber(payments_queue, payments_exchange)
    async def handle_payment_new(msg: PaymentNewMessage) -> None:
        last_error: BaseException | None = None
        for attempt in range(max_attempts):
            try:
                await facade.process_payment_message(msg.payment_id)
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Processing attempt %s failed for payment %s: %s",
                    attempt + 1,
                    msg.payment_id,
                    exc,
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2**attempt)
        logger.error(
            "Giving up on payment %s after %s attempts; sending to DLQ",
            msg.payment_id,
            max_attempts,
        )
        await broker.publish(
            {"payment_id": str(msg.payment_id)},
            routing_key=DLQ_ROUTING_KEY,
        )
        if last_error is not None:
            logger.debug("Last error was: %s", last_error)

    @app.after_startup
    async def _declare_topology() -> None:
        await broker.declare_exchange(payments_exchange)
        await broker.declare_queue(dlq_queue)

    return app


def _wrap_exit_for_shutdown_logging(app: FastStream) -> None:
    original_exit = app.exit

    def exit_with_log() -> None:
        logger.info("graceful shutdown initiated")
        original_exit()

    app.exit = exit_with_log  # type: ignore[method-assign]


async def _run_consumer_async() -> None:
    settings = get_settings()
    deps = build_payment_facade_dependencies(settings)
    app = _build_app(settings, deps)
    _wrap_exit_for_shutdown_logging(app)
    try:
        await app.run()
    finally:
        await deps.webhook.aclose()
        await deps.redis_client.aclose()
        await deps.engine.dispose()
        logger.info("shutdown complete")


def main() -> None:
    logging.basicConfig(level=get_settings().log_level.upper())
    asyncio.run(_run_consumer_async())


if __name__ == "__main__":
    main()
