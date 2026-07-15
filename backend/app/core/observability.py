"""Lightweight request observability for the self-hosted demo."""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RequestMetrics:
    """In-memory rolling metrics for local demos and health dashboards."""

    started_at: float = field(default_factory=time.time)
    total_requests: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0.0
    recent: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=80))
    lock: Lock = field(default_factory=Lock)

    def record(self, *, method: str, path: str, status_code: int, latency_ms: float, request_id: str) -> None:
        with self.lock:
            self.total_requests += 1
            if status_code >= 500:
                self.total_errors += 1
            self.total_latency_ms += latency_ms
            self.recent.appendleft(
                {
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "latency_ms": round(latency_ms, 2),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            avg_latency = self.total_latency_ms / self.total_requests if self.total_requests else 0
            return {
                "uptime_seconds": round(time.time() - self.started_at, 2),
                "total_requests": self.total_requests,
                "total_errors": self.total_errors,
                "error_rate": round(self.total_errors / self.total_requests, 4) if self.total_requests else 0,
                "avg_latency_ms": round(avg_latency, 2),
                "recent_requests": list(self.recent),
            }


metrics = RequestMetrics()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request IDs and collect rolling latency/error metrics."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            metrics.record(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                latency_ms=latency_ms,
                request_id=request_id,
            )
            if "response" in locals():
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time-ms"] = f"{latency_ms:.2f}"
