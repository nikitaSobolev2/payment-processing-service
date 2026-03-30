from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_webhook_url(url: str) -> str:
    """Stable string for hashing: scheme/host lowercased, fragment dropped, query sorted."""
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.sort()
    query = urlencode(pairs)
    return urlunparse((scheme, netloc, path, "", query, ""))


def webhook_url_key_digest(url: str) -> str:
    """SHA-256 hex of normalized URL — fixed length and safe to log (no raw URL)."""
    normalized = normalize_webhook_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def webhook_circuit_redis_key(url: str) -> str:
    return f"webhook:cb:{webhook_url_key_digest(url)}"


def webhook_url_log_id(url: str) -> str:
    """Short prefix for logs (first 8 hex chars of digest)."""
    return webhook_url_key_digest(url)[:8]
