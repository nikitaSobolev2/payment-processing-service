"""Per-URL webhook circuit breaker backed by Redis (closed / open / half-open).

Half-open uses a ``trial`` flag on the hash: after open cooldown expires, the first
``should_attempt`` sets ``trial=1`` and allows exactly one HTTP attempt; concurrent
callers see ``trial=1`` and skip until ``record_success`` / ``record_failure`` clears state.
"""

from __future__ import annotations

import time

from redis.asyncio import Redis

from payment_service.config.settings import Settings
from payment_service.infrastructure.webhook.url_key import webhook_circuit_redis_key

_SHOULD_ATTEMPT_LUA = """
local now = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local ou = tonumber(redis.call('HGET', KEYS[1], 'open_until') or '0')
local trial = tonumber(redis.call('HGET', KEYS[1], 'trial') or '0')

if ou > now then
  return 0
end

if ou > 0 and ou <= now then
  if trial == 0 then
    redis.call('HSET', KEYS[1], 'trial', '1')
    redis.call('EXPIRE', KEYS[1], ttl)
    return 1
  end
  return 0
end

if trial ~= 0 then
  redis.call('HSET', KEYS[1], 'trial', '0')
end
return 1
"""

_RECORD_FAILURE_LUA = """
local now = tonumber(ARGV[1])
local threshold = tonumber(ARGV[2])
local open_sec = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local trial = tonumber(redis.call('HGET', KEYS[1], 'trial') or '0')
local failures = tonumber(redis.call('HGET', KEYS[1], 'failures') or '0')

if trial == 1 then
  redis.call('HSET', KEYS[1], 'open_until', tostring(now + open_sec))
  redis.call('HSET', KEYS[1], 'trial', '0')
  redis.call('HSET', KEYS[1], 'failures', '0')
  redis.call('EXPIRE', KEYS[1], ttl)
  return 1
end

failures = failures + 1
if failures >= threshold then
  redis.call('HSET', KEYS[1], 'open_until', tostring(now + open_sec))
  redis.call('HSET', KEYS[1], 'failures', '0')
else
  redis.call('HSET', KEYS[1], 'failures', tostring(failures))
end
redis.call('EXPIRE', KEYS[1], ttl)
return 1
"""

_RECORD_SUCCESS_LUA = """
local ttl = tonumber(ARGV[1])
redis.call('HSET', KEYS[1], 'failures', '0')
redis.call('HSET', KEYS[1], 'open_until', '0')
redis.call('HSET', KEYS[1], 'trial', '0')
redis.call('EXPIRE', KEYS[1], ttl)
return 1
"""


class WebhookCircuitBreaker:
    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self._redis = redis_client
        self._settings = settings

    def _key(self, url: str) -> str:
        return webhook_circuit_redis_key(url)

    async def should_attempt(self, url: str) -> bool:
        key = self._key(url)
        now = time.time()
        ttl = self._settings.webhook_cb_key_ttl_seconds
        raw = await self._redis.eval(
            _SHOULD_ATTEMPT_LUA,
            1,
            key,
            str(now),
            str(ttl),
        )
        return int(raw) == 1

    async def record_failure(self, url: str) -> None:
        key = self._key(url)
        now = time.time()
        s = self._settings
        await self._redis.eval(
            _RECORD_FAILURE_LUA,
            1,
            key,
            str(now),
            str(s.webhook_cb_failure_threshold),
            str(s.webhook_cb_open_seconds),
            str(s.webhook_cb_key_ttl_seconds),
        )

    async def record_success(self, url: str) -> None:
        key = self._key(url)
        ttl = self._settings.webhook_cb_key_ttl_seconds
        await self._redis.eval(
            _RECORD_SUCCESS_LUA,
            1,
            key,
            str(ttl),
        )
