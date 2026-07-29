"""Skill 1: 差评回复与客诉处理 — passive response type.

When a store manager reports a negative review, this Skill:
  1. Analyzes the complaint (store, dish, type, severity)
  2. Matches the best reply strategy from SOP + templates
  3. Generates a professional reply + internal action suggestion
  4. Formats structured output

Registers itself at import time.
"""

from __future__ import annotations

import logging
from app.skills.schema import SkillSchema
from app.skills.registry import SkillRegistry
from app.services.deepseek_client import chat as llm_chat, has_valid_api_key

logger = logging.getLogger(__name__)

SKILL_NAME = "review_reply"

# ── Skill Schema ──────────────────────────────────────────────
schema = SkillSchema(
    name=SKILL_NAME,
    description="差评回复与客诉处理：分析差评内容，匹配回复策略，生成专业回复文案与内部处理建议",
    intent_triggers=["差评", "投诉", "不满", "难吃", "态度差", "退单", "退款", "太咸",
                     "太淡", "太辣", "太贵", "量少", "等太久", "上菜慢", "服务差"],
    required_tools=["retrieve_sop_knowledge", "search_agent_memory", "save_agent_memory"],
    knowledge_sources=["aurasaas_skill_review_reply"],
    workflow_config={
        "nodes": ["review_analyzer", "sop_matcher", "reply_generator", "output_formatter"],
        "entry": "review_analyzer",
        "type": "passive_response",
    },
    output_format=(
        "结构化输出：\n"
        "1. 差评分析（投诉类型 / 情绪强度 / 是否需升级）\n"
        "2. 匹配的回复策略（道歉 / 解释 / 补偿）\n"
        "3. 回复文案（可直接使用）\n"
        "4. 内部处理建议（后厨/服务/流程改进）"
    ),
)


# ── Workflow Implementation ───────────────────────────────────

def _analyze_review(query: str) -> dict:
    """Node 1: Extract key info from the complaint."""
    system = (
        "你是一个客诉分析专家。从用户输入中提取关键信息，返回 JSON：\n"
        '{"store": "门店名称或编号", "dish": "涉及菜品", '
        '"complaint_type": "口味/服务/卫生/价格/速度/其他", '
        '"severity": "低/中/高", "needs_escalation": true/false}'
    )
    try:
        raw = llm_chat(system, f"用户输入: {query}", "", temperature=0.1, max_tokens=300)
        import json
        return json.loads(raw.strip().split("\n", 1)[1] if raw.strip().startswith("```") else raw.strip())
    except Exception:
        return {"complaint_type": "其他", "severity": "中", "needs_escalation": False}


def _match_sop(analysis: dict) -> str:
    """Node 2: Match the best reply strategy based on complaint type."""
    strategies = {
        "口味": "道歉 + 解释口味标准 + 邀请再次到店赠送小菜",
        "服务": "诚恳道歉 + 说明已约谈员工 + 承诺加强培训",
        "卫生": "高度重视 + 说明卫生标准 + 内部彻查 + 补偿方案",
        "价格": "解释定价逻辑 + 推荐性价比套餐 + 提供折扣券",
        "速度": "道歉 + 解释高峰期 + 推荐错峰用餐 + 赠送饮品券",
        "其他": "表达感谢 + 认真对待 + 邀请再次到店体验",
    }
    return strategies.get(analysis.get("complaint_type", "其他"), strategies["其他"])


def _generate_reply(query: str, analysis: dict, strategy: str) -> str:
    """Node 3: Generate professional reply copy."""
    system = (
        "你是一个连锁餐饮品牌的客服经理。根据差评内容和分析结果，生成一段专业、真诚的回复文案。\n"
        f"投诉类型：{analysis.get('complaint_type', '其他')}\n"
        f"严重程度：{analysis.get('severity', '中')}\n"
        f"回复策略：{strategy}\n"
        "要求：语气真诚、不推卸责任、给出具体改进措施、邀请再次到店。限制 200 字以内。"
    )
    try:
        return llm_chat(system, f"差评内容: {query}", "感谢您的反馈，我们非常重视。", temperature=0.7, max_tokens=400)
    except Exception:
        return "感谢您的反馈，我们非常重视您的意见，已安排相关人员跟进处理。期待您再次光临。"


def _format_output(analysis: dict, strategy: str, reply: str) -> str:
    """Node 4: Format structured output as Markdown."""
    severity_label = {"低": "[低]", "中": "[中]", "高": "[高]"}
    label = severity_label.get(analysis.get("severity", "中"), "[中]")

    return (
        f"## 差评回复\n\n"
        f"### 分析\n"
        f"- 投诉类型：{analysis.get('complaint_type', '未知')}\n"
        f"- 情绪强度：{label} {analysis.get('severity', '中')}\n"
        f"- 是否需升级：{'是' if analysis.get('needs_escalation') else '否'}\n\n"
        f"### 回复策略\n{strategy}\n\n"
        f"### 回复文案\n{reply}\n\n"
        f"### 内部处理建议\n"
        f"- 建议门店经理关注此单差评\n"
        f"- 如涉及菜品问题，通知后厨核查\n"
        f"- 记录到客诉台账，跟踪回访\n"
    )


def run(state: dict) -> dict:
    """Execute the review reply Skill workflow. Returns updated state dict."""
    query = state.get("query", "")

    analysis = _analyze_review(query)
    strategy = _match_sop(analysis)
    reply = _generate_reply(query, analysis, strategy)
    output = _format_output(analysis, strategy, reply)

    logger.info("Skill review_reply completed: type=%s severity=%s", analysis.get("complaint_type"), analysis.get("severity"))

    from app.agents.graph import _append_message
    return {
        "final_report": output,
        "strategy": strategy,
        "current_node": "skill:review_reply:output",
        "messages": _append_message(state, "skill:review_reply", f"投诉类型: {analysis.get('complaint_type')} | 回复已生成"),
    }


# ── Auto-register at import time ──────────────────────────────
SkillRegistry.register(schema)
logger.info("Skill registered: %s", SKILL_NAME)
