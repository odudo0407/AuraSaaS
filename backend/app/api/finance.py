"""Finance API — financial overview derived from business metrics."""

import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.models import BusinessMetricsDaily, Store

router = APIRouter(prefix="/api/finance", tags=["finance"])


def _latest_date(db: Session) -> datetime.date:
    d = db.query(func.max(BusinessMetricsDaily.date)).scalar()
    return d or datetime.date.today()


@router.get("/overview")
def finance_overview(
    store_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    """Financial overview derived from business metrics."""
    today = _latest_date(db)
    end = datetime.date.fromisoformat(end_date) if end_date else today
    start = datetime.date.fromisoformat(start_date) if start_date else end - datetime.timedelta(days=29)
    prev_end = start - datetime.timedelta(days=1)
    prev_start = prev_end - datetime.timedelta(days=(end - start).days)

    def agg(s, e):
        q = db.query(
            func.sum(BusinessMetricsDaily.revenue).label("revenue"),
            func.sum(BusinessMetricsDaily.total_revenue).label("total_revenue"),
            func.sum(BusinessMetricsDaily.order_count).label("orders"),
            func.avg(BusinessMetricsDaily.gross_margin).label("margin"),
            func.sum(BusinessMetricsDaily.platform_commission).label("commission"),
            func.sum(BusinessMetricsDaily.net_profit).label("profit"),
        ).filter(BusinessMetricsDaily.date >= s, BusinessMetricsDaily.date <= e)
        if store_id:
            q = q.filter(BusinessMetricsDaily.store_id == store_id)
        return q.first()

    cur = agg(start, end)
    prev = agg(prev_start, prev_end)

    cur_rev = cur.revenue or cur.total_revenue or 0
    prev_rev = prev.revenue or prev.total_revenue or 0
    cur_profit = cur.profit or 0
    prev_profit = prev.profit or 0
    cur_commission = cur.commission or 0

    # Estimate cost breakdown from revenue
    food_cost = cur_rev * 0.35
    labor_cost = cur_rev * 0.22
    rent_cost = cur_rev * 0.12
    other_cost = cur_rev * 0.08
    total_expense = food_cost + labor_cost + rent_cost + cur_commission + other_cost

    def growth(cur_v, prev_v):
        return round((cur_v - prev_v) / prev_v * 100, 1) if prev_v else 0

    return {
        "code": 0,
        "data": {
            "total_revenue": round(cur_rev, 2),
            "total_expense": round(total_expense, 2),
            "net_profit": round(cur_profit, 2),
            "revenue_growth": growth(cur_rev, prev_rev),
            "profit_growth": growth(cur_profit, prev_profit),
            "cost_breakdown": [
                {"name": "食材采购", "amount": round(food_cost, 2), "pct": round(food_cost / total_expense * 100, 1) if total_expense else 0},
                {"name": "人工成本", "amount": round(labor_cost, 2), "pct": round(labor_cost / total_expense * 100, 1) if total_expense else 0},
                {"name": "房租水电", "amount": round(rent_cost, 2), "pct": round(rent_cost / total_expense * 100, 1) if total_expense else 0},
                {"name": "平台抽佣", "amount": round(cur_commission, 2), "pct": round(cur_commission / total_expense * 100, 1) if total_expense else 0},
                {"name": "其他支出", "amount": round(other_cost, 2), "pct": round(other_cost / total_expense * 100, 1) if total_expense else 0},
            ],
            "range": {"start": str(start), "end": str(end)},
        },
        "message": "ok",
    }


@router.get("/transactions")
def finance_transactions(
    store_id: int = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Transaction records derived from daily metrics."""
    today = _latest_date(db)
    start = today - datetime.timedelta(days=days - 1)
    q = db.query(BusinessMetricsDaily).filter(
        BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= today
    )
    if store_id:
        q = q.filter(BusinessMetricsDaily.store_id == store_id)
    rows = q.order_by(BusinessMetricsDaily.date.desc()).limit(20).all()

    stores_map = {s.id: s.name for s in db.query(Store).all()}
    transactions = []
    for r in rows:
        store_name = stores_map.get(r.store_id, f"门店{r.store_id}")
        rev = r.revenue or r.total_revenue or 0
        if rev > 0:
            transactions.append({
                "time": r.date.strftime("%m-%d"),
                "type": "收入",
                "desc": f"{store_name} - 日营收",
                "amount": round(rev, 2),
            })
        commission = r.platform_commission or 0
        if commission > 0:
            transactions.append({
                "time": r.date.strftime("%m-%d"),
                "type": "支出",
                "desc": f"{store_name} - 平台抽佣",
                "amount": -round(commission, 2),
            })

    return {"code": 0, "data": transactions, "message": "ok"}
