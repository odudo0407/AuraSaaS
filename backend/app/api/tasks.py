"""Tasks API — pending tasks, alerts, and auto-generated warnings."""

import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models.models import Task, BusinessMetricsDaily, SkuPerformance, Store, MarketingCampaign

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    status: str = Query("pending"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List tasks filtered by status. Auto-generates alerts if none exist."""
    # Auto-generate if no tasks exist
    if db.query(Task).count() == 0:
        generate_alerts(db=db)

    q = db.query(Task).filter(Task.status == status)
    rows = q.order_by(
        Task.urgency.desc(), Task.created_at.desc()
    ).limit(limit).all()

    return {
        "code": 0,
        "data": [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "type": r.task_type,
                "urgency": r.urgency,
                "status": r.status,
                "icon": r.icon,
                "tag": r.tag,
                "link_to": r.link_to,
                "time": r.created_at.strftime("%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ],
        "message": "ok",
    }


@router.post("/{task_id}/done")
def mark_done(task_id: int, db: Session = Depends(get_db)):
    """Mark a task as done."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return {"code": -1, "data": None, "message": "任务不存在"}
    task.status = "done"
    db.commit()
    return {"code": 0, "data": None, "message": "已标记完成"}


@router.post("/{task_id}/dismiss")
def dismiss_task(task_id: int, db: Session = Depends(get_db)):
    """Dismiss a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return {"code": -1, "data": None, "message": "任务不存在"}
    task.status = "dismissed"
    db.commit()
    return {"code": 0, "data": None, "message": "已忽略"}


@router.post("/generate")
def generate_alerts(db: Session = Depends(get_db)):
    """Run alert rules and generate tasks for current conditions."""
    latest = db.query(func.max(BusinessMetricsDaily.date)).scalar()
    today = latest or datetime.date.today()
    generated = []

    # Rule 1: Revenue drop — today vs yesterday per store
    yesterday = today - datetime.timedelta(days=1)
    for store in db.query(Store).all():
        today_rev = db.query(func.sum(BusinessMetricsDaily.revenue)).filter(
            BusinessMetricsDaily.store_id == store.id,
            BusinessMetricsDaily.date == today,
        ).scalar() or 0
        yest_rev = db.query(func.sum(BusinessMetricsDaily.revenue)).filter(
            BusinessMetricsDaily.store_id == store.id,
            BusinessMetricsDaily.date == yesterday,
        ).scalar() or 0
        if yest_rev > 0 and today_rev < yest_rev * 0.8:
            drop_pct = round((1 - today_rev / yest_rev) * 100, 1)
            _add_task(db, generated,
                title=f"{store.name} 营收环比下降 {drop_pct}%",
                description=f"今日营收 ¥{today_rev:,.0f}，昨日 ¥{yest_rev:,.0f}",
                task_type="cost", urgency="high",
                icon="⚠", tag="营收异常", link_to="/app/dashboard")

    # Rule 2: Low margin products
    low_margin = db.query(SkuPerformance.sku_name, func.avg(SkuPerformance.gross_margin).label("avg_m")).group_by(
        SkuPerformance.sku_name
    ).having(func.avg(SkuPerformance.gross_margin) < 0.3).limit(3).all()
    for sku in low_margin:
        _add_task(db, generated,
            title=f"商品「{sku.sku_name}」毛利率偏低 ({round(sku.avg_m*100, 1)}%)",
            description="建议检查成本结构或调整定价",
            task_type="inventory", urgency="medium",
            icon="⚠", tag="成本预警", link_to="/app/products")

    # Rule 3: Campaigns ending soon
    campaigns = db.query(MarketingCampaign).filter(MarketingCampaign.status == "active").all()
    for c in campaigns:
        _add_task(db, generated,
            title=f"营销活动「{c.campaign_name}」正在进行中",
            description=f"渠道: {c.channel}，预算: ¥{c.budget:,.0f}",
            task_type="marketing", urgency="low",
            icon="📣", tag="营销", link_to="/app/marketing")

    # Rule 4: High refund rate stores
    for store in db.query(Store).all():
        avg_refund = db.query(func.avg(BusinessMetricsDaily.refund_rate)).filter(
            BusinessMetricsDaily.store_id == store.id,
            BusinessMetricsDaily.date >= today - datetime.timedelta(days=7),
        ).scalar() or 0
        if avg_refund > 0.05:
            _add_task(db, generated,
                title=f"{store.name} 近7天退单率偏高 ({round(avg_refund*100, 1)}%)",
                description="建议排查服务质量和出品问题",
                task_type="cost", urgency="high",
                icon="⚠", tag="退单预警", link_to="/app/stores")

    # Rule 5: Generate monthly report reminder
    if today.day == 1:
        _add_task(db, generated,
            title="月度经营报表已生成",
            description=f"{today.year}年{today.month-1 or 12}月经营数据汇总",
            task_type="report", urgency="low",
            icon="📊", tag="报表", link_to="/app/reports")

    db.commit()
    return {"code": 0, "data": {"generated": len(generated)}, "message": f"生成 {len(generated)} 条预警"}


def _add_task(db, generated, title, description, task_type, urgency, icon, tag, link_to):
    """Add a task if not already pending with the same title."""
    existing = db.query(Task).filter(Task.title == title, Task.status == "pending").first()
    if existing:
        return
    task = Task(
        title=title, description=description,
        task_type=task_type, urgency=urgency,
        icon=icon, tag=tag, link_to=link_to,
    )
    db.add(task)
    generated.append(title)
