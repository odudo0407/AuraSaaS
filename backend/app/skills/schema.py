"""Skill Schema — defines the contract every Skill module must fulfill."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class SkillSchema:
    """Unified schema for registering a Skill into the AuraSaaS agent platform.

    Each Skill is a self-contained vertical solution: it declares what user
    intents trigger it, which tools it needs, where its knowledge lives, and
    how its LangGraph subgraph is structured.

    Attributes:
        name: Unique skill identifier, e.g. "review_reply".
        description: Human-readable one-liner shown in the skill selector.
        intent_triggers: Chinese keywords that, if present in the user query,
            cause the agent router to match this skill.
        required_tools: Tool names this skill may call (used for validation
            and privilege pre-check).
        knowledge_sources: ChromaDB collection names this skill can query.
            Each skill gets its own collection for RAG isolation.
        workflow_config: Dict describing the LangGraph subgraph:
            {"nodes": [...], "edges": [...], "entry": "node_name"}.
        output_format: Free-text description of the structured output shape,
            shown in API responses so frontends can adapt rendering.
        build_subgraph: Optional callable that returns a compiled LangGraph
            StateGraph subgraph. Called once at registration time.
    """

    name: str
    description: str
    intent_triggers: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    knowledge_sources: list[str] = field(default_factory=list)
    workflow_config: dict = field(default_factory=dict)
    output_format: str = ""
    build_subgraph: Optional[Callable[[], Any]] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "intent_triggers": self.intent_triggers,
            "required_tools": self.required_tools,
            "knowledge_sources": self.knowledge_sources,
            "workflow_config": self.workflow_config,
            "output_format": self.output_format,
        }
