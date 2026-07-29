"""Tests for Skill Registry — register, discover, match, and list."""

import pytest
from app.skills.schema import SkillSchema
from app.skills.registry import SkillRegistry


@pytest.fixture(autouse=True)
def clear_registry():
    SkillRegistry.clear()
    yield
    SkillRegistry.clear()


def test_register_and_get():
    skill = SkillSchema(
        name="test_skill",
        description="A test skill",
        intent_triggers=["测试", "test"],
        required_tools=["get_daily_summary"],
    )
    SkillRegistry.register(skill)
    assert SkillRegistry.count() == 1
    assert SkillRegistry.get("test_skill") is skill
    assert SkillRegistry.get("nonexistent") is None


def test_list_all():
    s1 = SkillSchema(name="s1", description="First")
    s2 = SkillSchema(name="s2", description="Second")
    SkillRegistry.register(s1)
    SkillRegistry.register(s2)
    skills = SkillRegistry.list_all()
    assert len(skills) == 2
    assert {s.name for s in skills} == {"s1", "s2"}


def test_match_intent_exact_keyword():
    skill = SkillSchema(
        name="review_reply",
        description="Handle customer complaints",
        intent_triggers=["差评", "投诉", "不满"],
    )
    SkillRegistry.register(skill)

    assert SkillRegistry.match_intent("客户给了差评说菜品太咸") is not None
    assert SkillRegistry.match_intent("有个投诉需要处理") is not None
    assert SkillRegistry.match_intent("今天天气不错") is None


def test_match_intent_first_match_wins():
    s1 = SkillSchema(name="s1", description="First", intent_triggers=["差评"])
    s2 = SkillSchema(name="s2", description="Second", intent_triggers=["差评", "投诉"])
    SkillRegistry.register(s1)
    SkillRegistry.register(s2)

    result = SkillRegistry.match_intent("客户给了差评")
    assert result is not None
    assert result.name == "s1"  # first registered wins


def test_match_intent_empty_registry():
    assert SkillRegistry.match_intent("差评") is None
    assert SkillRegistry.count() == 0


def test_register_replaces_existing():
    s1 = SkillSchema(name="test", description="v1")
    s2 = SkillSchema(name="test", description="v2")
    SkillRegistry.register(s1)
    SkillRegistry.register(s2)
    assert SkillRegistry.count() == 1
    assert SkillRegistry.get("test").description == "v2"


def test_to_dict():
    skill = SkillSchema(
        name="demo",
        description="Demo skill",
        intent_triggers=["demo"],
        required_tools=["tool_a"],
        knowledge_sources=["coll_demo"],
        workflow_config={"nodes": ["a", "b"]},
        output_format="markdown",
    )
    d = skill.to_dict()
    assert d["name"] == "demo"
    assert d["knowledge_sources"] == ["coll_demo"]
    assert d["output_format"] == "markdown"
