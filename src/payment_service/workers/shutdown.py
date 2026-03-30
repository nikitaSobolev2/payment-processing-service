"""Graceful shutdown helpers for worker processes (asyncio.Event + signals)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_INITIATED_MESSAGE = "graceful shutdown initiated"


def _request_shutdown(
    shutdown: asyncio.Event,
    initiated: list[bool],
    log: Callable[[str], None],
) -> None:
    if initiated[0]:
        return
    initiated[0] = True
    log(_INITIATED_MESSAGE)
    shutdown.set()


def install_shutdown_handlers(
    shutdown: asyncio.Event,
    *,
    loop: asyncio.AbstractEventLoop | None = None,
) -> None:
    """Register SIGINT/SIGTERM"""
    initiated: list[bool] = [False]

    def log_info(msg: str) -> None:
        logger.info("%s", msg)

    def on_signal() -> None:
        _request_shutdown(shutdown, initiated, log_info)

    running_loop = loop or asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            running_loop.add_signal_handler(sig, on_signal)
        except (NotImplementedError, OSError):
            if sig is signal.SIGINT:
                signal.signal(signal.SIGINT, lambda *_: on_signal())
            elif hasattr(signal, "SIGTERM"):
                with contextlib.suppress(OSError, ValueError):
                    signal.signal(signal.SIGTERM, lambda *_: on_signal())


async def wait_until_shutdown_or_sleep(
    shutdown: asyncio.Event,
    delay_seconds: float,
) -> bool:
    if shutdown.is_set():
        return True
    try:
        await asyncio.wait_for(shutdown.wait(), timeout=max(delay_seconds, 0.0))
    except TimeoutError:
        return False
    return True
