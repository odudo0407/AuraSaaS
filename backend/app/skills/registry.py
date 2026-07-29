"""Skill Registry — register, discover, and match Skills to user intents."""

from __future__ import annotations

import logging
from typing import Optional

from app.skills.schema import SkillSchema

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Thread-safe registry for Skill plugins.

    Skills are registered at startup. The agent router queries the registry
    to check whether an incoming intent should be handled by a Skill subgraph
    rather than the generic agent pipeline.
    """

    _skills: dict[str, SkillSchema] = {}

    @classmethod
    def register(cls, skill: SkillSchema) -> None:
        """Register a skill. Replaces any existing skill with the same name."""
        cls._skills[skill.name] = skill
        logger.info(
            "Skill registered: %s (triggers=%s, tools=%s)",
            skill.name,
            skill.intent_triggers,
            skill.required_tools,
        )

    @classmethod
    def get(cls, name: str) -> Optional[SkillSchema]:
        """Get a skill by name, or None if not found."""
        return cls._skills.get(name)

    @classmethod
    def list_all(cls) -> list[SkillSchema]:
        """Return all registered skills."""
        return list(cls._skills.values())

    @classmethod
    def match_intent(cls, query: str) -> Optional[SkillSchema]:
        """Match a user query to the best-matching skill.

        Returns the first skill whose intent_triggers have a keyword match
        in the query. Falls back to None if no skill matches — the caller
        should then route to the generic agent pipeline.
        """
        q = query.lower()
        for skill in cls._skills.values():
            for trigger in skill.intent_triggers:
                if trigger.lower() in q:
                    logger.info("Skill matched: %s (trigger='%s')", skill.name, trigger)
                    return skill
        return None

    @classmethod
    def clear(cls) -> None:
        """Remove all registered skills (useful for testing)."""
        cls._skills.clear()

    @classmethod
    def count(cls) -> int:
        """Return the number of registered skills."""
        return len(cls._skills)
