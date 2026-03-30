from __future__ import annotations

import asyncio

import pytest

from payment_service.workers.shutdown import (
    install_shutdown_handlers,
    wait_until_shutdown_or_sleep,
)


@pytest.mark.asyncio
async def test_wait_until_shutdown_or_sleep_returns_true_when_event_already_set() -> None:
    shutdown = asyncio.Event()
    shutdown.set()
    assert await wait_until_shutdown_or_sleep(shutdown, 10.0) is True


@pytest.mark.asyncio
async def test_wait_until_shutdown_or_sleep_returns_false_after_timeout() -> None:
    shutdown = asyncio.Event()
    assert await wait_until_shutdown_or_sleep(shutdown, 0.01) is False


@pytest.mark.asyncio
async def test_wait_until_shutdown_or_sleep_returns_true_when_set_during_wait() -> None:
    shutdown = asyncio.Event()

    async def set_soon() -> None:
        await asyncio.sleep(0.01)
        shutdown.set()

    task = asyncio.create_task(set_soon())
    assert await wait_until_shutdown_or_sleep(shutdown, 1.0) is True
    await task


@pytest.mark.asyncio
async def test_install_shutdown_handlers_does_not_raise_with_running_loop() -> None:
    shutdown = asyncio.Event()
    install_shutdown_handlers(shutdown)
    shutdown.set()
