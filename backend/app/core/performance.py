"""Agent performance tracking — lightweight decorator for elapsed time + external metrics.

Usage:
    from app.core.performance import track_performance, set_perf_context

    @track_performance
    async def run_react_agent_stream(query, ...):
        # ... somewhere during execution ...
        set_perf_context(rag_hit_rate=0.67, extra_metrics={"tool_calls": 3})
        ...

The decorator works with sync / async / async-generator functions.
After the function returns, it prints to console and writes a JSON line to
``backend/logs/agent_performance.log``.

Token billing is handled separately inside ``deepseek_client.py``.
BudgetExceededError (raised by deepseek_client) is caught and logged.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.deepseek_client import BudgetExceededError, get_current_cost

# ---------------------------------------------------------------------------
# Per-invocation context (set by the running function, read by the decorator)
# ---------------------------------------------------------------------------

@dataclass
class _PerfContext:
    rag_hit_rate:  float | None = None   # 0.0 – 1.0
    extra_metrics: dict[str, Any] | None = None


_store = threading.local()

try:
    from contextvars import ContextVar
    _cv_ctx: ContextVar[_PerfContext] = ContextVar("perf_ctx")
except ImportError:
    _cv_ctx = None  # type: ignore[assignment]


def _get_ctx() -> _PerfContext:
    if _cv_ctx is not None:
        try:
            return _cv_ctx.get()
        except LookupError:
            pass
    if not hasattr(_store, "ctx"):
        _store.ctx = _PerfContext()
    return _store.ctx


def _reset_ctx() -> None:
    if _cv_ctx is not None:
        _cv_ctx.set(_PerfContext())
    _store.ctx = _PerfContext()


def set_perf_context(
    rag_hit_rate: float | None = None,
    extra_metrics: dict[str, Any] | None = None,
) -> None:
    """Call this inside a decorated function to attach metrics.

    The decorator will include these values when it prints and logs the
    performance record after the function finishes.
    """
    ctx = _get_ctx()
    if rag_hit_rate is not None:
        ctx.rag_hit_rate = rag_hit_rate
    if extra_metrics is not None:
        if ctx.extra_metrics is None:
            ctx.extra_metrics = {}
        ctx.extra_metrics.update(extra_metrics)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    _logger = logging.getLogger("agent_performance")
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

    if not _logger.handlers:
        fh = logging.FileHandler(log_dir / "agent_performance.log", encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(message)s"))
        _logger.addHandler(fh)

    return _logger


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _report(func_name: str, elapsed_s: float, ctx: _PerfContext,
            budget_exceeded: bool = False) -> None:
    ts = datetime.now(timezone.utc).isoformat()

    # Pull cumulative cost from deepseek_client
    try:
        cost_info = get_current_cost()
    except Exception:
        cost_info = {}

    record: dict[str, Any] = {
        "timestamp":       ts,
        "function":        func_name,
        "elapsed_seconds": round(elapsed_s, 3),
    }
    if cost_info:
        record["prompt_tokens"]     = cost_info.get("prompt_tokens", 0)
        record["completion_tokens"] = cost_info.get("completion_tokens", 0)
        record["total_tokens"]      = cost_info.get("total_tokens", 0)
        record["cost_yuan"]         = cost_info.get("cost_yuan", 0)
    if ctx.rag_hit_rate is not None:
        record["rag_hit_rate"] = ctx.rag_hit_rate
    if ctx.extra_metrics:
        record["extra"] = ctx.extra_metrics
    if budget_exceeded:
        record["budget_exceeded"] = True

    # Console — one clean line
    extra_parts = []
    if budget_exceeded:
        extra_parts.append("\u26a0 预算超限")
    if cost_info:
        extra_parts.append(
            f"输入: {cost_info.get('prompt_tokens', 0)}t | "
            f"输出: {cost_info.get('completion_tokens', 0)}t | "
            f"费用: ¥{cost_info.get('cost_yuan', 0):.6f}"
        )
    if ctx.rag_hit_rate is not None:
        extra_parts.append(f"RAG命中率: {ctx.rag_hit_rate:.0%}")
    if ctx.extra_metrics:
        extra_parts.append(" | ".join(f"{k}={v}" for k, v in ctx.extra_metrics.items()))

    extra_str = (" | " + " | ".join(extra_parts)) if extra_parts else ""
    try:
        print(f"[{ts}] {func_name} | elapsed: {record['elapsed_seconds']}s{extra_str}")
    except UnicodeEncodeError:
        print(f"[{ts}] {func_name} | elapsed: {record['elapsed_seconds']}s")

    # JSON log file
    _get_logger().info(json.dumps(record, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def track_performance(func):
    """Measure elapsed time of an Agent entry function.

    Compatible with sync, async, and async-generator functions.
    Catches BudgetExceededError from deepseek_client and logs it.
    """

    if inspect.iscoroutinefunction(func):
        if inspect.isasyncgenfunction(func):

            @functools.wraps(func)
            async def _async_gen_wrapper(*args, **kwargs):
                _reset_ctx()
                t0 = time.perf_counter()
                exceeded = False
                try:
                    async for item in func(*args, **kwargs):
                        yield item
                except BudgetExceededError:
                    exceeded = True
                finally:
                    _report(func.__name__, time.perf_counter() - t0,
                            _get_ctx(), exceeded)

            return _async_gen_wrapper

        @functools.wraps(func)
        async def _async_wrapper(*args, **kwargs):
            _reset_ctx()
            t0 = time.perf_counter()
            exceeded = False
            try:
                result = await func(*args, **kwargs)
                return result
            except BudgetExceededError:
                exceeded = True
                return None
            finally:
                _report(func.__name__, time.perf_counter() - t0,
                        _get_ctx(), exceeded)

        return _async_wrapper

    @functools.wraps(func)
    def _sync_wrapper(*args, **kwargs):
        _reset_ctx()
        t0 = time.perf_counter()
        exceeded = False
        try:
            result = func(*args, **kwargs)
            return result
        except BudgetExceededError:
            exceeded = True
            return None
        finally:
            _report(func.__name__, time.perf_counter() - t0,
                    _get_ctx(), exceeded)

    return _sync_wrapper
