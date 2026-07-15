"""Compatibility exports for BI Agent tools.

New code should prefer the grouped modules under ``app.agents.toolkit``.
This module keeps the historical ``from app.agents.tools import ...`` API
stable for graph nodes, tool schemas, tests, and external callers.
"""

from app.agents.toolkit.analytics import (
    compare_periods,
    create_anomaly_tasks,
    forecast_metric,
    rank_stores,
)
from app.agents.toolkit.bi import (
    analyze_sku_trends,
    calculate_roi,
    compare_stores,
    detect_business_anomalies,
    fetch_cost_anomalies,
    get_daily_summary,
    get_store_detail,
    get_holiday_context,
    get_store_overview,
    get_weather_impact_summary,
    list_all_stores,
    search_products,
)
from app.agents.toolkit.common import tool_result
from app.agents.toolkit.context import check_external_context
from app.agents.toolkit.knowledge import (
    retrieve_historical_reviews,
    retrieve_marketing_cases,
    retrieve_sop_knowledge,
)
from app.agents.toolkit.marketing import (
    evaluate_strategy_risk,
    generate_campaign_copy,
    generate_marketing_strategy,
    simulate_marketing_webhook,
)
from app.agents.toolkit.memory import (
    save_agent_memory,
    search_agent_memory,
    summarize_store_history,
)
from app.agents.toolkit.mutations import (
    add_product,
    add_staff_member,
    add_store_metric,
)
from app.agents.toolkit.reporting import (
    export_report_to_markdown,
    export_report_to_pdf,
    generate_business_report,
)

__all__ = [
    "add_product",
    "add_staff_member",
    "add_store_metric",
    "analyze_sku_trends",
    "calculate_roi",
    "check_external_context",
    "compare_periods",
    "compare_stores",
    "create_anomaly_tasks",
    "detect_business_anomalies",
    "evaluate_strategy_risk",
    "export_report_to_markdown",
    "export_report_to_pdf",
    "fetch_cost_anomalies",
    "forecast_metric",
    "generate_business_report",
    "generate_campaign_copy",
    "generate_marketing_strategy",
    "get_daily_summary",
    "get_holiday_context",
    "get_store_detail",
    "get_store_overview",
    "get_weather_impact_summary",
    "list_all_stores",
    "rank_stores",
    "retrieve_historical_reviews",
    "retrieve_marketing_cases",
    "retrieve_sop_knowledge",
    "save_agent_memory",
    "search_agent_memory",
    "search_products",
    "simulate_marketing_webhook",
    "summarize_store_history",
    "tool_result",
]
