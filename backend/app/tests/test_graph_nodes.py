"""Unit tests for LangGraph agent nodes, routing logic, and RAG retrieval."""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

test_db = Path(tempfile.mkdtemp()) / "aurasaas_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db.as_posix()}"
os.environ["SEED_DEMO_ON_STARTUP"] = "false"
os.environ["DEEPSEEK_API_KEY"] = "sk-placeholder"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ENVIRONMENT"] = "test"

from app.database import Base, engine  # noqa: E402
Base.metadata.create_all(bind=engine)


# ── Graph compilation ──────────────────────────────────────────────────────

def test_build_graph_has_all_nodes():
    from app.agents.graph import build_graph
    graph = build_graph()
    nodes = set(graph.nodes.keys())
    expected = {"__start__", "intent_router", "skill_executor", "data_analyst",
                "data_editor", "fetch_context", "rag_strategist", "risk_controller",
                "human_approval", "general_chat", "report_generator"}
    assert nodes == expected


def test_phase2_graph_compiles():
    from app.agents.graph import build_post_approval_graph
    g = build_post_approval_graph()
    nodes = set(g.nodes.keys())
    assert "copywriter" in nodes
    assert "report_generator" in nodes


# ── Keyword intent routing (11 intents) ────────────────────────────────────

def test_keyword_intent_chat():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("你好")["intent"] == "general_chat"


def test_keyword_intent_data_query():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("门店营收排行")["intent"] == "data_query"


def test_keyword_intent_anomaly():
    from app.agents.graph import _keyword_intent
    r = _keyword_intent("为什么退款率下降了")
    assert r["intent"] == "anomaly_diagnosis"


def test_keyword_intent_knowledge():
    from app.agents.graph import _keyword_intent
    r = _keyword_intent("查SOP知识库流程规范")
    assert r["intent"] == "knowledge_query"


def test_keyword_intent_marketing():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("帮我做营销推广方案")["intent"] == "marketing_plan"


def test_keyword_intent_data_management():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("新增一个商品")["intent"] == "data_management"


def test_keyword_intent_report():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("生成上周战报")["intent"] == "report_generation"


def test_keyword_intent_store_ops():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("员工排班怎么安排")["intent"] == "store_operation"


def test_keyword_intent_finance():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("帮我算一下ROI")["intent"] == "financial_analysis"


def test_keyword_intent_customer():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("客户复购率怎么样")["intent"] == "customer_insight"


def test_keyword_intent_competitor():
    from app.agents.graph import _keyword_intent
    assert _keyword_intent("竞品分析对比")["intent"] == "competitor_analysis"


# ── Intent router node ─────────────────────────────────────────────────────

def test_intent_router_classifies_anomaly():
    from app.agents.graph import intent_router_node, AgentState
    state: AgentState = {"user_query": "为什么退单率上升", "query": "为什么退单率上升",
                         "trace_id": "t1", "messages": []}
    result = intent_router_node(state)
    assert result["intent"] == "anomaly_diagnosis"


def test_intent_router_classifies_knowledge():
    from app.agents.graph import intent_router_node, AgentState
    state: AgentState = {"user_query": "雨天怎么处理外卖", "query": "雨天怎么处理外卖",
                         "trace_id": "t2", "messages": []}
    result = intent_router_node(state)
    assert result["intent"] == "knowledge_query"


def test_intent_router_defaults_to_general_chat():
    from app.agents.graph import intent_router_node, AgentState
    state: AgentState = {"user_query": "今天天气不错", "query": "今天天气不错",
                         "trace_id": "t3", "messages": []}
    result = intent_router_node(state)
    assert result["intent"] == "general_chat"


# ── Graph routing ──────────────────────────────────────────────────────────

def test_knowledge_query_skips_hitl():
    from app.agents.graph import build_graph, AgentState
    state: AgentState = {"user_query": "查SOP", "query": "查SOP", "trace_id": "tk",
                         "messages": [], "intent": "knowledge_query"}
    graph = build_graph()
    for output in graph.stream(state):
        node_names = list(output.keys())
        assert "risk_controller" not in node_names
        assert "human_approval" not in node_names


def test_anomaly_diagnosis_hits_hitl_gate():
    from app.agents.graph import build_graph, AgentState
    state: AgentState = {"user_query": "为什么营收下降", "query": "为什么营收下降",
                         "trace_id": "ta", "messages": [], "intent": "anomaly_diagnosis"}
    graph = build_graph()
    nodes_seen = set()
    for output in graph.stream(state):
        nodes_seen.update(output.keys())
    assert "human_approval" in nodes_seen


# ── API auto-routing ───────────────────────────────────────────────────────

def test_route_to_langgraph():
    from app.api.agent import _route_intent
    assert _route_intent("帮我做营销活动方案") == "langgraph"
    assert _route_intent("为什么退单率飙升") == "langgraph"
    assert _route_intent("生成战报") == "langgraph"


def test_route_to_react():
    from app.api.agent import _route_intent
    assert _route_intent("今天营收多少") == "react"
    assert _route_intent("你好") == "react"
    assert _route_intent("门店有哪些") == "react"


# ── RAG retrieval ──────────────────────────────────────────────────────────

def test_rag_keyword_fallback():
    from app.services.rag_service import _keyword_query
    docs = _keyword_query("退单率", top_k=3)
    assert len(docs) >= 1
    for d in docs:
        assert "title" in d
        assert "snippet" in d


def test_rag_query_knowledge_rain():
    from app.services.rag_service import query_knowledge
    docs = query_knowledge("雨天外卖配送", top_k=2)
    assert len(docs) >= 1
    for d in docs:
        assert "title" in d


def test_rag_query_knowledge_holiday():
    from app.services.rag_service import query_knowledge
    docs = query_knowledge("节假日营销活动", top_k=3)
    assert len(docs) >= 1


def test_rag_query_knowledge_refund():
    from app.services.rag_service import query_knowledge
    docs = query_knowledge("退单率过高怎么处理", top_k=2)
    assert len(docs) >= 1


# ── AgentState ─────────────────────────────────────────────────────────────

def test_agent_state_defaults():
    from app.agents.graph import AgentState
    state: AgentState = {
        "user_query": "test", "query": "test", "trace_id": "s1", "messages": [],
        "external_context": "", "retrieved_docs": "", "diagnosis": "",
        "data_analysis": "", "strategy": "", "approval_status": "",
        "approval_comment": "", "hitl_proposal": "", "hitl_approved": False,
        "campaign_copy": "", "copy": "", "final_report": "", "current_node": "",
    }
    assert state["external_context"] == ""
    assert state["hitl_approved"] is False


# ── SSE streaming ──────────────────────────────────────────────────────────

def test_run_agent_stream_yields_events():
    import asyncio
    from app.agents.graph import run_agent_stream

    async def _collect():
        events = []
        async for raw in run_agent_stream("查看经营数据概况"):
            events.append(raw)
            if len(events) >= 3:
                break
        return events

    events = asyncio.run(_collect())
    assert len(events) >= 1
    first = json.loads(events[0])
    assert first["type"] == "agent_start"
    assert "trace_id" in first
