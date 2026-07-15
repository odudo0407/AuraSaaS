"""DeepSeek 多模型客户端，支持普通聊天、流式输出、推理内容捕获、预算熔断与实时用量统计。

预算控制：
    每次 API 调用前检查累计费用是否超过 AGENT_BUDGET_YUAN（默认 ¥0.02），
    超限时抛出 BudgetExceededError，绝不发起请求。

实时用量：
    API 返回后立即从 response.usage 提取 token 数，累加到内存变量并打印日志。
    通过 get_current_cost() 可随时查询累计费用。

异常策略：
    只捕获 httpx.TimeoutException / ConnectionError 用于重试，
    BudgetExceededError 绝不被吞掉。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import threading
from dataclasses import dataclass
from typing import AsyncGenerator

import httpx
from openai import OpenAI, Timeout
from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing & budget
# ---------------------------------------------------------------------------

INPUT_PRICE_PER_1M  = 1.02   # ¥ per 1 000 000 prompt tokens
OUTPUT_PRICE_PER_1M = 2.04   # ¥ per 1 000 000 completion tokens

_DEFAULT_BUDGET = float(os.getenv("AGENT_BUDGET_YUAN", "0.02"))


class BudgetExceededError(RuntimeError):
    """预算超限——本次 API 请求已被拦截，不会产生费用。"""


# ---------------------------------------------------------------------------
# In-memory cost tracker
# ---------------------------------------------------------------------------

@dataclass
class _CostTracker:
    prompt_tokens:     int = 0
    completion_tokens: int = 0

    @property
    def cost_yuan(self) -> float:
        return round(
            (self.prompt_tokens     / 1_000_000) * INPUT_PRICE_PER_1M +
            (self.completion_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M,
            8,
        )

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens     += prompt
        self.completion_tokens += completion

    def reset(self) -> None:
        self.prompt_tokens     = 0
        self.completion_tokens = 0


_tracker_lock = threading.Lock()
_tracker = _CostTracker()


def _check_budget() -> None:
    """Before every API call: raise if cumulative cost already exceeds budget."""
    with _tracker_lock:
        current = _tracker.cost_yuan
    if current >= _DEFAULT_BUDGET:
        raise BudgetExceededError(
            f"预算超限，请求已拦截 "
            f"(累计 ¥{current:.6f} / 预算 ¥{_DEFAULT_BUDGET:.4f}，"
            f"输入 {_tracker.prompt_tokens}t，输出 {_tracker.completion_tokens}t)"
        )


def _record_real_usage(prompt: int, completion: int) -> None:
    """Called immediately after a successful API response."""
    with _tracker_lock:
        _tracker.add(prompt, completion)
        cost = _tracker.cost_yuan
        total_prompt = _tracker.prompt_tokens
        total_completion = _tracker.completion_tokens

    logger.info(
        "真实用量 — 本次输入: %st | 本次输出: %st | "
        "累计输入: %st | 累计输出: %st | 累计费用: ¥%.6f",
        prompt, completion, total_prompt, total_completion, cost,
    )


def get_current_cost() -> dict:
    """对外接口：返回当前会话的累计用量和费用。

    Returns dict with keys: prompt_tokens, completion_tokens, total_tokens, cost_yuan.
    """
    with _tracker_lock:
        return {
            "prompt_tokens":     _tracker.prompt_tokens,
            "completion_tokens": _tracker.completion_tokens,
            "total_tokens":      _tracker.prompt_tokens + _tracker.completion_tokens,
            "cost_yuan":         _tracker.cost_yuan,
        }


def reset_cost() -> None:
    """重置累计用量（每次新会话开始时调用）。"""
    with _tracker_lock:
        _tracker.reset()


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------

MODEL_MAP = {
    "deepseek-v3":       "deepseek-chat",
    "deepseek-chat":     "deepseek-chat",
    "deepseek-r1":       "deepseek-reasoner",
    "deepseek-reasoner": "deepseek-reasoner",
    "deepseek-v4":       "deepseek-chat",
    "deepseek-v4-pro":   "deepseek-chat",
}

MODEL_LABELS = {
    "deepseek-chat":     "DeepSeek-V3",
    "deepseek-reasoner": "DeepSeek-R1",
    "deepseek-v3":       "DeepSeek-V3",
    "deepseek-r1":       "DeepSeek-R1",
    "deepseek-v4":       "DeepSeek-V4",
    "deepseek-v4-pro":   "DeepSeek-V4 Pro",
}


def resolve_model(model: str) -> str:
    return MODEL_MAP.get(model, "deepseek-chat")


def get_model_label(model: str) -> str:
    return MODEL_LABELS.get(model, model)


def get_client(api_key: str | None = None, base_url: str | None = None) -> OpenAI:
    key = api_key or os.getenv("DEEPSEEK_API_KEY") or settings.deepseek_api_key
    url = base_url or os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_API_BASE") or settings.deepseek_base_url
    http_client = httpx.Client(trust_env=False)
    return OpenAI(api_key=key, base_url=url, http_client=http_client)


def has_valid_api_key() -> bool:
    key = os.getenv("DEEPSEEK_API_KEY") or settings.deepseek_api_key
    if not key:
        return False
    return key.strip() not in {"sk-placeholder", "sk-your-key-here", "sk-xxxx", "your-key", ""}


# ---------------------------------------------------------------------------
# Retry policy — only for known transient network errors
# ---------------------------------------------------------------------------

_RETRYABLE = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    ConnectionError,
    OSError,
)


def _retry_attempt(attempt: int, exc: Exception) -> bool:
    """Return True if we should retry, False if error is non-retryable."""
    if not isinstance(exc, _RETRYABLE):
        return False
    if attempt >= settings.llm_max_retries:
        return False
    wait = 1.0 * (2 ** attempt)
    logger.warning("LLM 调用可重试错误 (attempt %d/%d): %s — 等待 %.1fs",
                   attempt + 1, settings.llm_max_retries, exc, wait)
    time.sleep(wait)
    return True


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

def chat(
    system: str,
    user: str,
    fallback: str,
    model: str = "deepseek-chat",
    temperature: float = 0.3,
    max_tokens: int = 800,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    """同步 chat completion，带预算检查、重试和实时用量记录。"""
    if not has_valid_api_key():
        return fallback

    resolved = resolve_model(model)
    last_error = ""

    for attempt in range(settings.llm_max_retries + 1):
        try:
            _check_budget()                                 # ① 预算门控

            client = get_client(api_key, base_url)
            resp = client.chat.completions.create(
                model=resolved,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=Timeout(settings.llm_timeout_seconds),
            )

            if resp.usage:                                  # ② 记录真实用量
                _record_real_usage(resp.usage.prompt_tokens, resp.usage.completion_tokens)

            return resp.choices[0].message.content or fallback

        except BudgetExceededError:                         # ③ 绝不吞掉
            raise

        except Exception as exc:
            last_error = str(exc)
            if not _retry_attempt(attempt, exc):
                break

    return f"{fallback}\n\n[LLM 降级提示] {last_error}"


def chat_with_tools(
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    model: str = "deepseek-chat",
    temperature: float = 0.3,
    max_tokens: int = 1200,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict | None:
    """带 function calling 的 chat completion，含预算检查与用量记录。"""
    if not has_valid_api_key():
        return None

    resolved = resolve_model(model)
    last_error = ""

    for attempt in range(settings.llm_max_retries + 1):
        try:
            _check_budget()

            client = get_client(api_key, base_url)
            kwargs: dict = {
                "model":       resolved,
                "messages":    messages,
                "temperature": temperature,
                "max_tokens":  max_tokens,
                "timeout":     Timeout(settings.llm_timeout_seconds),
            }
            if tools:
                kwargs["tools"]      = tools
                kwargs["tool_choice"] = tool_choice

            resp = client.chat.completions.create(**kwargs)

            if resp.usage:
                _record_real_usage(resp.usage.prompt_tokens, resp.usage.completion_tokens)

            msg = resp.choices[0].message

            tool_calls = None
            if msg.tool_calls:
                tool_calls = [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            return {
                "role":       "assistant",
                "content":    msg.content,
                "tool_calls": tool_calls,
            }

        except BudgetExceededError:
            raise

        except Exception as exc:
            last_error = str(exc)
            if not _retry_attempt(attempt, exc):
                break

    return {
        "role":       "assistant",
        "content":    f"LLM 调用失败: {last_error}",
        "tool_calls": None,
    }


async def chat_stream(
    system: str,
    user: str,
    model: str = "deepseek-chat",
    temperature: float = 0.3,
    max_tokens: int = 800,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncGenerator[dict, None]:
    """异步流式 chat completion，预算门控 + 用量在最后一个 chunk 记录。"""
    resolved = resolve_model(model)

    if not has_valid_api_key():
        yield {"type": "content", "content": "[演示模式] 请在设置中配置 DeepSeek API Key 以启用 AI 功能。", "done": False}
        yield {"type": "done", "content": "", "done": True}
        return

    _check_budget()                                        # ① 流启动前检查预算

    client = get_client(api_key, base_url)

    try:
        stream = client.chat.completions.create(
            model=resolved,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=Timeout(settings.llm_timeout_seconds),
        )

        think_buffer   = ""
        content_buffer = ""
        in_think       = False
        last_usage     = None

        for chunk in stream:
            if chunk.usage:                                  # ② 最后一个 chunk 带 usage
                last_usage = chunk.usage

            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            text = delta.content or ""

            # <think> tag handling for R1/V4 reasoning models
            if "<｜end▁of▁thinking｜><think>" in text or text.startswith(" response<think>"):
                in_think = True
                text = re.sub(r"^\s*response<think>", "", text)
            if " response</think>" in text:
                in_think = False
                text = text.replace(" response</think>", "")
                think_buffer += text
                yield {"type": "thinking", "content": text, "think_content": think_buffer, "done": False}
                continue

            if in_think:
                think_buffer += text
                yield {"type": "thinking", "content": text, "think_content": think_buffer, "done": False}
            else:
                if " response<think>" in text:
                    parts = text.split(" response<think>", 1)
                    content_buffer += parts[0]
                    if parts[0]:
                        yield {"type": "content", "content": parts[0], "done": False}
                    in_think = True
                    think_buffer = parts[1] if len(parts) > 1 else ""
                    if think_buffer:
                        yield {"type": "thinking", "content": think_buffer, "think_content": think_buffer, "done": False}
                elif " response</think>" in text:
                    parts = text.split(" response</think>", 1)
                    think_buffer += parts[0]
                    yield {"type": "thinking", "content": parts[0], "think_content": think_buffer, "done": False}
                    in_think = False
                    if len(parts) > 1 and parts[1]:
                        content_buffer += parts[1]
                        yield {"type": "content", "content": parts[1], "done": False}
                else:
                    content_buffer += text
                    yield {"type": "content", "content": text, "done": False}

        if last_usage:                                       # ③ 流结束后记录真实用量
            _record_real_usage(last_usage.prompt_tokens, last_usage.completion_tokens)

        yield {
            "type":         "done",
            "content":      content_buffer,
            "think_content": think_buffer,
            "done":         True,
        }

    except BudgetExceededError:                              # ④ 绝不吞掉
        raise
    except Exception as exc:
        yield {"type": "error", "content": str(exc), "done": True}


async def chat_stream_sse(
    system: str,
    user: str,
    model: str = "deepseek-chat",
    temperature: float = 0.3,
    max_tokens: int = 800,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncGenerator[str, None]:
    """SSE-friendly JSON-string wrapper around chat_stream."""
    async for event in chat_stream(system, user, model, temperature, max_tokens, api_key, base_url):
        yield json.dumps(event, ensure_ascii=False)
