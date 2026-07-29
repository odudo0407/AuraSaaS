"""AuraSaaS Skill Plugin System.

Tool = atomic capability (one function, one action), Agent decides when & how to combine.
Skill = vertical solution (preset workflow + dedicated knowledge + structured output),
        auto-executed when intent matches.

Analogy: Tool is a screwdriver, Skill is "IKEA assembly service" —
         you don't need to figure out how to assemble every time.
"""

from app.skills.schema import SkillSchema
from app.skills.registry import SkillRegistry

__all__ = ["SkillSchema", "SkillRegistry"]
