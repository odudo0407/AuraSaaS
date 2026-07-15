from app.agents import tools
from app.agents.graph import build_graph
from app.agents.nodes import data_analysis
from app.agents.tool_schemas import TOOL_MAP


def test_tools_compatibility_exports_keep_public_helpers():
    result = tools.tool_result(data={"ok": True})

    assert result["success"] is True
    assert result["data"] == {"ok": True}
    assert callable(tools.get_daily_summary)
    assert callable(tools.detect_business_anomalies)
    assert callable(tools.generate_marketing_strategy)


def test_tool_map_points_to_callable_tools():
    expected = {
        "get_daily_summary",
        "detect_anomalies",
        "search_knowledge_base",
        "rank_stores",
        "calculate_roi",
    }

    assert expected.issubset(TOOL_MAP.keys())
    for name in expected:
        assert callable(TOOL_MAP[name])


def test_build_graph_still_compiles_to_runnable_app():
    graph = build_graph()

    assert hasattr(graph, "stream")
    assert hasattr(graph, "invoke")


def test_data_analyst_node_contract(monkeypatch):
    monkeypatch.setattr(
        data_analysis,
        "collect_business_signals",
        lambda store_id=None: {
            "sku_report": "sku",
            "cost_report": "cost",
            "anomaly_result": {"data": [{"type": "revenue_drop"}]},
            "forecast": {"data": {"metric": "revenue"}},
            "comparison": {"data": {"change_pct": 1.5}},
            "ranking": {"data": [{"rank": 1}]},
            "tasks_created": {"data": {"tasks_created": 1}},
        },
    )
    monkeypatch.setattr(data_analysis, "summarize_business_signals", lambda signals: "summary")

    output = data_analysis.run_data_analyst_node({"store_id": 1, "messages": []})

    assert output["current_node"] == "data_analyst"
    assert output["data_analysis"] == "summary"
    assert output["diagnosis"] == "summary"
    assert output["anomalies"] == [{"type": "revenue_drop"}]
    assert output["metrics"]["forecast"] == {"metric": "revenue"}
    assert output["messages"][0]["node"] == "data_analyst"
