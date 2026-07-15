"""
Tool schemas in OpenAI Function Calling format + TOOL_MAP + 5-level privilege gating.

Privilege levels (cumulative):
  1. 只读 (read)     — query existing data, no analysis
  2. 分析 (analyze)  — detect anomalies, forecast, compare, rank
  3. 检索 (retrieve) — search knowledge base, agent memory
  4. 生成 (generate) — create marketing strategy, campaign copy, reports
  5. 写入 (write)    — add products, staff, metrics, tasks, memory

The ReAct agent defaults to level 3.  Levels 4-5 require the LangGraph HITL path.
"""

from __future__ import annotations

import enum
import threading
from app.agents.tools import (
    add_product,
    add_staff_member,
    add_store_metric,
    analyze_sku_trends,
    calculate_roi,
    check_external_context,
    compare_periods,
    create_anomaly_tasks,
    detect_business_anomalies,
    evaluate_strategy_risk,
    forecast_metric,
    generate_business_report,
    generate_campaign_copy,
    generate_marketing_strategy,
    get_daily_summary,
    get_store_detail,
    list_all_stores,
    rank_stores,
    retrieve_sop_knowledge,
    save_agent_memory,
    search_agent_memory,
    search_products,
)


class PrivilegeLevel(enum.IntEnum):
    READ = 1      # 只读
    ANALYZE = 2   # 分析
    RETRIEVE = 3  # 检索
    GENERATE = 4  # 生成
    WRITE = 5     # 写入


PRIVILEGE_LABELS = {
    1: "只读",
    2: "分析",
    3: "检索",
    4: "生成",
    5: "写入",
}

# Thread-local privilege context — defaults to RETRIEVE (level 3).
_privilege_ctx = threading.local()
_privilege_ctx.level = PrivilegeLevel.RETRIEVE


def set_privilege_level(level: PrivilegeLevel | int) -> None:
    """Set the current privilege ceiling for tool execution."""
    _privilege_ctx.level = PrivilegeLevel(int(level))


def get_privilege_level() -> PrivilegeLevel:
    """Get the current privilege ceiling."""
    return _privilege_ctx.level


class PrivilegeEscalationError(PermissionError):
    """Raised when a tool requires higher privilege than the current ceiling."""


# ── Tool schemas (OpenAI function calling format) ──────────────────────────

TOOL_SCHEMAS = [
    # ── Level 1: 只读 ──
    {
        "type": "function",
        "function": {
            "name": "get_daily_summary",
            "description": "查询某门店某天的经营日报，返回营收、订单量、客单价、热销SKU等指标。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID，必填"},
                    "date": {"type": "string", "description": "日期，格式 YYYY-MM-DD，默认今天"},
                },
                "required": ["store_id"],
            },
        },
        "privilege_level": 1,
    },
    {
        "type": "function",
        "function": {
            "name": "get_store_detail",
            "description": "查询单个门店的详细信息：店长姓名、城市商圈、评分、员工数、今日营收和订单数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID"},
                },
                "required": ["store_id"],
            },
        },
        "privilege_level": 1,
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_stores",
            "description": "列出全部门店及其基本信息：店名、城市、状态、店长、员工数、近7天营收。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        "privilege_level": 1,
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "按名称或分类模糊搜索商品/SKU，返回匹配的商品列表含价格和销量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "商品名称或分类关键词"},
                    "store_id": {"type": "integer", "description": "门店ID"},
                },
                "required": ["query"],
            },
        },
        "privilege_level": 1,
    },
    # ── Level 2: 分析 ──
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies",
            "description": "检测门店近N天的经营异常：营收骤降（环比下降超12%）、退单率飙升（环比翻1.8倍以上）、毛利恶化、外卖占比下滑等。返回异常列表含严重等级。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID，不传则检测全部门店"},
                    "days": {"type": "integer", "description": "检测最近多少天，默认7天"},
                },
                "required": [],
            },
        },
        "privilege_level": 2,
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_sku_trends",
            "description": "分析近N天的SKU销售趋势，识别销量下跌超过20%、低毛利（<45%）、高退单率（>3%）、缺货的SKU。返回文本报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID，不传则查全部"},
                    "date_range": {"type": "integer", "description": "天数范围，默认7天"},
                },
                "required": [],
            },
        },
        "privilege_level": 2,
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_metric",
            "description": "基于近30天历史数据用移动平均法预测未来N天的营收/利润/订单量趋势。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID"},
                    "metric": {"type": "string", "enum": ["revenue", "net_profit", "order_count"], "description": "要预测的指标"},
                    "forecast_days": {"type": "integer", "description": "预测未来几天，默认7天"},
                },
                "required": [],
            },
        },
        "privilege_level": 2,
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": "环比对比两个时间段的数据：本周 vs 上周，查看营收/利润/订单/毛利率的变化百分比和方向。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID"},
                    "metric": {"type": "string", "enum": ["revenue", "net_profit", "order_count", "gross_margin", "refund_rate", "avg_ticket"], "description": "对比指标"},
                },
                "required": [],
            },
        },
        "privilege_level": 2,
    },
    {
        "type": "function",
        "function": {
            "name": "rank_stores",
            "description": "按指标（营收/利润/订单/毛利率等）对门店进行排名，返回TOP N榜单。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["revenue", "net_profit", "order_count", "gross_margin", "refund_rate"], "description": "排名指标"},
                    "top_n": {"type": "integer", "description": "返回前N名，默认5"},
                },
                "required": [],
            },
        },
        "privilege_level": 2,
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_roi",
            "description": "计算营销活动的ROI回报率，可模拟不同转化率场景下的预期收益。",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {"type": "number", "description": "营销预算金额，默认1000元"},
                    "revenue_generated": {"type": "number", "description": "已产生的实际营收（如果有的话）"},
                },
                "required": [],
            },
        },
        "privilege_level": 2,
    },
    {
        "type": "function",
        "function": {
            "name": "check_external_factors",
            "description": "查询外部环境因素：天气、节假日、附近活动等，了解可能影响门店经营的外部条件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID"},
                    "date": {"type": "string", "description": "日期 YYYY-MM-DD，默认今天"},
                },
                "required": [],
            },
        },
        "privilege_level": 2,
    },
    # ── Level 3: 检索 ──
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "从SOP知识库中检索相关文档，包括经营策略、营销手册、差评回复流程、雨天外卖方案、退单处理SOP、高毛利SKU策略、节假日营销方案、新店开业清单等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或问题描述"},
                    "top_k": {"type": "integer", "description": "返回文档数量，默认4篇"},
                },
                "required": ["query"],
            },
        },
        "privilege_level": 3,
    },
    {
        "type": "function",
        "function": {
            "name": "search_agent_memory",
            "description": "搜索Agent的历史记忆——之前分析过的结论、用户偏好、门店历史情况等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索词"},
                    "store_id": {"type": "integer", "description": "门店ID"},
                },
                "required": ["query"],
            },
        },
        "privilege_level": 3,
    },
    # ── Level 4: 生成 ──
    {
        "type": "function",
        "function": {
            "name": "generate_marketing_strategy",
            "description": "根据诊断结果和预算限制，调用LLM生成低预算营销方案，包含具体动作和预期效果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "目标门店ID"},
                    "problem": {"type": "string", "description": "要解决的问题描述"},
                    "budget_limit": {"type": "number", "description": "预算上限，默认2000元"},
                    "target": {"type": "string", "description": "目标，如'提升订单'、'降低退单率'"},
                },
                "required": ["store_id", "problem"],
            },
        },
        "privilege_level": 4,
    },
    {
        "type": "function",
        "function": {
            "name": "generate_campaign_copy",
            "description": "根据营销策略调用LLM生成具体文案：短信、小程序Push、公众号文章、外卖平台标题、员工话术。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID"},
                    "name": {"type": "string", "description": "活动名称"},
                    "target": {"type": "string", "description": "活动目标"},
                },
                "required": ["store_id", "name"],
            },
        },
        "privilege_level": 4,
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_strategy_risk",
            "description": "评估营销策略的风险等级，返回风险评级（low/medium/high）和是否需要审批。",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {"type": "number", "description": "营销预算金额"},
                    "channel_count": {"type": "integer", "description": "投放渠道数量"},
                    "problem": {"type": "string", "description": "要解决的经营问题"},
                },
                "required": ["budget"],
            },
        },
        "privilege_level": 4,
    },
    # ── Level 5: 写入 ──
    {
        "type": "function",
        "function": {
            "name": "create_anomaly_tasks",
            "description": "根据检测到的异常自动创建待处理任务（如营收下降告警、退款异常工单），任务会出现在Dashboard。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID"},
                },
                "required": [],
            },
        },
        "privilege_level": 5,
    },
    {
        "type": "function",
        "function": {
            "name": "save_agent_memory",
            "description": "将本次分析的重要结论保存到长期记忆中，供未来对话参考。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID，没有则不传"},
                    "memory_type": {"type": "string", "enum": ["diagnosis", "preference", "strategy", "fact"], "description": "记忆类型"},
                    "content": {"type": "string", "description": "记忆内容，200字以内"},
                },
                "required": ["memory_type", "content"],
            },
        },
        "privilege_level": 5,
    },
    {
        "type": "function",
        "function": {
            "name": "add_product",
            "description": "添加新的商品/SKU到系统中。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku_name": {"type": "string", "description": "商品名称"},
                    "category": {"type": "string", "description": "商品分类"},
                    "price": {"type": "number", "description": "售价"},
                    "cost": {"type": "number", "description": "成本"},
                    "store_id": {"type": "integer", "description": "门店ID，默认1"},
                },
                "required": ["sku_name", "category", "price", "cost"],
            },
        },
        "privilege_level": 5,
    },
    {
        "type": "function",
        "function": {
            "name": "add_staff",
            "description": "添加新员工到系统中。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "员工姓名"},
                    "phone": {"type": "string", "description": "手机号"},
                    "role": {"type": "string", "description": "角色，如staff/manager/barista"},
                    "store_id": {"type": "integer", "description": "门店ID，默认1"},
                },
                "required": ["name", "role"],
            },
        },
        "privilege_level": 5,
    },
    {
        "type": "function",
        "function": {
            "name": "add_store_metric",
            "description": "录入门店某天的经营指标数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id": {"type": "integer", "description": "门店ID"},
                    "date": {"type": "string", "description": "日期 YYYY-MM-DD"},
                    "revenue": {"type": "number", "description": "营收金额"},
                    "order_count": {"type": "integer", "description": "订单数"},
                },
                "required": ["store_id", "date", "revenue", "order_count"],
            },
        },
        "privilege_level": 5,
    },
]

# ── Tool name → function map ──────────────────────────────────────────────

TOOL_MAP = {
    # Level 1: 只读
    "get_daily_summary": get_daily_summary,
    "get_store_detail": get_store_detail,
    "list_all_stores": list_all_stores,
    "search_products": search_products,
    # Level 2: 分析
    "detect_anomalies": detect_business_anomalies,
    "analyze_sku_trends": analyze_sku_trends,
    "forecast_metric": forecast_metric,
    "compare_periods": compare_periods,
    "rank_stores": rank_stores,
    "calculate_roi": calculate_roi,
    "check_external_factors": check_external_context,
    # Level 3: 检索
    "search_knowledge_base": retrieve_sop_knowledge,
    "search_agent_memory": search_agent_memory,
    # Level 4: 生成
    "generate_marketing_strategy": generate_marketing_strategy,
    "generate_campaign_copy": generate_campaign_copy,
    "evaluate_strategy_risk": evaluate_strategy_risk,
    # Level 5: 写入
    "create_anomaly_tasks": create_anomaly_tasks,
    "save_agent_memory": save_agent_memory,
    "add_product": add_product,
    "add_staff": add_staff_member,
    "add_store_metric": add_store_metric,
}

# Build privilege lookup per tool name
_TOOL_PRIVILEGE = {}
for s in TOOL_SCHEMAS:
    _TOOL_PRIVILEGE[s["function"]["name"]] = s["privilege_level"]


def get_tool_privilege(tool_name: str) -> int:
    """Return the privilege level required for a tool (default 5 if unknown)."""
    return _TOOL_PRIVILEGE.get(tool_name, 5)


def get_tools_for_privilege(max_level: int) -> list[dict]:
    """Return tool schemas filtered to the given max privilege level."""
    return [s for s in TOOL_SCHEMAS if s["privilege_level"] <= max_level]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with privilege gating. Returns JSON string for the LLM.

    If the tool's privilege level exceeds the current ceiling, raises
    ``PrivilegeEscalationError`` so the caller can route to HITL instead.
    """
    func = TOOL_MAP.get(name)
    if func is None:
        return _err(f"未知工具: {name}，请从可用工具列表中选择。可用: {', '.join(TOOL_MAP.keys())}")

    required_level = get_tool_privilege(name)
    current_level = get_privilege_level()

    if required_level > current_level:
        raise PrivilegeEscalationError(
            f"工具 '{name}' 需要 {PRIVILEGE_LABELS[required_level]}(Lv{required_level}) 权限，"
            f"当前权限等级为 {PRIVILEGE_LABELS[current_level]}(Lv{current_level})。"
            f"请通过人工审批流程提升权限后重试。"
        )

    try:
        result = func(**args)
    except TypeError as e:
        return _err(f"参数错误: {e}。请检查参数名和类型是否正确。")
    except Exception as e:
        return _err(f"工具执行异常: {e}")

    if isinstance(result, dict):
        return _ok(result)
    return _ok({"result": str(result)})


def _ok(data: dict) -> str:
    import json
    return json.dumps({"success": True, "data": data}, ensure_ascii=False)


def _err(msg: str) -> str:
    import json
    return json.dumps({"success": False, "error": msg}, ensure_ascii=False)
