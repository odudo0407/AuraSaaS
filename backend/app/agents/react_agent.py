"""
ReAct Agent — Think → Act → Observe → Think → ... → Answer.

Replaces the fixed 8-node LangGraph DAG with an autonomous loop where the LLM
decides which tools to call at each step based on what it has observed so far.

SSE event format is compatible with the existing frontend useAgentAnalysis.
"""

from __future__ import annotations

import datetime
import json
import time
import uuid

from app.agents.tool_schemas import TOOL_SCHEMAS, TOOL_MAP, execute_tool, PrivilegeEscalationError, get_tools_for_privilege, get_privilege_level, PRIVILEGE_LABELS
from app.agents.tools import save_agent_memory, search_agent_memory
from app.core.config import get_settings
from app.database import SessionLocal
from app.models.models import AgentTrace
from app.services.agent_forms import form_event_from_query
from app.services.deepseek_client import chat_with_tools, has_valid_api_key
from app.core.performance import track_performance, set_perf_context

settings = get_settings()
MAX_ITERATIONS = 12       # safety cap — avoid infinite loops
TOOL_RESULT_MAX_CHARS = 3000  # truncate long tool results to stay in context


SYSTEM_PROMPT = """你是 AuraSaaS 的 AI 经营分析助手，服务于一个咖啡与轻食连锁品牌的多门店运营团队。

## 你的能力

你可以通过调用工具来获取真实的经营数据，包括：
- 查询门店日报、详情、排行榜
- 检测经营异常（营收下滑、退单飙升、毛利恶化）
- 分析 SKU 销售趋势
- 查看外部环境因素（天气、节假日）
- 检索 SOP 知识库（退单处理、营销方案、差评回复、活动策划等）
- 预测营收趋势、环比对比
- 生成营销策略和文案
- 计算 ROI

## 工作方式

1. 先理解用户的问题，明确需要什么信息
2. 只调用必要的工具，一次获取一个维度的信息
3. 拿到工具结果后，判断信息是否足够回答问题：
   - 如果不够 → 继续调用下一个需要的工具
   - 如果够了 → 给出结构清晰的分析结论
4. 把多个工具的结果综合起来，不要独立复述每个工具

## 重要规则

- 不要重复调用同一个工具（除非参数不同）
- 如果用户只是打招呼或闲聊，直接回应，不要调用任何工具
- 如果用户问题涉及具体数据（营收、订单、异常等），必须先调用工具获取数据再回答，不能编造数字
- 工具返回的 data 字段中的内容才是真实数据，请引用具体数字
- 分析时要量化：涨幅/降幅百分比、具体金额、时间段对比
- 最后给出 1-3 条可执行的下一步建议

## 输出格式

你必须使用 Markdown 格式输出，让报告美观易读。具体规则：

- **标题**: 用 `##` 和 `###` 分层，不要用 `#`
- **加粗**: 关键数字和结论用 `**粗体**` 突出
- **表格**: 多组对比数据用表格呈现（如门店对比、SKU对比）
- **列表**: 建议和行动项用 `- ` 无序列表或 `1. ` 有序列表
- **引用**: 来自SOP的内容用 `>` 引用块
- **代码块**: JSON数据或示例用 ``` 包裹
- **金额**: 用 `¥1,234` 格式
- **分割线**: 章节之间用 `---` 分隔
- 严重问题需要加 🔴，良好表现加 🟢

输出风格：简洁中文，不废话，量化分析引用具体数字。"""


# ── helpers ────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    """Encode an SSE event as a JSON string."""
    return json.dumps(data, ensure_ascii=False)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def _trace_create(trace_id: str, query: str, store_id: int | None) -> None:
    db = SessionLocal()
    try:
        db.add(AgentTrace(
            trace_id=trace_id, user_query=query, store_id=store_id,
            status="running", steps_json="[]",
        ))
        db.commit()
    finally:
        db.close()


def _trace_finish(trace_id: str, steps: list[dict], final_answer: str, status: str = "completed") -> None:
    db = SessionLocal()
    try:
        trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
        if trace:
            trace.steps_json = json.dumps(steps, ensure_ascii=False)
            trace.final_answer = final_answer
            trace.status = status
            trace.updated_at = datetime.datetime.now()
            db.commit()
    finally:
        db.close()


def _tool_title(name: str) -> str:
    """Human-readable title for a tool name shown in the frontend pipeline."""
    labels = {
        "get_daily_summary": "📊 查询日报",
        "detect_anomalies": "🔍 异常检测",
        "analyze_sku_trends": "📈 SKU趋势",
        "check_external_factors": "🌦 外部环境",
        "search_knowledge_base": "📚 知识库检索",
        "get_store_detail": "🏪 门店详情",
        "list_all_stores": "🏢 门店列表",
        "forecast_metric": "🔮 趋势预测",
        "compare_periods": "📉 环比对比",
        "rank_stores": "🏆 门店排行",
        "calculate_roi": "💰 ROI计算",
        "search_products": "🔎 商品搜索",
        "generate_marketing_strategy": "🎯 策略生成",
        "generate_campaign_copy": "✍️ 文案生成",
        "create_anomaly_tasks": "📋 创建任务",
        "search_agent_memory": "🧠 记忆搜索",
        "save_agent_memory": "💾 保存记忆",
    }
    return labels.get(name, f"🔧 {name}")


def _demo_response(query: str) -> str:
    """Fallback response when no LLM API key is configured."""
    return f"""[演示模式] 请在 .env 中配置 DEEPSEEK_API_KEY 以启用完整的 AI Agent 功能。

当前查询："{query}"

在没有 LLM 的情况下，我无法自主决定调用哪些工具。配置 API Key 后，你将看到：
1. Agent 根据你的问题选择最合适的工具
2. 实时查看每个工具的调用和返回结果
3. 综合多轮数据给出分析结论

支持 OpenAI 兼容 API（DeepSeek / OpenAI / 其他兼容服务）。"""


# ── main ReAct loop ─────────────────────────────────────────────────────────

@track_performance
async def run_react_agent_stream(
    query: str,
    store_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    history: list[dict] | None = None,
):
    """Run the ReAct agent loop, yielding SSE events for the frontend.

    The agent loops:
      1. Send messages + tools to LLM
      2. If LLM returns tool_calls → execute each tool, feed results back
      3. If LLM returns plain text → that's the final answer
      4. Repeat until answer or MAX_ITERATIONS

    If `history` is provided (from previous turns in the same conversation),
    these messages are inserted between the system prompt and the new user query,
    allowing the agent to understand follow-up context like "可以，做吧".
    """
    trace_id = str(uuid.uuid4())
    _trace_create(trace_id, query, store_id)

    # ── RAG tracking ──
    _rag_queries = 0
    _rag_hits = 0

    # ── agent_start event ──
    yield _sse({
        "type": "agent_start", "trace_id": trace_id, "node": "agent",
        "title": "Agent 启动", "content": query, "done": False,
    })

    form_preview = form_event_from_query(query=query, store_id=store_id, history=history)
    if form_preview:
        content = form_preview.get("description", "")
        yield _sse({
            "type": "form_required",
            "trace_id": trace_id,
            "node": "agent_form",
            "title": form_preview.get("title", "经营操作表格"),
            "content": content,
            "form": form_preview,
            "done": True,
        })
        _trace_finish(trace_id, [{
            "node": "agent_form",
            "event": {"type": "form_required", "title": form_preview.get("title", "")},
            "input_summary": query[:180],
            "time": _now_iso(),
            "duration_ms": 0,
        }], content)
        yield _sse({"type": "end", "trace_id": trace_id, "node": "end", "done": True, "content": ""})
        return

    # ── build initial messages ──
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    context_parts = []
    if store_id:
        context_parts.append(f"当前选中门店ID：{store_id}")
    if start_date or end_date:
        context_parts.append(f"日期范围：{start_date or '不限'} ~ {end_date or '不限'}")
    if context_parts:
        messages.append({"role": "system", "content": "上下文信息\n" + "\n".join(context_parts)})

    # ── inject conversation history (multi-turn support) ──
    if history:
        for h in history:
            role = h.get("role")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": query})

    # ── inject past agent memory ──
    try:
        memories = search_agent_memory(query, store_id=store_id).get("data", [])
        if memories:
            past = "\n".join(
                f"- [{m.get('memory_type', '')}] {m.get('content', '')}"
                for m in memories[:5]
            )
            messages.insert(
                1,
                {"role": "system", "content": f"以下是你过去对相关问题的分析记录，请结合这些上下文理解用户的追问：\n{past}"},
            )
    except Exception:
        pass  # memory is best-effort, never block the main flow

    # ── ReAct loop ──
    trace_steps = []
    final_answer = ""
    has_api_key = has_valid_api_key()

    if not has_api_key:
        final_answer = _demo_response(query)
        yield _sse({
            "type": "final_answer", "trace_id": trace_id, "node": "report_generator",
            "title": "✅ 演示模式", "content": final_answer, "done": True,
        })
        _trace_finish(trace_id, trace_steps, final_answer)
        yield _sse({"type": "end", "trace_id": trace_id, "node": "end", "done": True, "content": ""})
        return

    current_privilege = get_privilege_level()
    active_tools = get_tools_for_privilege(int(current_privilege))

    for iteration in range(1, MAX_ITERATIONS + 1):
        round_start = time.perf_counter()

        # ── 1. Ask LLM to think and decide ──
        response = chat_with_tools(
            messages=messages,
            tools=active_tools,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1200,
        )

        if response is None:
            final_answer = _demo_response(query)
            yield _sse({
                "type": "final_answer", "trace_id": trace_id, "node": "report_generator",
                "title": "✅ 演示模式", "content": final_answer, "done": True,
            })
            break

        content = response.get("content") or ""
        tool_calls = response.get("tool_calls")

        # ── 2a. No tool calls → LLM is giving the final answer ──
        if not tool_calls:
            final_answer = content
            yield _sse({
                "type": "final_answer", "trace_id": trace_id, "node": "report_generator",
                "title": "✅ 分析结果", "content": final_answer, "done": True,
            })
            trace_steps.append({
                "node": "final_answer", "event": {"type": "final_answer"},
                "input_summary": query[:180],
                "time": _now_iso(),
                "duration_ms": round((time.perf_counter() - round_start) * 1000, 2),
            })
            break

        # ── 2b. LLM wants to call tools ──
        # Record the assistant message (with tool_calls) for conversation history
        assistant_msg = {
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
                for tc in tool_calls
            ],
        }
        messages.append(assistant_msg)

        # Execute each tool call
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                tool_args = {}

            args_summary = json.dumps(tool_args, ensure_ascii=False)

            # SSE: tool call starting
            yield _sse({
                "type": "tool_result", "trace_id": trace_id, "node": tool_name,
                "title": _tool_title(tool_name),
                "content": f"参数: {args_summary}",
                "done": False,
            })

            # Execute (with privilege gating)
            t0 = time.perf_counter()
            try:
                result_str = execute_tool(tool_name, tool_args)
            except PrivilegeEscalationError as esc:
                result_str = json.dumps({
                    "success": False,
                    "error": str(esc),
                    "requires_approval": True,
                    "hint": "该操作需要提升权限等级，请通过人工审批流程（LangGraph HITL）执行。"
                }, ensure_ascii=False)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            # Track RAG queries
            if tool_name in ("search_knowledge_base", "retrieve_sop_knowledge"):
                _rag_queries += 1
                try:
                    data = json.loads(result_str)
                    if data.get("data") and len(data["data"]) > 0:
                        _rag_hits += 1
                except Exception:
                    pass

            # Truncate if too long
            result_display = result_str[:TOOL_RESULT_MAX_CHARS]
            if len(result_str) > TOOL_RESULT_MAX_CHARS:
                result_display += "\n...(内容过长，已截断)"

            # SSE: tool result
            yield _sse({
                "type": "tool_result", "trace_id": trace_id, "node": tool_name,
                "title": _tool_title(tool_name),
                "content": result_display,
                "duration_ms": duration_ms,
                "done": False,
            })

            # Add tool result to conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_str[:4000],  # keep context window manageable
            })

            trace_steps.append({
                "node": tool_name,
                "event": {"type": "tool_result", "title": _tool_title(tool_name)},
                "input_summary": args_summary[:180],
                "time": _now_iso(),
                "duration_ms": duration_ms,
            })

    else:
        # ── Loop exhausted (MAX_ITERATIONS reached) ──
        # Force the LLM to summarize what it knows so far
        messages.append({
            "role": "user",
            "content": "你已经调用了多次工具。请根据已获取的所有数据，直接给出最终分析结论，不要再调用工具。",
        })
        force_resp = chat_with_tools(
            messages=messages, tools=None,  # no tools → must answer in text
            temperature=0.3, max_tokens=1000,
        )
        if force_resp:
            final_answer = force_resp.get("content", "") or "分析已超时，请简化问题后重试。"
        else:
            final_answer = "分析已超时，请简化问题后重试。"

        yield _sse({
            "type": "final_answer", "trace_id": trace_id, "node": "report_generator",
            "title": "⚠️ 达到最大轮次", "content": final_answer, "done": True,
        })

    # ── auto-save to memory ──
    if final_answer and has_api_key:
        try:
            summary = final_answer[:500]
            save_agent_memory(store_id, "diagnosis", summary)
        except Exception:
            pass

    # ── persist trace & end ──
    _trace_finish(trace_id, trace_steps, final_answer)

    # ── performance context (RAG hit rate for decorator) ──
    rag_hit_rate = (_rag_hits / _rag_queries) if _rag_queries > 0 else None
    set_perf_context(rag_hit_rate=rag_hit_rate)

    yield _sse({"type": "end", "trace_id": trace_id, "node": "end", "done": True, "content": ""})
