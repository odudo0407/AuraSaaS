"""Admin API — mock data regeneration and database reset."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.core.deps import get_current_user
from app.models.models import (
    Store, BusinessMetricsDaily, SkuPerformance, ExternalFactor,
    MarketingCampaign, CampaignResult, KnowledgeDocument, AgentMemory,
    AgentTrace, AgentApproval, Task, User,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

DATA_TABLES = [
    Task, AgentApproval, AgentTrace, AgentMemory, KnowledgeDocument,
    CampaignResult, MarketingCampaign, ExternalFactor, SkuPerformance,
    BusinessMetricsDaily, Store,
]


@router.post("/regenerate-mock")
def regenerate_mock(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Delete all data and re-seed mock data."""
    for model in reversed(DATA_TABLES):
        db.query(model).delete()
    db.commit()
    from scripts.generate_mock_data import init_mock_data
    init_mock_data()
    return {"code": 0, "data": None, "message": "Demo 数据已重新生成"}


@router.post("/reset-db")
def reset_db(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Drop all data tables, recreate, and re-seed."""
    db.close()
    for model in reversed(DATA_TABLES):
        model.__table__.drop(engine, checkfirst=True)
    Base.metadata.create_all(engine, tables=[m.__table__ for m in DATA_TABLES])
    from scripts.generate_mock_data import init_mock_data
    init_mock_data()
    return {"code": 0, "data": None, "message": "数据库已重置"}
