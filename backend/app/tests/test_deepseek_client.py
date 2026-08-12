"""Unit tests for DeepSeek client — demo fallback, budget check, cost tracking.

These tests run WITHOUT a real API key. They verify:
  - Demo mode kicks in when no valid key is configured
  - Budget exceeded error fires when cost > limit
  - Cost tracking math is correct
  - reset_cost() actually clears everything
  Add by:odudo
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

# ── Test environment: fake key → demo mode ──────────────────────────────────
os.environ["DEEPSEEK_API_KEY"] = "sk-placeholder"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ENVIRONMENT"] = "test"

from app.services.deepseek_client import (
    has_valid_api_key,
    chat,
    chat_with_tools,
    get_current_cost,
    reset_cost,
    _check_budget,
    _record_real_usage,
    BudgetExceededError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. API Key 检测 — has_valid_api_key()
# ═══════════════════════════════════════════════════════════════════════════════

def test_placeholder_key_is_invalid():
    """sk-placeholder 是假 Key，系统应该识别并拒绝"""
    assert has_valid_api_key() is False

def test_your_key_here_is_invalid():
    """sk-your-key-here 占位 key 被识别为无效"""
    import app.services.deepseek_client as dc

    dc._request_api_key = "sk-your-key-here"
    try:
        assert has_valid_api_key() is False
    finally:
        dc._request_api_key = None


def test_real_looking_key_is_valid():
    """以 sk- 开头的真实格式 Key 应该通过检测"""
    import app.services.deepseek_client as dc

    dc._request_api_key = "sk-real-key-abc123"
    try:
        assert has_valid_api_key() is True
    finally:
        dc._request_api_key = None  # 清理，不影响后续测试


def test_empty_key_is_invalid():
    """空字符串 Key 无效"""
    import app.services.deepseek_client as dc

    dc._request_api_key = ""
    try:
        assert has_valid_api_key() is False
    finally:
        dc._request_api_key = None


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Demo 降级 — chat()
# ═══════════════════════════════════════════════════════════════════════════════

def test_chat_demo_mode_returns_fallback():
    """没有 Key 时，chat() 不调 API，直接返回 fallback 文案"""
    fallback = "[演示] 这是离线回复，请配置 API Key"

    result = chat(
        system="你是一个 BI 分析师",
        user="今天营收怎么样？",
        fallback=fallback,
    )

    # 应该原样返回 fallback，不包含任何 LLM 输出格式
    assert result == fallback


def test_chat_demo_mode_ignores_other_params():
    """Demo 模式下 system/user/model 全被忽略，只认 fallback"""
    result = chat(
        system="忽略我",
        user="也忽略我",
        fallback="唯一输出",
        model="deepseek-v4",
        temperature=0.9,
        max_tokens=2000,
    )
    assert result == "唯一输出"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Demo 降级 — chat_with_tools()
# ═══════════════════════════════════════════════════════════════════════════════

def test_chat_with_tools_demo_mode_returns_none():
    """没有 Key 时，带工具调用的 chat 返回 None（表示无法决策）"""
    result = chat_with_tools(
        messages=[{"role": "user", "content": "查询今天的营收"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_daily_summary",
                    "description": "查询当日经营数据",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )
    assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Demo 降级 — chat_stream()  异步流式
# ═══════════════════════════════════════════════════════════════════════════════

def test_chat_stream_demo_mode_yields_demo_message():
    """没有 Key 时，流式输出直接返回演示模式提示 + done"""
    import asyncio
    from app.services.deepseek_client import chat_stream

    async def _collect():
        events = []
        async for event in chat_stream(
            system="你是一个助手",
            user="你好",
        ):
            events.append(event)
        return events

    events = asyncio.run(_collect())

    # Demo 模式只产生 2 个事件：提示文本 + 结束标记
    assert len(events) == 2
    assert events[0]["type"] == "content"
    assert "演示模式" in events[0]["content"]
    assert events[1]["type"] == "done"
    assert events[1]["done"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 预算超限 — _check_budget()
# ═══════════════════════════════════════════════════════════════════════════════

def test_budget_exceeded_raises_error():
    """累计费用超过预算时，_check_budget() 必须抛出 BudgetExceededError"""
    import app.services.deepseek_client as dc

    reset_cost()

    # 模拟消耗大量 token：50万 prompt token ≈ ¥0.51，超过默认 ¥0.50
    _record_real_usage(prompt=500_000, completion=0)

    try:
        _check_budget()
        assert False, "没抛异常 = 预算熔断失效，这是安全缺陷"
    except BudgetExceededError as e:
        error_msg = str(e)
        assert "预算超限" in error_msg
        assert "0.51" in error_msg or "¥" in error_msg
    finally:
        reset_cost()


def test_budget_under_limit_passes():
    """累计费用未超预算时，_check_budget() 不抛异常"""
    import app.services.deepseek_client as dc

    reset_cost()
    _record_real_usage(prompt=1000, completion=1000)  # 约 ¥0.003

    try:
        _check_budget()  # 不应该抛异常
    except BudgetExceededError:
        assert False, "小额度不应该触发熔断"
    finally:
        reset_cost()



# ═══════════════════════════════════════════════════════════════════════════════
# 6. 费用计算
# ═══════════════════════════════════════════════════════════════════════════════

def test_cost_calculation_is_accurate():
    """验证费用 = prompt * 1.02/1M + completion * 2.04/1M"""
    reset_cost()
    _record_real_usage(prompt=100_000, completion=50_000)

    cost = get_current_cost()

    expected_prompt_cost = (100_000 / 1_000_000) * 1.02   # 0.102
    expected_compl_cost  = (50_000  / 1_000_000) * 2.04   # 0.102
    expected_total       = round(expected_prompt_cost + expected_compl_cost, 8)

    assert cost["prompt_tokens"] == 100_000
    assert cost["completion_tokens"] == 50_000
    assert cost["total_tokens"] == 150_000
    assert cost["cost_yuan"] == expected_total



def test_cost_zero_on_startup():
    """刚启动时，累计费用为 0"""
    reset_cost()
    cost = get_current_cost()
    assert cost["prompt_tokens"] == 0
    assert cost["completion_tokens"] == 0
    assert cost["total_tokens"] == 0
    assert cost["cost_yuan"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 7. 费用重置
# ═══════════════════════════════════════════════════════════════════════════════

def test_reset_cost_clears_everything():
    """reset_cost() 把所有计数归零"""
    _record_real_usage(prompt=50_000, completion=10_000)

    # 确认有值
    assert get_current_cost()["total_tokens"] > 0

    # 重置
    reset_cost()

    # 确认归零
    after = get_current_cost()
    assert after["prompt_tokens"] == 0
    assert after["completion_tokens"] == 0
    assert after["total_tokens"] == 0
    assert after["cost_yuan"] == 0.0
