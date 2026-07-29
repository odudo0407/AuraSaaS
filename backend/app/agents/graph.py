"""LangGraph multi-agent workflow with RAG, HITL, SSE and trace persistence."""

from __future__ import annotations

import logging
import asyncio
import datetime
import json
import os
import queue as thread_queue
import threading
import time
import uuid
from typing import TypedDict
try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired
from langgraph.graph import StateGraph, END
from openai import OpenAI
from app.agents.tools import (
    add_product,
    add_staff_member,
    add_store_metric,
    tool_result,
    analyze_sku_trends,
    check_external_context,
    compare_periods,
    create_anomaly_tasks,
    detect_business_anomalies,
    evaluate_strategy_risk,
    fetch_cost_anomalies,
    forecast_metric,
    generate_campaign_copy,
    generate_marketing_strategy,
    rank_stores,
    save_agent_memory,
    search_agent_memory,
    search_products,
    get_store_detail,
    get_daily_summary,
    calculate_roi,
    list_all_stores,
)
from app.core.config import get_settings
from app.core.performance import track_performance, set_perf_context
from app.database import SessionLocal
from app.models.models import AgentApproval, AgentMemory, AgentTrace
from app.agents.nodes.data_analysis import run_data_analyst_node
from app.services.rag_service import query_knowledge
from app.services.tenant_knowledge_service import query_tenant_knowledge
from app.services.code_rag_service import query_codebase
from app.services.deepseek_client import chat as llm_chat, has_valid_api_key


class AgentState(TypedDict):
    user_query: str
    query: str
    trace_id: str
    store_id: NotRequired[int | None]
    date_range: NotRequired[dict]
    intent: NotRequired[str]
    active_skill: NotRequired[str | None]
    skill_knowledge_sources: NotRequired[list[str]]
    metrics: NotRequired[dict]
    anomalies: NotRequired[list]
    external_context: str
    retrieved_docs: str
    rag_references: NotRequired[list]
    diagnosis: str
    data_analysis: str
    strategy: str
    risk_assessment: NotRequired[dict]
    approval_status: str
    approval_comment: str
    approval_id: NotRequired[int | None]
    hitl_proposal: str
    hitl_approved: bool
    campaign_copy: str
    copy: str
    execution_result: NotRequired[dict]
    final_report: str
    messages: list
    current_node: str


settings = get_settings()
logger = logging.getLogger(__name__)


def _append_message(state: AgentState, node: str, content: str) -> list:
    return [*state.get("messages", []), {"node": node, "content": content, "time": datetime.datetime.now().isoformat()}]


def intent_router_node(state: AgentState) -> dict:
    """Node 0: Skill-aware intent classification.

    1. Check SkillRegistry for a matching Skill (keyword-based, fast).
    2. If matched → set active_skill + skill_knowledge_sources, skip LLM classification.
    3. If no match → fall through to LLM-based intent classification as before.
    """

    query = state["query"]

    # ── Skill matching (keyword-based, runs before LLM) ──────────
    from app.skills.registry import SkillRegistry

    matched = SkillRegistry.match_intent(query)
    if matched is not None:
        logger.info("Skill matched: %s for query=%r", matched.name, query[:80])
        return {
            "intent": "skill:" + matched.name,
            "active_skill": matched.name,
            "skill_knowledge_sources": matched.knowledge_sources,
            "tools_needed": matched.required_tools,
            "current_node": "intent_router",
            "messages": _append_message(
                state, "intent_router",
                f"skill: {matched.name} | {matched.description}",
            ),
        }

    system = """You are AuraSaaS's intent router. Classify the user request and return JSON only.

Return this schema:
{
  "intent": "general_chat|data_query|anomaly_diagnosis|knowledge_query|marketing_plan|data_management|report_generation|store_operation|financial_analysis|customer_insight|competitor_analysis",
  "tools_needed": ["tool_name"],
  "reasoning": "brief reason"
}

Intent rules:
- general_chat: greeting, casual chat, or no business data needed.
- data_query: asks for revenue, orders, rankings, store details, products, or daily summaries.
- anomaly_diagnosis: asks why a metric dropped/spiked or asks to diagnose anomalies.
- knowledge_query: asks for SOP, process, policy, or how to handle an operational case.
- marketing_plan: asks for campaign, promotion, copywriting, or strategy.
- data_management: asks to add, edit, delete, or import product/staff/metric data.
- report_generation: asks for report, summary, weekly report, or business review.
- store_operation: asks about staffing, scheduling, store opening/closing, equipment, or daily operations.
- financial_analysis: asks about cost analysis, profit margins, ROI calculation, budget planning, or financial health.
- customer_insight: asks about customer segments, repurchase rates, satisfaction, membership, or customer behavior.
- competitor_analysis: asks about market competition, competitor comparison, pricing strategy, or market positioning.

Available tools include get_daily_summary, get_store_detail, search_products, rank_stores, forecast_metric,
compare_periods, calculate_roi, list_all_stores, retrieve_knowledge, detect_anomalies, add_product,
add_staff, and add_metric. Choose only 1-3 relevant tools. Use an empty list for general_chat."""
    if has_valid_api_key():
        try:
            raw = llm_chat(
                system,
                f"用户输入: {query}",
                "",  # no fallback — if LLM fails, fall through to keyword
                temperature=0.1,
                max_tokens=300,
            )
            if raw:
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                    if raw.endswith("```"):
                        raw = raw[:-3]
                parsed = json.loads(raw.strip())
            else:
                raise ValueError("empty response")
        except (json.JSONDecodeError, ValueError, Exception):
            parsed = _keyword_intent(query)
    else:
        parsed = _keyword_intent(query)

    intent = parsed.get("intent", "general_chat")
    tools = parsed.get("tools_needed", [])
    reasoning = parsed.get("reasoning", "")

    return {
        "intent": intent,
        "tools_needed": tools,
        "current_node": "intent_router",
        "messages": _append_message(state, "intent_router", f"intent: {intent} | tools: {', '.join(tools) or 'none'} | {reasoning}"),
    }


def _keyword_intent(query: str) -> dict:
    """Fallback keyword-based intent classification when LLM is unavailable."""
    q = query.lower()
    if any(w in q for w in ["添加", "增加", "新增", "录入", "删除", "修改", "导入"]):
        return {"intent": "data_management", "tools_needed": [], "reasoning": "keyword:data_mgmt"}
    if any(w in q for w in ["报告", "战报", "总结", "报表"]):
        return {"intent": "report_generation", "tools_needed": [], "reasoning": "keyword:report"}
    if any(w in q for w in ["营销", "活动", "文案", "推广", "方案"]):
        return {"intent": "marketing_plan", "tools_needed": [], "reasoning": "keyword:marketing"}
    if any(w in q for w in ["下降", "异常", "退单", "退款", "毛利", "为什么", "飙升"]):
        return {"intent": "anomaly_diagnosis", "tools_needed": ["detect_anomalies", "compare_periods"], "reasoning": "keyword:anomaly"}
    if any(w in q for w in ["sop", "知识", "流程", "怎么处理", "规范"]):
        return {"intent": "knowledge_query", "tools_needed": ["retrieve_knowledge"], "reasoning": "keyword:knowledge"}
    if any(w in q for w in ["排行", "排名", "门店", "详情", "日报", "搜索", "商品", "营收", "订单", "概况"]):
        return {"intent": "data_query", "tools_needed": [], "reasoning": "keyword:data"}
    if any(w in q for w in ["排班", "打卡", "考勤", "开店", "关店", "设备", "库存", "盘点"]):
        return {"intent": "store_operation", "tools_needed": ["get_store_detail"], "reasoning": "keyword:store_op"}
    if any(w in q for w in ["成本", "利润", "预算", "roi", "投资回报", "回报率"]):
        return {"intent": "financial_analysis", "tools_needed": ["calculate_roi", "compare_periods"], "reasoning": "keyword:finance"}
    if any(w in q for w in ["客户", "复购", "回头客", "会员", "满意度", "客群", "消费习惯"]):
        return {"intent": "customer_insight", "tools_needed": ["search_agent_memory"], "reasoning": "keyword:customer"}
    if any(w in q for w in ["竞品", "竞争对手", "同行", "市场份额", "定价", "对比同行"]):
        return {"intent": "competitor_analysis", "tools_needed": [], "reasoning": "keyword:competitor"}
    return {"intent": "general_chat", "tools_needed": [], "reasoning": "keyword:chat"}


def data_analyst_node(state: AgentState) -> dict:
    """Node 1: Analyze metrics, anomalies, forecasts, comparisons, and auto-create tasks."""

    return run_data_analyst_node(state)


def fetch_external_context_node(state: AgentState) -> dict:
    """Node 2: Collect external factors."""

    store_id = state.get("store_id")
    context = check_external_context(store_id=store_id)
    return {
        "external_context": context,
        "current_node": "fetch_context",
        "messages": _append_message(state, "fetch_context", context),
    }



CODE_QUERY_KEYWORDS = (
    "\u4ee3\u7801", "\u51fd\u6570", "\u7c7b", "bug", "\u62a5\u9519", "\u5b9e\u73b0", "\u903b\u8f91", "\u600e\u4e48\u5199\u7684",
)
SOP_QUERY_KEYWORDS = ("sop", "\u6d41\u7a0b", "\u89c4\u8303", "\u5236\u5ea6", "\u600e\u4e48\u64cd\u4f5c")
CODE_FILE_PATTERNS = (".py", ".js", ".java")


def _is_code_query(query: str) -> bool:
    lowered = query.lower()
    return any(keyword.lower() in lowered for keyword in CODE_QUERY_KEYWORDS) or any(pattern in lowered for pattern in CODE_FILE_PATTERNS)


def _is_sop_query(query: str) -> bool:
    lowered = query.lower()
    return any(keyword.lower() in lowered for keyword in SOP_QUERY_KEYWORDS)


def _format_code_results(results: list[dict]) -> str:
    if not results:
        return "\u672a\u627e\u5230\u76f8\u5173\u4ee3\u7801\uff0c\u8bf7\u68c0\u67e5\u6587\u4ef6\u662f\u5426\u5df2\u4e0a\u4f20\n"

    blocks = []
    for idx, item in enumerate(results, start=1):
        metadata = item.get("metadata") or {}
        file_name = metadata.get("file_name", "unknown")
        symbol_name = metadata.get("symbol_name") or metadata.get("signature") or "module"
        start_line = metadata.get("start_line", "?")
        end_line = metadata.get("end_line", "?")
        language = metadata.get("language", "")
        content = item.get("content", "")
        blocks.append(
            f"[\u4ee3\u7801\u7247\u6bb5 {idx}]\n"
            f"\u6587\u4ef6\uff1a{file_name}\n"
            f"\u51fd\u6570/\u7c7b\uff1a{symbol_name}\n"
            f"\u884c\u53f7\uff1a{start_line}-{end_line}\n"
            f"\u4ee3\u7801\uff1a\n```{language}\n{content}\n```"
        )
    return "\n\n".join(blocks)


def _format_sop_results(results: list[dict]) -> str:
    if not results:
        return "No related SOP documents were found."

    return "\n".join(
        f"- {doc.get('title', 'Untitled')} ({doc.get('source', '')}): {doc.get('snippet', '')[:500]}"
        for doc in results
    )

def rag_strategist_node(state: AgentState) -> dict:
    """Node 3: Retrieve SOP/code context and generate grounded guidance.

    When a Skill is active, its knowledge_sources declare which ChromaDB
    collections to query — each Skill gets isolated RAG access.
    """

    query = state["query"]
    query_with_analysis = f"{query} {state.get('data_analysis', '')}".strip()
    use_code_rag = _is_code_query(query)
    use_sop_rag = _is_sop_query(query) or not use_code_rag
    skill_sources = state.get("skill_knowledge_sources") or []

    code_results: list[dict] = []
    sop_docs: list[dict] = []
    tenant_docs: list[dict] = []

    if use_code_rag:
        try:
            code_results = query_codebase(query=query, top_k=5)
        except Exception:
            logger.exception("Code RAG lookup failed for query=%r", query)
            code_results = []

    if use_sop_rag:
        tenant_id = state.get("store_id")
        if tenant_id:
            try:
                tenant_docs = query_tenant_knowledge(query_with_analysis, tenant_id=tenant_id, top_k=3)
            except Exception:
                logger.exception("Tenant knowledge lookup failed tenant_id=%s query=%r", tenant_id, query)
                tenant_docs = []

        # Skill-specific knowledge sources get priority
        if skill_sources:
            skill_docs: list[dict] = []
            for collection in skill_sources:
                try:
                    skill_docs.extend(query_knowledge(query_with_analysis, top_k=3, collection=collection))
                except Exception:
                    logger.exception("Skill RAG lookup failed collection=%s", collection)
            sop_docs = skill_docs + tenant_docs
        else:
            sop_docs = tenant_docs + query_knowledge(query_with_analysis, top_k=2)

    logger.info(
        "rag_strategist retrieval mode code=%s sop=%s code_hits=%d tenant_hits=%d sop_hits=%d query=%r",
        use_code_rag,
        use_sop_rag,
        len(code_results),
        len(tenant_docs),
        len(sop_docs),
        query,
    )

    code_context = _format_code_results(code_results) if use_code_rag else ""
    sop_context = _format_sop_results(sop_docs) if use_sop_rag else ""
    context_blocks = []
    if use_code_rag:
        context_blocks.append(
            "CODE_CONTEXT\n"
            "You are a full-stack development assistant. The following snippets were retrieved from the codebase. "
            "Answer using these snippets. If no code was found, answer exactly: \u672a\u627e\u5230\u76f8\u5173\u4ee3\u7801\uff0c\u8bf7\u68c0\u67e5\u6587\u4ef6\u662f\u5426\u5df2\u4e0a\u4f20\n"
            "When code is found, cite file names and line ranges in the answer.\n"
            f"{code_context}"
        )
    if use_sop_rag:
        context_blocks.append(f"SOP_CONTEXT\n{sop_context}")

    retrieved_context = "\n\n".join(context_blocks) or "No related context was found."
    references = [
        {
            "title": doc.get("title", "Untitled"),
            "source": doc.get("source", ""),
            "snippet": doc.get("snippet", "")[:220],
            "score": doc.get("score"),
            "type": "sop",
        }
        for doc in sop_docs
    ]
    references.extend(
        {
            "title": (item.get("metadata") or {}).get("symbol_name", "code"),
            "source": (item.get("metadata") or {}).get("file_name", ""),
            "snippet": item.get("content", "")[:220],
            "score": item.get("score"),
            "type": "code",
            "metadata": item.get("metadata") or {},
        }
        for item in code_results
    )

    fallback = "\u672a\u627e\u5230\u76f8\u5173\u4ee3\u7801\uff0c\u8bf7\u68c0\u67e5\u6587\u4ef6\u662f\u5426\u5df2\u4e0a\u4f20\n" if use_code_rag and not code_results else "Generated an answer from retrieved context."
    strategy = llm_chat(
        "You are AuraSaaS's full-stack development assistant and business strategy advisor. Use CODE_CONTEXT and SOP_CONTEXT when provided. "
        "Ground the answer in the retrieved context. For code questions, cite file names and line ranges. If context is missing, say so clearly.",
        f"User question: {query}\nDiagnosis: {state.get('data_analysis', '')}\n\n{retrieved_context}\n\nAnswer using the context above.",
        fallback,
        temperature=0.3,
        max_tokens=900,
    )
    risk_result = evaluate_strategy_risk({"budget": 2000})
    return {
        "strategy": strategy,
        "retrieved_docs": retrieved_context,
        "rag_references": references,
        "risk_assessment": risk_result.get("data", {}),
        "current_node": "rag_strategist",
        "messages": _append_message(state, "rag_strategist", strategy),
    }

def risk_controller_node(state: AgentState) -> dict:
    """Node 4: Mark approval requirement."""
    risk = state.get("risk_assessment") or {"risk_level": "medium", "requires_approval": True}
    summary = f"风险等级：{risk.get('risk_level', 'medium')}；是否需要审批：{risk.get('requires_approval', True)}"
    return {
        "risk_assessment": risk,
        "current_node": "risk_controller",
        "messages": _append_message(state, "risk_controller", summary),
    }


def hitl_node(state: AgentState) -> dict:
    """Node 5: Human-in-the-loop approval task creation."""

    proposal = llm_chat(
        "根据策略方案生成一个简洁审批提案，包含策略摘要、预估成本、预期收益，100字以内。",
        f"策略方案:\n{state['strategy']}",
        "审批提案：建议上线低预算定向券和高毛利套餐，预估成本 2000 元内，目标提升订单 8%-15%，需店长确认后执行。",
        temperature=0.3,
        max_tokens=220,
    )

    db = SessionLocal()
    approval_id = None
    try:
        approval = AgentApproval(
            session_id=f"session_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            trace_id=state["trace_id"],
            node_name="human_approval",
            proposal=proposal,
            estimated_cost=2000,
            status="pending",
        )
        db.add(approval)
        db.commit()
        approval_id = approval.id
    finally:
        db.close()

    content = json.dumps({"approval_id": approval_id, "proposal": proposal}, ensure_ascii=False)
    return {
        "hitl_proposal": proposal,
        "approval_status": "pending",
        "approval_id": approval_id,
        "hitl_approved": False,
        "current_node": "human_approval",
        "messages": _append_message(state, "human_approval", content),
    }


def copywriter_node(state: AgentState) -> dict:
    """Node 6: Generate campaign copy."""

    strategy_payload = {"name": "AI 经营改善活动", "target": "提升订单并控制毛利风险", "budget": 2000, "store_id": state.get("store_id") or 1}
    copy_payload = generate_campaign_copy(strategy_payload, tone="friendly").get("data", {})
    fallback = json.dumps(copy_payload, ensure_ascii=False, indent=2)
    copy = llm_chat(
        "你是门店营销文案专家，根据策略生成短信、小程序 Push、公众号、外卖平台标题、员工话术，输出 JSON。",
        f"策略:\n{state['strategy']}\n\n问题: {state['query']}",
        fallback,
        temperature=0.6,
        max_tokens=800,
    )
    return {
        "campaign_copy": copy,
        "copy": copy,
        "current_node": "copywriter",
        "messages": _append_message(state, "copywriter", copy),
    }


def report_generator_node(state: AgentState) -> dict:
    """Node 7: Final report with quantified insights and actionable next steps."""

    references = "\n".join(
        f"- {doc.get('title', 'Untitled')} ({doc.get('source', '')})"
        for doc in state.get("rag_references", [])
    ) or state.get("retrieved_docs", "")[:1200]

    metrics = state.get("metrics", {})
    forecast_block = ""
    if metrics.get("forecast"):
        f = metrics["forecast"]
        forecast_block = (
            f"\n## \u8425\u6536\u9884\u6d4b\n"
            f"\u5386\u53f2\u5747\u503c\uff1a{f.get('historical_avg', 'N/A')} \u5143\n"
            f"\u8fd1\u671f\u5747\u503c\uff1a{f.get('recent_avg', 'N/A')} \u5143\n"
            f"\u8d8b\u52bf\uff1a{f.get('trend_pct', 0):.1f}%\n"
            f"\u672a\u67657\u5929\u9884\u6d4b\uff1a{json.dumps(f.get('forecast', []), ensure_ascii=False)}\n"
        )

    comparison_block = ""
    if metrics.get("comparison"):
        c = metrics["comparison"]
        comparison_block = (
            f"\n## \u5468\u671f\u5bf9\u6bd4\uff08\u672c\u5468 vs \u4e0a\u5468\uff09\n"
            f"\u672c\u5468\uff1a{c.get('current_value', 'N/A')} | \u4e0a\u5468\uff1a{c.get('previous_value', 'N/A')}\n"
            f"\u53d8\u5316\uff1a{c.get('change_pct', 0):+.1f}% ({c.get('direction', 'flat')})\n"
        )

    ranking_block = ""
    if metrics.get("ranking"):
        ranking_block = "\n## \u95e8\u5e97\u6392\u884c TOP3\n" + "\n".join(
            f"{r.get('rank')}. {r.get('name')} ({r.get('city')}): {r.get('value')} \u5143"
            for r in metrics["ranking"]
        )

    tasks_block = ""
    tasks = metrics.get("tasks_created") or {}
    if tasks.get("tasks_created", 0) > 0:
        tasks_block = (
            f"\n## \u81ea\u52a8\u544a\u8b66\n"
            f"\u5df2\u751f\u6210 {tasks['tasks_created']} \u6761\u5f85\u5904\u7406\u4efb\u52a1\uff0c\u8bf7\u524d\u5f80 Dashboard \u67e5\u770b\u3002\n"
        )

    report = (
        "# AuraSaaS \u7ecf\u8425\u8bca\u65ad\u62a5\u544a\n\n"
        f"## \u7528\u6237\u95ee\u9898\n{state['query']}\n\n"
        f"## \u6570\u636e\u8bca\u65ad\n{state.get('diagnosis', '')}\n"
        f"## \u5916\u90e8\u56e0\u7d20\n{state.get('external_context', '')}\n"
        f"## SOP \u5f15\u7528\n{references}\n"
        f"{forecast_block}"
        f"{comparison_block}"
        f"{ranking_block}"
        f"{tasks_block}"
        f"## \u7b56\u7565\u5efa\u8bae\n{state.get('strategy', '')}\n\n"
        f"## \u98ce\u9669\u4e0e\u5ba1\u6279\n{json.dumps(state.get('risk_assessment', {}), ensure_ascii=False)}\n\n"
        f"## \u53ef\u6267\u884c\u4e0b\u4e00\u6b65\n"
        f"1. \u5ba1\u6279\u901a\u8fc7\u540e\uff0c\u7cfb\u7edf\u5c06\u81ea\u52a8\u521b\u5efa\u8425\u9500\u6d3b\u52a8\u8349\u7a3f\n"
        f"2. \u5c06\u7b56\u7565\u4efb\u52a1\u5206\u914d\u7ed9\u5bf9\u5e94\u95e8\u5e97\u5e97\u957f\n"
        f"3. \u6bcf24\u5c0f\u65f6\u590d\u76d8\u8ba2\u5355\u3001\u9000\u5355\u548c\u6bdb\u5229\u8868\u73b0\n"
        f"4. 3\u5929\u540e\u590d\u8bca\uff0c\u5bf9\u6bd4\u7b56\u7565\u6548\u679c\u6570\u636e\n\n"
        f"## \u8425\u9500\u6587\u6848\n{state.get('campaign_copy', '')}\n"
    )

    return {
        "final_report": report,
        "current_node": "report_generator",
        "messages": _append_message(state, "report_generator", report),
    }

def data_editor_node(state: AgentState) -> dict:
    """Node for data CRUD: parse natural language, call tools, return result."""

    query = state["query"]
    store_id = state.get("store_id") or 1
    system = """You are a data-entry assistant. Extract structured JSON from the user input.
Supported actions: add_product, add_staff, add_store_metric.

Return one of these shapes only:
{"action":"add_product","data":{"sku_name":"...","category":"...","price":0,"cost":0,"store_id":1}}
{"action":"add_staff","data":{"name":"...","phone":"...","role":"...","store_id":1}}
{"action":"add_store_metric","data":{"store_id":1,"date":"YYYY-MM-DD","revenue":0,"order_count":0}}

Return JSON only. Do not include prose."""

    result_json = llm_chat(
        system,
        f"User input: {query}\nStore ID: {store_id}",
        json.dumps({"action": "unknown", "data": {}, "message": "Unable to parse data-entry request."}),
        temperature=0.1,
        max_tokens=500,
    )

    try:
        parsed = json.loads(result_json)
    except json.JSONDecodeError:
        parsed = {"action": "unknown", "data": {}, "message": result_json[:200]}

    action = parsed.get("action", "unknown")
    data = parsed.get("data", {})

    result = tool_result(False, error="Unsupported data operation")
    if action == "add_product":
        result = add_product(data)
    elif action == "add_staff":
        result = add_staff_member(data)
    elif action == "add_store_metric":
        result = add_store_metric(data)

    if result.get("success", False):
        summary = f"Completed {action}: {json.dumps(result.get('data', {}), ensure_ascii=False)}"
    else:
        summary = f"Operation failed: {result.get('error', 'unknown error')}"

    return {
        "current_node": "data_editor",
        "final_report": summary,
        "messages": _append_message(state, "data_editor", summary),
    }


def general_chat_node(state: AgentState) -> dict:
    """Node for general conversation: direct LLM answer without tools."""

    query = state["query"]
    answer = llm_chat(
        "You are AuraSaaS's AI operations assistant. Answer friendly and concise Chinese when possible.",
        query,
        "你好，我是 AuraSaaS 的 AI 经营助手，可以帮助分析门店数据、诊断异常、制定营销策略、查询 SOP 知识库。",
        temperature=0.7,
        max_tokens=400,
    )
    return {
        "final_report": answer,
        "current_node": "general_chat",
        "messages": _append_message(state, "general_chat", answer),
    }


def skill_executor_node(state: AgentState) -> dict:
    """Node: Execute the active Skill's workflow and return its output.

    Looks up the Skill from SkillRegistry by ``active_skill`` name,
    then calls the Skill's ``run(state)`` entry point.
    If no active skill or skill not found, falls through to general_chat.
    """
    skill_name = state.get("active_skill")
    if not skill_name:
        return {
            "final_report": "No active skill.",
            "current_node": "skill_executor",
            "messages": _append_message(state, "skill_executor", "No active skill"),
        }

    from app.skills.registry import SkillRegistry

    skill = SkillRegistry.get(skill_name)
    if skill is None:
        logger.warning("Skill not found: %s", skill_name)
        return {
            "final_report": f"Skill '{skill_name}' not registered.",
            "current_node": "skill_executor",
            "messages": _append_message(state, "skill_executor", f"Skill not found: {skill_name}"),
        }

    logger.info("Executing skill: %s", skill_name)
    try:
        # Import the skill module and call its run() entry point
        import importlib
        module = importlib.import_module(f"app.skills.{skill_name}")
        return module.run(state)
    except Exception:
        logger.exception("Skill execution failed: %s", skill_name)
        return {
            "final_report": f"Skill '{skill_name}' execution failed.",
            "current_node": "skill_executor",
            "messages": _append_message(state, "skill_executor", f"Skill failed: {skill_name}"),
        }


def build_graph():
    """Build the LangGraph StateGraph with conditional routing based on intent."""

    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("skill_executor", skill_executor_node)
    graph.add_node("data_analyst", data_analyst_node)
    graph.add_node("fetch_context", fetch_external_context_node)
    graph.add_node("rag_strategist", rag_strategist_node)
    graph.add_node("risk_controller", risk_controller_node)
    graph.add_node("human_approval", hitl_node)
    graph.add_node("data_editor", data_editor_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("report_generator", report_generator_node)

    graph.set_entry_point("intent_router")

    def route_after_intent(state: AgentState) -> str:
        """Route based on intent — skills first, then standard routing."""
        intent = state.get("intent") or ""
        if intent.startswith("skill:"):
            return "skill_executor"
        if intent == "knowledge_query":
            return "rag_strategist"
        if intent == "data_management":
            return "data_editor"
        if intent == "general_chat":
            return "general_chat"
        return "data_analyst"

    def route_after_data(state: AgentState) -> str:
        """dashboard_query skips to report; anomaly/marketing/report continue full pipeline."""
        return "report_generator" if state.get("intent") == "dashboard_query" else "fetch_context"

    def route_after_rag(state: AgentState) -> str:
        """knowledge_query done after RAG; others need risk review."""
        return "report_generator" if state.get("intent") == "knowledge_query" else "risk_controller"

    def route_after_risk(state: AgentState) -> str:
        """Lightweight intents skip HITL approval."""
        if state.get("intent") in ("knowledge_query", "dashboard_query"):
            return "report_generator"
        return "human_approval"

    graph.add_conditional_edges("intent_router", route_after_intent, {
        "skill_executor": "skill_executor",
        "data_analyst": "data_analyst",
        "data_editor": "data_editor",
        "rag_strategist": "rag_strategist",
        "general_chat": "general_chat",
    })
    graph.add_conditional_edges("data_analyst", route_after_data, {
        "fetch_context": "fetch_context",
        "report_generator": "report_generator",
    })
    graph.add_edge("fetch_context", "rag_strategist")
    graph.add_conditional_edges("rag_strategist", route_after_rag, {
        "risk_controller": "risk_controller",
        "report_generator": "report_generator",
    })
    graph.add_conditional_edges("risk_controller", route_after_risk, {
        "human_approval": "human_approval",
        "report_generator": "report_generator",
    })
    # Phase 1 stops here — caller persists state and yields approval_required event
    graph.add_edge("skill_executor", END)
    graph.add_edge("human_approval", END)
    graph.add_edge("data_editor", END)
    graph.add_edge("general_chat", END)
    graph.add_edge("report_generator", END)
    return graph.compile()


def build_post_approval_graph():
    """Build Phase 2 graph: runs after human approval, from saved state.

    copywriter -> report_generator -> END.
    Called by ``resume_agent_stream`` after the user approves the HITL proposal.
    """
    graph = StateGraph(AgentState)
    graph.add_node("copywriter", copywriter_node)
    graph.add_node("report_generator", report_generator_node)
    graph.set_entry_point("copywriter")
    graph.add_edge("copywriter", "report_generator")
    graph.add_edge("report_generator", END)
    return graph.compile()


def _save_graph_state(trace_id: str, state: dict) -> None:
    """Persist intermediate AgentState to AgentTrace for later resume."""
    db = SessionLocal()
    try:
        trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
        if trace:
            serializable: dict = {}
            for k, v in state.items():
                if k == "messages":
                    serializable[k] = v  # list[dict] is JSON-serializable
                else:
                    try:
                        json.dumps(v, ensure_ascii=False)
                        serializable[k] = v
                    except (TypeError, ValueError):
                        serializable[k] = str(v)
            trace.graph_state = json.dumps(serializable, ensure_ascii=False)
            trace.status = "awaiting_approval"
            db.commit()
    finally:
        db.close()


def _load_graph_state(trace_id: str) -> dict:
    """Load saved intermediate AgentState from AgentTrace."""
    db = SessionLocal()
    try:
        trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
        if trace and trace.graph_state:
            return json.loads(trace.graph_state)
        return {}
    finally:
        db.close()


def _create_trace(trace_id: str, query: str, store_id: int | None):
    db = SessionLocal()
    try:
        trace = AgentTrace(trace_id=trace_id, user_query=query, store_id=store_id, status="running", steps_json="[]")
        db.add(trace)
        db.commit()
    finally:
        db.close()


def _finish_trace(trace_id: str, steps: list[dict], final_answer: str, status: str = "completed"):
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


def _sse(data: dict) -> str:
    """Return JSON string — EventSourceResponse adds the 'data:' prefix automatically."""
    return json.dumps(data, ensure_ascii=False)


@track_performance
async def run_agent_stream(query: str, store_id: int | None = None, start_date: str | None = None, end_date: str | None = None):
    """Yield SSE events as the graph executes each node — true streaming via async queue."""

    # RAG hit-rate tracking
    _rag_queries = 0
    _rag_hits = 0

    trace_id = str(uuid.uuid4())
    _create_trace(trace_id, query, store_id)
    yield _sse({"type": "agent_start", "trace_id": trace_id, "node": "agent", "title": "Agent \u542f\u52a8", "content": query, "done": False})

    app_graph = build_graph()
    initial_state: AgentState = {
        "user_query": query,
        "query": query,
        "trace_id": trace_id,
        "store_id": store_id,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "intent": "",
        "metrics": {},
        "anomalies": [],
        "external_context": "",
        "retrieved_docs": "",
        "rag_references": [],
        "diagnosis": "",
        "data_analysis": "",
        "strategy": "",
        "risk_assessment": {},
        "approval_status": "",
        "approval_comment": "",
        "approval_id": None,
        "hitl_proposal": "",
        "hitl_approved": False,
        "campaign_copy": "",
        "copy": "",
        "execution_result": {},
        "final_report": "",
        "messages": [],
        "current_node": "",
    }

    queue = thread_queue.Queue()

    def _run_graph():
        """Run LangGraph stream in a thread, pushing each node result to the queue."""
        try:
            for output in app_graph.stream(initial_state):
                for node_name, node_output in output.items():
                    queue.put((node_name, node_output))
        except Exception as exc:
            queue.put(("__error__", {"error": str(exc)}))
        finally:
            queue.put(None)

    thread = threading.Thread(target=_run_graph, daemon=True)
    thread.start()

    trace_steps = []
    final_state = initial_state
    hit_approval_gate = False

    try:
        while True:
            item = await asyncio.to_thread(queue.get)
            if item is None:
                break

            if isinstance(item, tuple) and item[0] == "__error__":
                error_msg = item[1].get("error", "Unknown error")
                _finish_trace(trace_id, trace_steps, str(error_msg), status="failed")
                yield _sse({"type": "error", "trace_id": trace_id, "node": "error", "done": True, "content": error_msg})
                thread.join(timeout=5)
                return

            node_name, node_output = item
            if not isinstance(node_output, dict):
                node_output = {}
            final_state = {**final_state, **node_output}
            node_started = time.perf_counter()
            yield _sse({"type": "node_start", "trace_id": trace_id, "node": node_name, "title": f"\u5f00\u59cb\uff1a{node_name}", "content": "", "done": False})

            if node_name == "intent_router":
                event = {"type": "thinking", "title": "\u610f\u56fe\u8bc6\u522b", "content": f"\u8bc6\u522b\u4e3a\uff1a{node_output.get('intent', '')}"}
            elif node_name == "data_analyst":
                event = {"type": "tool_result", "title": "\u6570\u636e\u5206\u6790", "content": node_output.get("data_analysis", ""), "anomalies": node_output.get("anomalies", [])}
            elif node_name == "fetch_context":
                event = {"type": "tool_result", "title": "\u5916\u90e8\u73af\u5883", "content": node_output.get("external_context", "")}
            elif node_name == "rag_strategist":
                # Track RAG hit rate
                _rag_queries += 1
                refs = node_output.get("rag_references", [])
                if refs and len(refs) > 0:
                    _rag_hits += 1
                event = {
                    "type": "rag_reference",
                    "title": "SOP \u5f15\u7528 & \u7b56\u7565\u89c4\u5212",
                    "content": node_output.get("strategy", ""),
                    "strategy": node_output.get("strategy", ""),
                    "retrieved_docs": node_output.get("retrieved_docs", ""),
                    "references": refs,
                }
            elif node_name == "risk_controller":
                event = {"type": "thinking", "title": "\u98ce\u9669\u8bc4\u4f30", "content": json.dumps(node_output.get("risk_assessment", {}), ensure_ascii=False)}
            elif node_name == "human_approval":
                hit_approval_gate = True
                event = {"type": "approval_required", "title": "\u7b49\u5f85\u5ba1\u6279", "content": node_output.get("hitl_proposal", ""), "approval_needed": True, "approval_id": node_output.get("approval_id"), "estimated_cost": 2000}
            elif node_name == "copywriter":
                event = {"type": "thinking", "title": "\u8425\u9500\u6587\u6848", "content": node_output.get("copy", "")}
            elif node_name == "data_editor":
                event = {"type": "tool_result", "title": "\u6570\u636e\u64cd\u4f5c", "content": node_output.get("final_report", ""), "done": True}
            elif node_name == "report_generator":
                event = {"type": "final_answer", "title": "\u76f4\u63a5\u56de\u7b54", "content": node_output.get("final_report", ""), "done": True}
            elif node_name == "general_chat":
                event = {"type": "final_answer", "title": "\u76f4\u63a5\u56de\u7b54", "content": node_output.get("final_report", ""), "done": True}
            else:
                event = {"type": "thinking", "title": node_name, "content": json.dumps(node_output, ensure_ascii=False)}

            event.update({"trace_id": trace_id, "node": node_name, "done": event.get("done", False)})
            event["duration_ms"] = round((time.perf_counter() - node_started) * 1000, 2)
            trace_steps.append({
                "node": node_name,
                "event": event,
                "input_summary": query[:180],
                "time": datetime.datetime.now().isoformat(),
                "duration_ms": event["duration_ms"],
            })
            yield _sse(event)

        thread.join(timeout=10)

        # If we hit the HITL gate, pause here — Phase 2 runs via resume_agent_stream
        if hit_approval_gate:
            _save_graph_state(trace_id, final_state)
            _finish_trace(trace_id, trace_steps, "等待人工审批", status="awaiting_approval")
            yield _sse({"type": "end", "trace_id": trace_id, "node": "end", "done": True, "awaiting_approval": True, "content": ""})
            return

        final_answer = final_state.get("final_report") or final_state.get("copy") or final_state.get("strategy") or ""
        _finish_trace(trace_id, trace_steps, final_answer)
        rag_hit_rate = (_rag_hits / _rag_queries) if _rag_queries > 0 else None
        set_perf_context(rag_hit_rate=rag_hit_rate, extra_metrics={"trace_steps": len(trace_steps), "hit_approval": hit_approval_gate})
        yield _sse({"type": "end", "trace_id": trace_id, "node": "end", "done": True, "content": ""})
    except Exception as exc:
        _finish_trace(trace_id, trace_steps, str(exc), status="failed")
        yield _sse({"type": "error", "trace_id": trace_id, "node": "error", "done": True, "content": str(exc)})


async def resume_agent_stream(trace_id: str):
    """Resume Phase 2 (copywriter -> report_generator) after human approval.

    Relies on the approval record being already set to 'approved' by
    ``POST /api/agent/approve`` before this function is called.
    """
    from app.agents.tool_schemas import set_privilege_level, PrivilegeLevel
    set_privilege_level(PrivilegeLevel.WRITE)  # HITL approved → full privilege

    state = _load_graph_state(trace_id)
    if not state:
        yield _sse({"type": "error", "trace_id": trace_id, "node": "error",
                      "done": True, "content": "No saved state found for resume"})
        return

    # Verify approval status
    db = SessionLocal()
    try:
        approval = db.query(AgentApproval).filter(
            AgentApproval.trace_id == trace_id
        ).order_by(AgentApproval.id.desc()).first()
        if not approval or approval.status != "approved":
            yield _sse({"type": "end", "trace_id": trace_id, "node": "end",
                          "done": True, "content": "策略未被批准，流程终止"})
            return
    finally:
        db.close()

    # Mark resumed
    state["hitl_approved"] = True
    state["approval_status"] = "approved"

    # Load existing trace steps
    db = SessionLocal()
    try:
        trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
        if trace:
            trace.status = "running"
            db.commit()
    finally:
        db.close()

    yield _sse({"type": "agent_start", "trace_id": trace_id, "node": "agent",
                  "title": "审批通过，继续执行",
                  "content": "人工审批已通过，正在生成文案和最终报告...", "done": False})

    phase2_graph = build_post_approval_graph()
    queue: thread_queue.Queue = thread_queue.Queue()

    def _run_phase2():
        try:
            for output in phase2_graph.stream(state):
                for node_name, node_output in output.items():
                    queue.put((node_name, node_output))
        except Exception as exc:
            queue.put(("__error__", {"error": str(exc)}))
        finally:
            queue.put(None)

    thread = threading.Thread(target=_run_phase2, daemon=True)
    thread.start()

    trace_steps: list[dict] = []
    # Merge with existing steps
    db = SessionLocal()
    try:
        trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
        if trace:
            trace_steps = json.loads(trace.steps_json or "[]")
    finally:
        db.close()

    final_state = state

    try:
        while True:
            item = await asyncio.to_thread(queue.get)
            if item is None:
                break

            if isinstance(item, tuple) and item[0] == "__error__":
                error_msg = item[1].get("error", "Unknown error")
                _finish_trace(trace_id, trace_steps, str(error_msg), status="failed")
                yield _sse({"type": "error", "trace_id": trace_id, "node": "error",
                           "done": True, "content": error_msg})
                thread.join(timeout=5)
                return

            node_name, node_output = item
            if not isinstance(node_output, dict):
                node_output = {}
            final_state = {**final_state, **node_output}
            node_started = time.perf_counter()

            if node_name == "copywriter":
                event: dict = {"type": "thinking", "title": "营销文案",
                               "content": node_output.get("copy", "")}
            elif node_name == "report_generator":
                event = {"type": "final_answer", "title": "最终报告",
                         "content": node_output.get("final_report", ""), "done": True}
            else:
                event = {"type": "thinking", "title": node_name,
                         "content": json.dumps(node_output, ensure_ascii=False)}

            event.update({"trace_id": trace_id, "node": node_name,
                         "done": event.get("done", False)})
            event["duration_ms"] = round((time.perf_counter() - node_started) * 1000, 2)
            trace_steps.append({
                "node": node_name,
                "event": event,
                "input_summary": state.get("query", "")[:180],
                "time": datetime.datetime.now().isoformat(),
                "duration_ms": event["duration_ms"],
            })
            yield _sse(event)

        thread.join(timeout=10)

        final_answer = final_state.get("final_report") or final_state.get("copy", "")

        # Write decision back to agent memory for future reasoning
        if final_answer:
            try:
                store_id = state.get("store_id")
                save_agent_memory(store_id, "diagnosis", final_answer[:500])
            except Exception:
                pass  # best-effort, never block the flow

        _finish_trace(trace_id, trace_steps, final_answer)
        yield _sse({"type": "end", "trace_id": trace_id, "node": "end",
                    "done": True, "content": ""})
    except Exception as exc:
        _finish_trace(trace_id, trace_steps, str(exc), status="failed")
        yield _sse({"type": "error", "trace_id": trace_id, "node": "error",
                    "done": True, "content": str(exc)})




