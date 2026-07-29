"""Redis client with graceful fallback to in-memory storage.

When REDIS_URL is not configured or Redis is unreachable, all operations
fall back to an in-memory dict — the application continues to work
normally without Redis.

Usage::

    from app.core.redis_client import redis_client
    redis_client.set("key", "value", ttl=300)
    value = redis_client.get("key")
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── In-memory fallback store ────────────────────────────────────────────────


class _MemoryStore:
    """Thread-safe in-memory dict with TTL support."""

    def __init__(self):
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, str]] = {}  # key → (expiry, value)

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expiry, value = entry
            if time.time() > expiry:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: str, ttl: int = 300) -> None:
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def incr(self, key: str, ttl: int = 60) -> int:
        with self._lock:
            entry = self._store.get(key)
            now = time.time()
            if entry is None or now > entry[0]:
                self._store[key] = (now + ttl, "1")
                return 1
            count = int(entry[1]) + 1
            self._store[key] = (now + ttl, str(count))
            return count

    def exists(self, key: str) -> bool:
        return self.get(key) is not None


# ── Redis client wrapper ─────────────────────────────────────────────────────


class RedisClient:
    """Unified cache interface — Redis when available, in-memory fallback otherwise."""

    def __init__(self):
        self._redis = None
        self._memory = _MemoryStore()
        self._available = False
        self._init_attempted = False

    def _ensure(self) -> None:
        """Lazy-init: try Redis on first access, stay on memory if unreachable."""
        if self._init_attempted:
            return
        self._init_attempted = True

        settings = get_settings()
        redis_url = settings.redis_url.strip() if settings.redis_url else ""

        if not redis_url:
            logger.info("REDIS_URL not configured — using in-memory cache")
            return

        try:
            import redis as redis_py
            self._redis = redis_py.from_url(
                redis_url,
                socket_connect_timeout=3,
                socket_timeout=3,
                decode_responses=True,
            )
            self._redis.ping()
            self._available = True
            logger.info("Redis connected: %s", redis_url)
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — falling back to in-memory cache", exc)

    def get(self, key: str) -> str | None:
        self._ensure()
        if self._available and self._redis:
            try:
                return self._redis.get(key)
            except Exception:
                pass
        return self._memory.get(key)

    def set(self, key: str, value: str, ttl: int = 300) -> None:
        self._ensure()
        if self._available and self._redis:
            try:
                self._redis.set(key, value, ex=ttl)
                return
            except Exception:
                pass
        self._memory.set(key, value, ttl=ttl)

    def delete(self, key: str) -> None:
        self._ensure()
        if self._available and self._redis:
            try:
                self._redis.delete(key)
                return
            except Exception:
                pass
        self._memory.delete(key)

    def incr(self, key: str, ttl: int = 60) -> int:
        """Increment counter, returns new value. Used by rate limiter."""
        self._ensure()
        if self._available and self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl)
                results = pipe.execute()
                return int(results[0])
            except Exception:
                pass
        return self._memory.incr(key, ttl)

    def exists(self, key: str) -> bool:
        self._ensure()
        if self._available and self._redis:
            try:
                return bool(self._redis.exists(key))
            except Exception:
                pass
        return self._memory.exists(key)

    def is_available(self) -> bool:
        self._ensure()
        return self._available

    # ── convenience methods for Python objects ──

    def get_json(self, key: str) -> Any | None:
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_json(self, key: str, value: Any, ttl: int = 300) -> None:
        self.set(key, json.dumps(value, ensure_ascii=False), ttl=ttl)


# ── module-level singleton ───────────────────────────────────────────────────

redis_client = RedisClient()
