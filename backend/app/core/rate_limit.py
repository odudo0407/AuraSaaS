"""Simple in-memory rate limiter for AuraSaaS API endpoints."""

from __future__ import annotations

import time
import os
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    """Sliding-window rate limiter keyed by client IP."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    def _clean(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._clients[key] = [t for t in self._clients[key] if t > cutoff]

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        self._clean(key, now)
        if len(self._clients[key]) >= self.max_requests:
            return False
        self._clients[key].append(now)
        return True


# Pre-configured limiters for different endpoint categories
_agent_limiter = RateLimiter(max_requests=5, window_seconds=60)   # expensive AI endpoints
_default_limiter = RateLimiter(max_requests=60, window_seconds=60)  # general API


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware that applies rate limits based on the request path."""

    if os.getenv("ENVIRONMENT", "").lower() == "test":
        return await call_next(request)

    # Skip rate limiting for static files, health checks, and docs
    path = request.url.path
    if path.startswith("/uploads") or path in ("/api/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{path}"

    limiter = _agent_limiter if "/agent/" in path else _default_limiter

    if not limiter.is_allowed(key):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

    return await call_next(request)
