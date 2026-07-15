"""System status and observability endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.observability import metrics
from app.database import get_db
from app.models.models import AgentApproval, AgentTrace, KnowledgeDocument, Store, Task

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def system_status(db: Session = Depends(get_db)):
    """Return a compact dependency and data readiness snapshot."""

    settings = get_settings()
    chroma_path = Path(settings.chroma_dir)
    database_status = "ok"
    schema_ready = True

    db.execute(text("SELECT 1"))

    try:
        counts = {
            "stores": db.query(Store).count(),
            "knowledge_documents": db.query(KnowledgeDocument).count(),
            "agent_traces": db.query(AgentTrace).count(),
            "pending_approvals": db.query(AgentApproval).filter(AgentApproval.status == "pending").count(),
            "pending_tasks": db.query(Task).filter(Task.status == "pending").count(),
        }
    except SQLAlchemyError:
        schema_ready = False
        database_status = "schema_missing"
        counts = {
            "stores": 0,
            "knowledge_documents": 0,
            "agent_traces": 0,
            "pending_approvals": 0,
            "pending_tasks": 0,
        }

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "app": settings.app_name,
            "environment": os.getenv("ENVIRONMENT", "local"),
            "database": database_status,
            "schema_ready": schema_ready,
            "next_step": None if schema_ready else "Run python -m app.scripts.generate_mock_data from backend/.",
            "rag_index_path": str(chroma_path),
            "rag_index_exists": chroma_path.exists(),
            "llm_configured": bool(settings.deepseek_api_key and settings.deepseek_api_key != "sk-placeholder"),
            "counts": counts,
        },
    }


@router.get("/metrics")
def system_metrics():
    """Return rolling in-memory request metrics for the dashboard or README demo."""

    return {"code": 0, "message": "ok", "data": metrics.snapshot()}
