"""Agent API — SSE streaming, HITL approval, trace and replay."""

import datetime
import json
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Query, Body, Depends
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.core.response import api_response
from app.database import get_db
from app.models.models import AgentApproval, AgentTrace, MarketingCampaign, User
from app.agents.graph import run_agent_stream, resume_agent_stream
from app.agents.react_agent import run_react_agent_stream
from app.services.agent_forms import preview_agent_form, submit_agent_form


# ── auto-routing: intents → LangGraph (HITL-capable) vs ReAct (fast) ──────

_LANGGRAPH_INTENTS = {
    "marketing_plan", "anomaly_diagnosis", "report_generation",
    "store_operation", "financial_analysis", "data_management",
    "competitor_analysis",
}


def _route_intent(query: str) -> str:
    """Fast keyword-based routing: return 'langgraph' or 'react'."""
    q = query.lower()
    # high-stakes → LangGraph with HITL
    if any(w in q for w in ["添加", "增加", "新增", "录入", "删除", "修改", "导入",
                             "报告", "战报", "总结", "报表",
                             "营销", "活动", "文案", "推广", "方案",
                             "下降", "异常", "退单", "退款", "毛利", "为什么", "飙升",
                             "排班", "打卡", "考勤", "开店", "关店", "设备", "库存", "盘点",
                             "成本", "利润", "预算", "投资回报", "回报率",
                             "竞品", "竞争对手", "同行", "市场份额", "定价"]):
        return "langgraph"
    # quick queries → ReAct
    return "react"


class ReactRequest(BaseModel):
    query: str
    store_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    history: Optional[list[dict]] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class AgentFormPreviewRequest(BaseModel):
    query: str
    store_id: Optional[int] = None
    history: Optional[list[dict]] = None


class AgentFormSubmitRequest(BaseModel):
    form_id: str
    rows: list[dict]
    confirm: bool = False


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/stream-diagnose")
async def stream_diagnose(
    query: str = Query(..., min_length=1, max_length=500),
    store_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
):
    """Stream LangGraph multi-agent diagnosis via SSE (direct call, no auto-route)."""
    return EventSourceResponse(
        run_agent_stream(query, store_id=store_id, start_date=start_date, end_date=end_date),
        media_type="text/event-stream; charset=utf-8",
    )


@router.post("/stream")
async def stream_auto(body: ReactRequest):
    """Auto-route to LangGraph or ReAct based on query intent.

    Accepts optional api_key / base_url / model from the frontend Settings page.
    When provided, they override the server-level .env configuration.
    """
    from app.services.deepseek_client import set_request_context, clear_request_context

    set_request_context(api_key=body.api_key, base_url=body.base_url, model=body.model)

    async def _wrap(gen):
        try:
            async for event in gen:
                yield event
        except Exception as exc:
            import json, logging
            logging.getLogger(__name__).exception("Agent stream crashed")
            yield json.dumps({
                "type": "error", "node": "report_generator",
                "title": "❌ 执行异常", "content": f"Agent 执行异常: {exc}",
                "done": True,
            }, ensure_ascii=False)
            yield json.dumps({
                "type": "end", "node": "end",
                "done": True, "content": "",
            }, ensure_ascii=False)
        finally:
            clear_request_context()

    route = _route_intent(body.query)
    if route == "langgraph":
        return EventSourceResponse(
            _wrap(run_agent_stream(
                body.query,
                store_id=body.store_id,
                start_date=body.start_date,
                end_date=body.end_date,
            )),
            media_type="text/event-stream; charset=utf-8",
        )
    return EventSourceResponse(
        _wrap(run_react_agent_stream(
            body.query,
            store_id=body.store_id,
            start_date=body.start_date,
            end_date=body.end_date,
            history=body.history,
        )),
        media_type="text/event-stream; charset=utf-8",
    )


@router.post("/stream-react")
async def stream_react(body: ReactRequest):
    """Stream ReAct Agent (autonomous tool selection) via SSE.

    Accepts POST with JSON body: {query, store_id?, start_date?, end_date?, history?}
    history is a list of {role, content} from previous turns, enabling multi-turn conversation.
    """
    return EventSourceResponse(
        run_react_agent_stream(
            body.query,
            store_id=body.store_id,
            start_date=body.start_date,
            end_date=body.end_date,
            history=body.history,
        ),
        media_type="text/event-stream; charset=utf-8",
    )


@router.post("/forms/preview")
def preview_form(
    body: AgentFormPreviewRequest,
    _user: User = Depends(get_current_user),
):
    """Generate a fillable business-operation form from natural language."""
    return {
        "code": 0,
        "data": preview_agent_form(
            query=body.query,
            store_id=body.store_id,
            history=body.history,
        ),
        "message": "ok",
    }


@router.post("/forms/submit")
def submit_form(
    body: AgentFormSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Validate and execute a submitted agent form."""
    return submit_agent_form(
        db=db,
        form_id=body.form_id,
        rows=body.rows,
        confirm=body.confirm,
        user_id=user.id,
    )


@router.get("/approvals")
def list_approvals(status: str = Query("pending"), db: Session = Depends(get_db)):
    """List HITL approval requests."""
    q = db.query(AgentApproval)
    if status != "all":
        q = q.filter(AgentApproval.status == status)
    rows = q.order_by(AgentApproval.created_at.desc()).limit(20).all()
    return {
        "code": 0,
        "data": [
            {
                "id": r.id,
                "session_id": r.session_id,
                "trace_id": r.trace_id,
                "node_name": r.node_name,
                "proposal": r.proposal,
                "estimated_cost": r.estimated_cost,
                "status": r.status,
                "reviewer_comment": r.reviewer_comment,
                "created_at": str(r.created_at),
                "reviewed_at": str(r.reviewed_at) if r.reviewed_at else None,
            }
            for r in rows
        ],
        "message": "ok",
    }


@router.post("/approve")
def approve_proposal(
    approval_id: int = Body(...),
    action: str = Body(...),  # approve / reject / revise
    comment: str = Body(""),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Approve, reject, or request revision for a HITL proposal."""
    if action not in {"approve", "reject", "revise"}:
        return api_response(code=-1, message="action must be approve, reject, or revise")

    approval = db.query(AgentApproval).filter(AgentApproval.id == approval_id).first()
    if not approval:
        return api_response(code=-1, message="Approval not found")
    if approval.status != "pending":
        return api_response(code=-1, message="Already reviewed")

    approval.status = {"approve": "approved", "reject": "rejected", "revise": "revise"}[action]
    approval.reviewer_comment = comment
    approval.reviewed_at = datetime.datetime.now()
    trace = db.query(AgentTrace).filter(AgentTrace.trace_id == approval.trace_id).first()
    campaign_id = None
    if action == "approve":
        campaign = MarketingCampaign(
            store_id=trace.store_id if trace else None,
            campaign_name="AI 审批通过活动草稿",
            channel="全渠道",
            status="draft",
            target_audience="门店会员与高潜客群",
            budget=approval.estimated_cost or 0,
            content_text=approval.proposal,
        )
        db.add(campaign)
        db.flush()
        campaign_id = campaign.id

    if trace:
        steps = json.loads(trace.steps_json or "[]")
        steps.append({
            "node": "human_approval",
            "time": datetime.datetime.now().isoformat(),
            "duration_ms": 0,
            "input_summary": approval.proposal[:180],
            "event": {
                "type": "approval_update",
                "title": "审批已更新",
                "content": f"Proposal {approval.status}",
                "trace_id": approval.trace_id,
                "node": "human_approval",
                "approval_id": approval.id,
                "campaign_id": campaign_id,
                "done": True,
            },
        })
        trace.steps_json = json.dumps(steps, ensure_ascii=False)
        trace.updated_at = datetime.datetime.now()
    db.commit()

    return {
        "code": 0,
        "data": {"id": approval.id, "status": approval.status, "trace_id": approval.trace_id, "campaign_id": campaign_id},
        "message": f"Proposal {approval.status}",
    }


@router.get("/stream-resume")
async def stream_resume(
    trace_id: str = Query(..., min_length=1),
    _user: User = Depends(get_current_user),
):
    """Resume Phase 2 (copywriter -> report_generator) via SSE after HITL approval.

    Call ``POST /api/agent/approve`` first to mark the proposal as approved,
    then open this SSE endpoint to stream the remaining Agent nodes.
    """
    return EventSourceResponse(
        resume_agent_stream(trace_id),
        media_type="text/event-stream; charset=utf-8",
    )


@router.get("/traces")
def list_traces(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Return recent agent traces for timeline browsing."""
    rows = db.query(AgentTrace).order_by(AgentTrace.created_at.desc()).limit(limit).all()
    return {
        "code": 0,
        "data": [
            {
                "trace_id": r.trace_id,
                "user_query": r.user_query,
                "store_id": r.store_id,
                "status": r.status,
                "created_at": str(r.created_at),
                "updated_at": str(r.updated_at),
                "step_count": len(json.loads(r.steps_json or "[]")),
            }
            for r in rows
        ],
        "message": "ok",
    }


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str, db: Session = Depends(get_db)):
    """Return one trace with timeline steps."""
    trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
    if not trace:
        return api_response(code=-1, message="Trace not found")
    return {
        "code": 0,
        "data": {
            "trace_id": trace.trace_id,
            "user_query": trace.user_query,
            "store_id": trace.store_id,
            "status": trace.status,
            "steps": json.loads(trace.steps_json or "[]"),
            "final_answer": trace.final_answer,
            "created_at": str(trace.created_at),
            "updated_at": str(trace.updated_at),
        },
        "message": "ok",
    }


@router.post("/replay/{trace_id}")
def replay_trace(trace_id: str, db: Session = Depends(get_db)):
    """MVP replay: return saved trace steps for frontend re-display."""
    trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
    if not trace:
        return api_response(code=-1, message="Trace not found")
    return {
        "code": 0,
        "data": {
            "trace_id": trace.trace_id,
            "mode": "saved_trace_replay",
            "steps": json.loads(trace.steps_json or "[]"),
            "final_answer": trace.final_answer,
        },
        "message": "ok",
    }
@router.delete("/traces/{trace_id}")
def delete_trace(
    trace_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete a single agent trace."""
    trace = db.query(AgentTrace).filter(AgentTrace.trace_id == trace_id).first()
    if not trace:
        return api_response(code=-1, message="Trace not found")
    db.delete(trace)
    db.commit()
    return api_response(message="Trace deleted")


@router.delete("/traces")
def clear_all_traces(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete all agent traces."""
    count = db.query(AgentTrace).delete()
    db.commit()
    return api_response(data={"deleted": count}, message=f"Deleted {count} traces")

