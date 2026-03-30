"""User-facing HTTP details and repository RuntimeError message strings."""

from __future__ import annotations

from typing import Final


class HttpErrorDetail:
    PAYMENT_NOT_FOUND: Final[str] = "Payment not found"
    INVALID_OR_MISSING_API_KEY: Final[str] = "Invalid or missing API key"


class RepositoryError:
    IDEMPOTENCY_CONFLICT: Final[str] = "Conflict on idempotency_key but row not found"
    PAYMENT_MISSING_AFTER_INSERT: Final[str] = "Payment not found after insert"
