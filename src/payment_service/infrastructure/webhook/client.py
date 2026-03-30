from __future__ import annotations

import asyncio
import logging

import httpx

from payment_service.application.dtos import WebhookPayloadDTO
from payment_service.config.settings import Settings
from payment_service.infrastructure.webhook.circuit_breaker import WebhookCircuitBreaker
from payment_service.infrastructure.webhook.url_key import webhook_url_log_id

logger = logging.getLogger(__name__)


class WebhookClient:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        circuit: WebhookCircuitBreaker | None = None,
    ) -> None:
        self._settings = settings
        self._circuit = circuit
        c = settings.webhook_connect_timeout_seconds
        r = settings.webhook_read_timeout_seconds
        timeout = httpx.Timeout(connect=c, read=r, write=r, pool=c)
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def notify(self, url: str, payload: WebhookPayloadDTO) -> None:
        log_id = webhook_url_log_id(url)
        if self._circuit is not None:
            allowed = await self._circuit.should_attempt(url)
            if not allowed:
                logger.warning(
                    "Webhook circuit open; skipping delivery for url_id=%s",
                    log_id,
                )
                return

        body = payload.model_dump(mode="json")
        last_error: Exception | None = None
        max_retries = self._settings.webhook_max_retries
        base = self._settings.webhook_backoff_base_seconds
        cap = self._settings.webhook_backoff_max_seconds
        for attempt in range(max_retries):
            try:
                response = await self._client.post(url, json=body)
                response.raise_for_status()
                if self._circuit is not None:
                    await self._circuit.record_success(url)
                return
            except Exception as exc:
                last_error = exc
                if self._circuit is not None:
                    await self._circuit.record_failure(url)
                logger.warning(
                    "Webhook attempt %s failed for %s: %s",
                    attempt + 1,
                    url,
                    exc,
                )
                if attempt < max_retries - 1:
                    delay = min(base * (2**attempt), cap)
                    await asyncio.sleep(delay)
        if last_error is not None:
            logger.error(
                "Webhook failed after %s attempts (best-effort, payment state unchanged): %s",
                max_retries,
                last_error,
            )

    async def aclose(self) -> None:
        await self._client.aclose()
