"""Data-analysis node helpers for the LangGraph workflow."""

from __future__ import annotations

import datetime
import json

from app.agents.tools import (
    analyze_sku_trends,
    compare_periods,
    create_anomaly_tasks,
    detect_business_anomalies,
    fetch_cost_anomalies,
    forecast_metric,
    rank_stores,
)
from app.services.deepseek_client import chat as llm_chat


def _append_message(state: dict, node: str, content: str) -> list:
    return [*state.get("messages", []), {"node": node, "content": content, "time": datetime.datetime.now().isoformat()}]


def collect_business_signals(store_id: int | None = None) -> dict:
    """Collect the raw BI signals used by the data analyst node."""

    anomaly_result = detect_business_anomalies(store_id=store_id, days=7)
    return {
        "sku_report": analyze_sku_trends(7, store_id=store_id),
        "cost_report": fetch_cost_anomalies(store_id=store_id),
        "anomaly_result": anomaly_result,
        "forecast": forecast_metric("revenue", store_id=store_id),
        "comparison": compare_periods(store_id=store_id, metric="revenue"),
        "ranking": rank_stores("revenue", top_n=3),
        "tasks_created": create_anomaly_tasks(store_id=store_id),
    }


def summarize_business_signals(signals: dict) -> str:
    """Summarize collected BI signals with the configured LLM fallback behavior."""

    anomaly_text = json.dumps(signals["anomaly_result"].get("data", []), ensure_ascii=False, indent=2)
    fallback = (
        "数据诊断：近 7 天发现以下重点信号：\n"
        f"{anomaly_text}\n\n"
        "SKU 趋势与成本异常已获取，供后续策略节点参考。"
    )
    return llm_chat(
        "你是经营分析师。根据 BI 数据，简洁总结关键发现，包括参数变化、退款趋势、SKU、毛利和外卖占比变化，50 字以内。",
        (
            f"近 7 天数据分析：\n"
            f"异常：{anomaly_text}\n"
            f"SKU报告：{json.dumps(signals['sku_report'], ensure_ascii=False, indent=2)}\n"
            f"成本异常：{json.dumps(signals['cost_report'], ensure_ascii=False, indent=2)}"
        ),
        fallback,
        temperature=0.3,
        max_tokens=500,
    )


def run_data_analyst_node(state: dict) -> dict:
    """Analyze metrics, anomalies, forecasts, comparisons, and auto-created tasks."""

    store_id = state.get("store_id")
    signals = collect_business_signals(store_id=store_id)
    analysis = summarize_business_signals(signals)

    return {
        "data_analysis": analysis,
        "diagnosis": analysis,
        "anomalies": signals["anomaly_result"].get("data", []),
        "metrics": {
            "forecast": signals["forecast"].get("data"),
            "comparison": signals["comparison"].get("data"),
            "ranking": signals["ranking"].get("data"),
            "tasks_created": signals["tasks_created"].get("data"),
        },
        "current_node": "data_analyst",
        "messages": _append_message(state, "data_analyst", analysis),
    }
