"""Business intelligence query and calculation tools."""

from app.agents.toolkit.legacy import (
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

__all__ = [
    "analyze_sku_trends",
    "calculate_roi",
    "compare_stores",
    "detect_business_anomalies",
    "fetch_cost_anomalies",
    "get_daily_summary",
    "get_holiday_context",
    "get_store_detail",
    "get_store_overview",
    "get_weather_impact_summary",
    "list_all_stores",
    "search_products",
]
