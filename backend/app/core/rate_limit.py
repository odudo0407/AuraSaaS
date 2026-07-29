"""Rate limiter — Redis-backed when available, in-memory fallback otherwise.

When Redis is configured, counters are shared across processes, enabling
safe multi-process deployments.  Otherwise a thread-safe in-memory store
is used (single-process only).
"""

from __future__ import annotations

import time
import os
from fastapi import Request, HTTPException

from app.core.redis_client import redis_client


class RateLimiter:
    """Sliding-window rate limiter using Redis or in-memory storage."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, key: str) -> bool:
        """Increment the request counter; return True if under the limit."""
        count = redis_client.incr(f"ratelimit:{key}", ttl=self.window_seconds)
        return count <= self.max_requests


# Pre-configured limiters for different endpoint categories
_agent_limiter = RateLimiter(max_requests=5, window_seconds=60)    # expensive AI endpoints
_default_limiter = RateLimiter(max_requests=60, window_seconds=60)  # general API


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware that applies rate limits based on the request path."""

    if os.getenv("ENVIRONMENT", "").lower() == "test":
        return await call_next(request)

    path = request.url.path
    if path.startswith("/uploads") or path in ("/api/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{path}"

    limiter = _agent_limiter if "/agent/" in path else _default_limiter

    if not limiter.is_allowed(key):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

    return await call_next(request)
