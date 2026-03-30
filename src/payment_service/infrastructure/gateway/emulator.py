from __future__ import annotations

import asyncio
import random

from payment_service.config.settings import Settings


class GatewayEmulator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def process_payment(self) -> bool:
        low = self._settings.gateway_min_delay_seconds
        high = self._settings.gateway_max_delay_seconds
        await asyncio.sleep(random.uniform(low, high))
        return random.random() < self._settings.gateway_success_probability
