"""Skills API — list and inspect registered Agent Skills."""

from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.core.response import api_response
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills(user=Depends(get_current_user)):
    """List all registered skills with their schemas."""
    skills = SkillRegistry.list_all()
    return api_response(
        data={
            "skills": [s.to_dict() for s in skills],
            "count": len(skills),
        },
        message="Skills listed",
    )
