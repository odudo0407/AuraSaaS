"""Skill 2: 门店健康度诊断 — proactive analysis type.

When a store manager asks about declining performance, this Skill:
  1. Collects BI data (daily summary, anomalies, period comparison, ranking)
  2. Diagnoses root cause via LLM analysis
  3. Outputs diagnostic report + improvement suggestions

Registers itself at import time.
"""

from __future__ import annotations

import logging
from app.skills.schema import SkillSchema
from app.skills.registry import SkillRegistry
from app.agents.tools import (
    get_daily_summary,
    detect_business_anomalies,
    compare_periods,
    rank_stores,
    calculate_roi,
)
from app.services.deepseek_client import chat as llm_chat

logger = logging.getLogger(__name__)

SKILL_NAME = "store_health"

# ── Skill Schema ──────────────────────────────────────────────
schema = SkillSchema(
    name=SKILL_NAME,
    description="门店健康度诊断：采集营收、异常、对比、排名等多维度数据，AI 归因分析并输出改善建议",
    intent_triggers=["营收下降", "业绩下滑", "怎么回事", "诊断", "经营状况",
                     "健康度", "预警", "亏损", "毛利下降", "客流量下降", "生意不好"],
    required_tools=["get_daily_summary", "detect_anomalies", "compare_periods",
                    "rank_stores", "calculate_roi", "retrieve_sop_knowledge"],
    knowledge_sources=[],  # reuses public SOP, no dedicated collection
    workflow_config={
        "nodes": ["data_collector", "root_cause_analyzer", "suggestion_output"],
        "entry": "data_collector",
        "type": "proactive_analysis",
    },
    output_format=(
        "结构化输出：\n"
        "1. 数据概览（营收趋势 / 异常指标 / 同期对比 / 同区域排名）\n"
        "2. 根因分析（客流降 / 客单降 / 退单升 / SKU滞销 / 外部因素）\n"
        "3. 改善建议（具体可执行的措施）"
    ),
)


# ── Workflow Implementation ───────────────────────────────────

def _collect_data(state: dict) -> dict:
    """Node 1: Collect BI data from multiple tools concurrently."""
    store_id = state.get("store_id")
    results = {}

    # Basic store data
    try:
        summary = get_daily_summary(store_id=store_id)
        results["summary"] = str(summary)[:2000]
    except Exception as e:
        results["summary"] = f"获取营收概况失败: {e}"

    # Anomaly detection
    try:
        anomalies = detect_business_anomalies(store_id=store_id)
        results["anomalies"] = str(anomalies)[:2000]
    except Exception as e:
        results["anomalies"] = f"获取异常数据失败: {e}"

    # Period comparison
    try:
        comparison = compare_periods(store_id=store_id)
        results["comparison"] = str(comparison)[:2000]
    except Exception as e:
        results["comparison"] = f"获取对比数据失败: {e}"

    # Store ranking
    try:
        ranking = rank_stores()
        results["ranking"] = str(ranking)[:2000]
    except Exception as e:
        results["ranking"] = f"获取排名数据失败: {e}"

    # ROI snapshot
    try:
        roi = calculate_roi(store_id=store_id)
        results["roi"] = str(roi)[:1500]
    except Exception as e:
        results["roi"] = f"获取ROI数据失败: {e}"

    logger.info("Skill store_health: data collected for store_id=%s", store_id)
    return results


def _diagnose(query: str, data: dict) -> str:
    """Node 2: LLM root-cause analysis from collected data."""
    system = (
        "你是一个连锁餐饮的运营总监。根据以下门店经营数据，分析业绩下滑的根因。\n"
        "从以下几个维度分析：客流/客单价/退单率/品类结构/外部因素。\n"
        "输出简洁的归因分析，每个结论都要引用具体数据。限制 300 字以内。"
    )
    context = (
        f"门店数据：\n"
        f"营收概况：{data.get('summary', '无数据')}\n"
        f"异常指标：{data.get('anomalies', '无数据')}\n"
        f"环比/同比：{data.get('comparison', '无数据')}\n"
        f"区域排名：{data.get('ranking', '无数据')}\n"
        f"ROI数据：{data.get('roi', '无数据')}\n"
    )
    try:
        return llm_chat(system, f"用户问题: {query}\n\n{context}", "数据不足，无法完成完整归因分析。", temperature=0.3, max_tokens=600)
    except Exception:
        return "当前数据不足以完成完整的根因分析，建议补充更多门店经营数据后再进行诊断。"


def _generate_suggestions(query: str, diagnosis: str) -> str:
    """Node 3: Generate actionable improvement suggestions."""
    system = (
        "你是一个连锁餐饮的运营总监。根据诊断结果，给出 3-5 条具体可执行的改善建议。\n"
        "每条建议包含：问题描述、具体措施、预期效果。限制 300 字以内。"
    )
    try:
        return llm_chat(system, f"用户问题: {query}\n\n诊断结果: {diagnosis}", "建议根据实际情况进一步细化方案。", temperature=0.5, max_tokens=500)
    except Exception:
        return "建议：1. 核查近期客流数据，分析客流下降原因；2. 检查菜单结构，评估高毛利SKU表现；3. 对比周边竞品定价策略。"


def _format_report(query: str, data: dict, diagnosis: str, suggestions: str) -> str:
    """Format the final diagnostic report as Markdown."""
    return (
        f"## 门店健康度诊断报告\n\n"
        f"**诊断问题**：{query}\n\n"
        f"### 数据概览\n"
        f"{data.get('summary', '暂无数据')[:300]}\n\n"
        f"### 异常指标\n"
        f"{data.get('anomalies', '暂无数据')[:300]}\n\n"
        f"### 根因分析\n"
        f"{diagnosis}\n\n"
        f"### 改善建议\n"
        f"{suggestions}\n\n"
        f"---\n"
        f"*以上诊断基于当前门店经营数据，建议结合实际运营情况综合判断。*"
    )


def run(state: dict) -> dict:
    """Execute the store health diagnostic Skill workflow."""
    query = state.get("query", "")

    data = _collect_data(state)
    diagnosis = _diagnose(query, data)
    suggestions = _generate_suggestions(query, diagnosis)
    report = _format_report(query, data, diagnosis, suggestions)

    logger.info("Skill store_health: diagnosis completed for query=%r", query[:80])

    from app.agents.graph import _append_message
    return {
        "final_report": report,
        "strategy": diagnosis,
        "current_node": "skill:store_health:output",
        "messages": _append_message(state, "skill:store_health", f"诊断完成 | 建议已生成"),
    }


# ── Auto-register at import time ──────────────────────────────
SkillRegistry.register(schema)
logger.info("Skill registered: %s", SKILL_NAME)
