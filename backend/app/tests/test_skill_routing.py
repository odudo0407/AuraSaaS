"""Tests for Skill routing — integration with intent_router_node."""

import pytest
from app.skills.schema import SkillSchema
from app.skills.registry import SkillRegistry
from app.agents.graph import intent_router_node


@pytest.fixture(autouse=True)
def clear_registry():
    SkillRegistry.clear()
    yield
    SkillRegistry.clear()


def _base_state(query: str):
    return {
        "query": query,
        "user_query": query,
        "trace_id": "test-trace",
        "messages": [],
        "current_node": "",
        "external_context": "",
        "retrieved_docs": "",
        "diagnosis": "",
        "data_analysis": "",
        "strategy": "",
        "approval_status": "",
        "approval_comment": "",
        "hitl_proposal": "",
        "hitl_approved": False,
        "campaign_copy": "",
        "copy": "",
        "final_report": "",
    }


def test_skill_routing_overrides_llm_intent():
    """When a Skill matches, intent should be 'skill:<name>'."""
    skill = SkillSchema(
        name="review_reply",
        description="Handle complaints",
        intent_triggers=["差评", "投诉"],
        required_tools=["retrieve_sop_knowledge"],
        knowledge_sources=["aurasaas_skill_review_reply"],
    )
    SkillRegistry.register(skill)

    result = intent_router_node(_base_state("客户给了差评，说菜品太咸"))
    assert result["intent"] == "skill:review_reply"
    assert result["active_skill"] == "review_reply"
    assert result["skill_knowledge_sources"] == ["aurasaas_skill_review_reply"]


def test_no_skill_match_falls_through():
    """When no Skill matches, intent should not start with 'skill:'."""
    result = intent_router_node(_base_state("今天天气怎么样"))
    assert not (result.get("intent") or "").startswith("skill:")
    assert result.get("active_skill") is None
