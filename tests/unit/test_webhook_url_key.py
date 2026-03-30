from payment_service.infrastructure.webhook.url_key import (
    normalize_webhook_url,
    webhook_circuit_redis_key,
    webhook_url_key_digest,
)


def test_normalize_webhook_url_sorts_query_and_lowercases_host():
    a = normalize_webhook_url("HTTPS://Example.COM/x?z=1&a=2#frag")
    b = normalize_webhook_url("https://example.com/x?a=2&z=1")
    assert a == b
    assert "#" not in a


def test_webhook_circuit_redis_key_stable_for_equivalent_urls():
    k1 = webhook_circuit_redis_key("https://H.com/a?x=1&y=2")
    k2 = webhook_circuit_redis_key("https://h.com/a?y=2&x=1")
    assert k1 == k2
    assert k1.startswith("webhook:cb:")
    assert len(webhook_url_key_digest("https://h.com/a")) == 64
