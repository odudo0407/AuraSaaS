"""Dashboard API — multi-store filtering, ranking, heatmaps and export."""

import csv
import datetime
import io
import random
from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from app.core.deps import get_current_user
from app.database import get_db
from app.models.models import (
    AgentMemory,
    AgentTrace,
    BusinessMetricsDaily,
    CampaignResult,
    ExternalFactor,
    MarketingCampaign,
    SkuPerformance,
    Staff,
    Store,
    User,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _parse_date(value: str | None, default: datetime.date) -> datetime.date:
    if not value:
        return default
    return datetime.date.fromisoformat(value)


def _latest_date(db: Session) -> datetime.date:
    """Get the latest date with data, fallback to today."""
    d = db.query(func.max(BusinessMetricsDaily.date)).scalar()
    return d or datetime.date.today()


def _metric_column(metric: str):
    return {
        "revenue": BusinessMetricsDaily.revenue,
        "total_revenue": BusinessMetricsDaily.total_revenue,
        "order_count": BusinessMetricsDaily.order_count,
        "gross_margin": BusinessMetricsDaily.gross_margin,
        "refund_rate": BusinessMetricsDaily.refund_rate,
        "avg_ticket": BusinessMetricsDaily.avg_ticket,
    }.get(metric, BusinessMetricsDaily.revenue)


@router.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    """Return all stores for the store selector."""
    latest = _latest_date(db)
    stores = db.query(Store).order_by(Store.id).all()
    metric_rows = db.query(
        BusinessMetricsDaily.store_id,
        func.sum(BusinessMetricsDaily.revenue).label("revenue"),
        func.sum(BusinessMetricsDaily.total_revenue).label("total_revenue"),
        func.sum(BusinessMetricsDaily.order_count).label("orders"),
    ).filter(BusinessMetricsDaily.date == latest).group_by(BusinessMetricsDaily.store_id).all()
    metric_map = {row.store_id: row for row in metric_rows}
    return {
        "code": 0,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "city": s.city,
                "address": s.address,
                "area": s.area,
                "store_type": s.store_type,
                "manager_name": s.manager_name,
                "status": s.status,
                "seats": s.seats,
                "staff_count": s.staff_count,
                "rating": s.rating,
                "revenue": round((metric_map.get(s.id).revenue or metric_map.get(s.id).total_revenue or 0), 2) if metric_map.get(s.id) else 0,
                "orders": int(metric_map.get(s.id).orders or 0) if metric_map.get(s.id) else 0,
                "achievement": min(100, round(((metric_map.get(s.id).revenue or metric_map.get(s.id).total_revenue or 0) / 20000) * 100)) if metric_map.get(s.id) else 0,
            }
            for s in stores
        ],
        "message": "ok",
    }


@router.get("/overview")
def get_overview(
    store_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    """Return KPI overview. Supports optional store and date range filters."""
    today = _latest_date(db)
    end = _parse_date(end_date, today)
    start = _parse_date(start_date, end - datetime.timedelta(days=29))
    period_days = max((end - start).days + 1, 1)
    prev_end = start - datetime.timedelta(days=1)
    prev_start = prev_end - datetime.timedelta(days=period_days - 1)

    def agg(range_start, range_end):
        q = db.query(
            func.sum(BusinessMetricsDaily.revenue).label("revenue"),
            func.sum(BusinessMetricsDaily.total_revenue).label("total_revenue"),
            func.sum(BusinessMetricsDaily.order_count).label("orders"),
            func.avg(BusinessMetricsDaily.avg_ticket).label("avg_ticket"),
            func.avg(BusinessMetricsDaily.avg_order_value).label("aov"),
            func.avg(BusinessMetricsDaily.gross_margin).label("gross_margin"),
            func.avg(BusinessMetricsDaily.refund_rate).label("refund_rate"),
            func.avg(BusinessMetricsDaily.delivery_ratio).label("delivery_ratio"),
            func.sum(BusinessMetricsDaily.platform_commission).label("commission"),
            func.sum(BusinessMetricsDaily.net_profit).label("profit"),
            func.sum(BusinessMetricsDaily.new_customers).label("new_customers"),
            func.sum(BusinessMetricsDaily.returning_customers).label("returning_customers"),
        ).filter(BusinessMetricsDaily.date >= range_start, BusinessMetricsDaily.date <= range_end)
        if store_id:
            q = q.filter(BusinessMetricsDaily.store_id == store_id)
        return q.first()

    cur = agg(start, end)
    prev = agg(prev_start, prev_end)

    cur_revenue = cur.revenue or cur.total_revenue or 0
    prev_revenue = prev.revenue or prev.total_revenue or 0
    cur_orders = cur.orders or 0
    prev_orders = prev.orders or 0

    def growth(current, previous):
        return round((current - previous) / previous * 100, 2) if previous else 0

    return {
        "code": 0,
        "data": {
            "range": {"start_date": str(start), "end_date": str(end), "store_id": store_id},
            "kpis": {
                "revenue": round(cur_revenue, 2),
                "order_count": int(cur_orders),
                "avg_ticket": round(cur.avg_ticket or cur.aov or 0, 2),
                "gross_margin": round((cur.gross_margin or 0) * 100, 2),
                "refund_rate": round((cur.refund_rate or 0) * 100, 2),
                "delivery_ratio": round((cur.delivery_ratio or 0) * 100, 2),
                "new_customers": int(cur.new_customers or 0),
                "returning_customers": int(cur.returning_customers or 0),
                "net_profit": round(cur.profit or 0, 2),
            },
            "today": {
                "revenue": round(cur_revenue, 2),
                "order_count": int(cur_orders),
                "avg_order_value": round(cur.avg_ticket or cur.aov or 0, 2),
            },
            "month": {
                "total_revenue": round(cur_revenue, 2),
                "total_orders": int(cur_orders),
                "avg_order_value": round(cur.avg_ticket or cur.aov or 0, 2),
                "total_commission": round(cur.commission or 0, 2),
                "net_profit": round(cur.profit or 0, 2),
            },
            "mom_growth": {
                "revenue_pct": growth(cur_revenue, prev_revenue),
                "orders_pct": growth(cur_orders, prev_orders),
            },
        },
        "message": "ok",
    }


@router.get("/store-ranking")
def get_store_ranking(
    metric: str = Query("revenue"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """Rank stores by revenue, order_count, gross_margin, or refund_rate."""
    today = _latest_date(db)
    end = _parse_date(end_date, today)
    start = _parse_date(start_date, end - datetime.timedelta(days=29))
    metric_col = _metric_column(metric)
    aggregate = func.avg(metric_col) if metric in {"gross_margin", "refund_rate", "avg_ticket"} else func.sum(metric_col)

    rows = db.query(
        Store.id,
        Store.name,
        Store.city,
        aggregate.label("metric_value"),
        func.sum(BusinessMetricsDaily.revenue).label("revenue"),
        func.sum(BusinessMetricsDaily.order_count).label("orders"),
        func.avg(BusinessMetricsDaily.gross_margin).label("gross_margin"),
        func.avg(BusinessMetricsDaily.refund_rate).label("refund_rate"),
    ).join(BusinessMetricsDaily, BusinessMetricsDaily.store_id == Store.id).filter(
        BusinessMetricsDaily.date >= start,
        BusinessMetricsDaily.date <= end,
    ).group_by(Store.id).order_by(desc("metric_value") if order != "asc" else asc("metric_value")).all()

    return {
        "code": 0,
        "data": [
            {
                "rank": idx + 1,
                "store_id": row.id,
                "store_name": row.name,
                "city": row.city,
                "metric": metric,
                "metric_value": round(row.metric_value or 0, 4),
                "revenue": round(row.revenue or 0, 2),
                "order_count": int(row.orders or 0),
                "gross_margin": round((row.gross_margin or 0) * 100, 2),
                "refund_rate": round((row.refund_rate or 0) * 100, 2),
            }
            for idx, row in enumerate(rows)
        ],
        "message": "ok",
    }


@router.get("/trends")
def get_trends(days: int = Query(30, ge=7, le=90), store_id: int = Query(None), db: Session = Depends(get_db)):
    """Return daily trend data. Optional store filtering."""
    today = _latest_date(db)
    start = today - datetime.timedelta(days=days - 1)
    q = db.query(BusinessMetricsDaily).filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= today)
    if store_id:
        q = q.filter(BusinessMetricsDaily.store_id == store_id)
    rows = q.order_by(BusinessMetricsDaily.date).all()

    return {
        "code": 0,
        "data": {
            "dates": [str(r.date) for r in rows],
            "revenue": [r.revenue or r.total_revenue for r in rows],
            "orders": [r.order_count for r in rows],
            "avg_order_value": [r.avg_ticket or r.avg_order_value for r in rows],
            "commission": [r.platform_commission for r in rows],
            "net_profit": [r.net_profit for r in rows],
        },
        "message": "ok",
    }


@router.get("/trend")
def get_trend_alias(
    store_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Session = Depends(get_db),
):
    """Return selected store trend and global average trend for chart comparison."""
    today = _latest_date(db)
    end = _parse_date(end_date, today)
    start = _parse_date(start_date, end - datetime.timedelta(days=29))

    base = db.query(
        BusinessMetricsDaily.date,
        func.sum(BusinessMetricsDaily.revenue).label("revenue"),
        func.sum(BusinessMetricsDaily.order_count).label("orders"),
    ).filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= end)
    if store_id:
        selected_rows = base.filter(BusinessMetricsDaily.store_id == store_id).group_by(BusinessMetricsDaily.date).order_by(BusinessMetricsDaily.date).all()
    else:
        selected_rows = base.group_by(BusinessMetricsDaily.date).order_by(BusinessMetricsDaily.date).all()

    avg_rows = db.query(
        BusinessMetricsDaily.date,
        (func.sum(BusinessMetricsDaily.revenue) / func.count(func.distinct(BusinessMetricsDaily.store_id))).label("avg_revenue"),
    ).filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= end).group_by(BusinessMetricsDaily.date).order_by(BusinessMetricsDaily.date).all()
    avg_map = {row.date: row.avg_revenue for row in avg_rows}

    return {
        "code": 0,
        "data": [
            {
                "date": str(row.date),
                "store_revenue": round(row.revenue or 0, 2),
                "global_avg_revenue": round(avg_map.get(row.date) or 0, 2),
                "orders": int(row.orders or 0),
            }
            for row in selected_rows
        ],
        "message": "ok",
    }


@router.get("/top-skus")
def get_top_skus(limit: int = Query(5, ge=1, le=20), days: int = Query(7, ge=1, le=30), store_id: int = Query(None), db: Session = Depends(get_db)):
    """Return top-selling SKUs. Optional store filtering."""
    today = _latest_date(db)
    start = today - datetime.timedelta(days=days - 1)
    q = db.query(
        SkuPerformance.sku_name,
        SkuPerformance.category,
        func.sum(SkuPerformance.sales_count).label("total_sales"),
        func.sum(SkuPerformance.sales_volume).label("total_volume"),
        func.sum(SkuPerformance.revenue).label("total_revenue"),
        func.avg(SkuPerformance.gross_margin).label("avg_margin"),
        func.max(SkuPerformance.cost_warning).label("cost_warning"),
    ).filter(SkuPerformance.date >= start, SkuPerformance.date <= today)
    if store_id:
        q = q.filter(SkuPerformance.store_id == store_id)
    rows = q.group_by(SkuPerformance.sku_name, SkuPerformance.category).order_by(desc("total_sales")).limit(limit).all()

    return {
        "code": 0,
        "data": [
            {
                "sku_name": r.sku_name,
                "category": r.category,
                "total_sales": int(r.total_sales or r.total_volume or 0),
                "total_revenue": round(r.total_revenue or 0, 2),
                "avg_margin": round((r.avg_margin or 0) * 100, 1),
                "cost_warning": bool(r.cost_warning),
            }
            for r in rows
        ],
        "message": "ok",
    }


@router.get("/sku-heatmap")
def get_sku_heatmap(store_id: int = Query(None), days: int = Query(14, ge=1, le=90), db: Session = Depends(get_db)):
    """Return SKU sales/margin/refund matrix data."""
    today = _latest_date(db)
    start = today - datetime.timedelta(days=days - 1)
    q = db.query(
        SkuPerformance.sku_name,
        SkuPerformance.category,
        func.sum(SkuPerformance.sales_count).label("sales"),
        func.sum(SkuPerformance.revenue).label("revenue"),
        func.avg(SkuPerformance.gross_margin).label("margin"),
        func.avg(SkuPerformance.refund_rate).label("refund_rate"),
        func.sum(SkuPerformance.stockout_count).label("stockouts"),
    ).filter(SkuPerformance.date >= start, SkuPerformance.date <= today)
    if store_id:
        q = q.filter(SkuPerformance.store_id == store_id)
    rows = q.group_by(SkuPerformance.sku_name, SkuPerformance.category).order_by(desc("sales")).all()
    return {
        "code": 0,
        "data": [
            {
                "sku_name": row.sku_name,
                "category": row.category,
                "sales_count": int(row.sales or 0),
                "revenue": round(row.revenue or 0, 2),
                "gross_margin": round((row.margin or 0) * 100, 2),
                "refund_rate": round((row.refund_rate or 0) * 100, 2),
                "stockout_count": int(row.stockouts or 0),
            }
            for row in rows
        ],
        "message": "ok",
    }


@router.get("/heatmap")
def get_heatmap(store_id: int = Query(None), db: Session = Depends(get_db)):
    """Return hourly order distribution heatmap data (7 days x 17 hours)."""
    return get_traffic_heatmap(store_id=store_id, days=7, db=db)


@router.get("/traffic-heatmap")
def get_traffic_heatmap(store_id: int = Query(None), days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    """Return hour/day traffic heatmap data generated from daily order totals."""
    # Find the latest date with data instead of using today
    latest = db.query(func.max(BusinessMetricsDaily.date)).scalar()
    if not latest:
        return {"code": 0, "data": [], "message": "ok"}
    end = latest
    start = end - datetime.timedelta(days=days - 1)
    q = db.query(BusinessMetricsDaily).filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= end)
    if store_id:
        q = q.filter(BusinessMetricsDaily.store_id == store_id)
    rows = q.all()

    # Deterministic hourly distribution based on date+hour hash
    heatmap = []
    for r in rows:
        dow = r.date.weekday()
        for hour in range(6, 23):
            # Deterministic percentage based on date and hour
            seed = (r.date.toordinal() * 100 + hour * 7) % 100
            if 11 <= hour <= 13:
                pct = 0.12 + (seed % 6) * 0.01  # 0.12 - 0.17
            elif 17 <= hour <= 20:
                pct = 0.10 + (seed % 5) * 0.01  # 0.10 - 0.14
            elif 7 <= hour <= 9:
                pct = 0.05 + (seed % 3) * 0.01  # 0.05 - 0.07
            else:
                pct = 0.02 + (seed % 3) * 0.01  # 0.02 - 0.04
            heatmap.append({
                "date": str(r.date),
                "day_of_week": dow,
                "hour": hour,
                "orders": max(1, int(r.order_count * pct)),
            })
    return {"code": 0, "data": heatmap, "message": "ok"}


@router.get("/external-factors")
def get_external_factors(days: int = Query(30), store_id: int = Query(None), db: Session = Depends(get_db)):
    """Return recent external factors for attribution analysis."""
    today = _latest_date(db)
    start = today - datetime.timedelta(days=days - 1)
    q = db.query(ExternalFactor).filter(ExternalFactor.date >= start)
    if store_id:
        q = q.filter(ExternalFactor.store_id == store_id)
    rows = q.order_by(ExternalFactor.date.desc()).all()
    return {
        "code": 0,
        "data": [
            {
                "date": str(r.date),
                "store_id": r.store_id,
                "type": r.factor_type,
                "description": r.description,
                "impact": r.impact_level,
                "weather": r.weather,
                "temperature": r.temperature,
                "holiday_name": r.holiday_name,
                "nearby_event": r.nearby_event,
                "traffic_level": r.traffic_level,
            }
            for r in rows
        ],
        "message": "ok",
    }


@router.get("/campaigns")
def list_campaigns(store_id: int = Query(None), db: Session = Depends(get_db)):
    """Return marketing campaigns."""
    q = db.query(MarketingCampaign)
    if store_id:
        q = q.filter(MarketingCampaign.store_id == store_id)
    rows = q.order_by(MarketingCampaign.created_at.desc()).limit(20).all()
    return {
        "code": 0,
        "data": [
            {
                "id": r.id,
                "store_id": r.store_id,
                "name": r.campaign_name,
                "channel": r.channel,
                "status": r.status,
                "budget": r.budget,
                "conversion_rate": r.conversion_rate,
                "spend": r.spend,
                "revenue_generated": r.revenue_generated,
                "content_text": r.content_text,
                "created_at": str(r.created_at),
            }
            for r in rows
        ],
        "message": "ok",
    }


@router.get("/campaigns/stats")
def get_campaign_stats(store_id: int = Query(None), db: Session = Depends(get_db)):
    """Return live marketing KPI stats from campaign records."""
    q = db.query(MarketingCampaign)
    if store_id:
        q = q.filter(MarketingCampaign.store_id == store_id)

    rows = q.all()
    total = len(rows)
    active = sum(1 for row in rows if row.status == "active")
    conversion_values = [float(row.conversion_rate or 0) for row in rows if row.conversion_rate is not None]
    avg_conversion = sum(conversion_values) / len(conversion_values) if conversion_values else 0
    revenue = sum(float(row.revenue_generated or 0) for row in rows)
    spend = sum(float(row.spend or 0) for row in rows)
    budget = sum(float(row.budget or 0) for row in rows)
    roi_base = spend if spend > 0 else budget
    roi = revenue / roi_base if roi_base > 0 else 0

    return {
        "code": 0,
        "data": {
            "total_campaigns": total,
            "active_campaigns": active,
            "avg_conversion_rate": round(avg_conversion, 4),
            "marketing_roi": round(roi, 2),
            "revenue_generated": round(revenue, 2),
            "spend": round(spend, 2),
            "budget": round(budget, 2),
        },
        "message": "ok",
    }


@router.get("/export")
def export_report(
    store_id: int = Query(None),
    days: int = Query(30),
    format: str = Query("csv"),
    db: Session = Depends(get_db),
):
    """Export dashboard data as CSV or Excel."""
    today = _latest_date(db)
    start = today - datetime.timedelta(days=days - 1)
    q = db.query(BusinessMetricsDaily).filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= today)
    if store_id:
        q = q.filter(BusinessMetricsDaily.store_id == store_id)
    rows = q.order_by(BusinessMetricsDaily.date).all()

    records = [
        {
            "日期": r.date,
            "门店ID": r.store_id,
            "营收": r.revenue or r.total_revenue,
            "订单数": r.order_count,
            "客单价": r.avg_ticket or r.avg_order_value,
            "毛利率": r.gross_margin,
            "退单率": r.refund_rate,
            "外卖占比": r.delivery_ratio,
            "平台抽佣": r.platform_commission,
            "净利润": r.net_profit,
        }
        for r in rows
    ]

    if format.lower() in {"xlsx", "excel"}:
        import pandas as pd
        output = io.BytesIO()
        pd.DataFrame(records).to_excel(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=report_{today}.xlsx"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(records[0].keys()) if records else ["日期", "门店ID", "营收"])
    writer.writeheader()
    writer.writerows(records)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{today}.csv"},
    )


# ============ Store CRUD ============

@router.post("/stores/batch-delete")
def batch_delete_stores(
    ids: list[int] = Body(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete stores and their related operation records."""
    unique_ids = sorted({int(item) for item in ids if item})
    if not unique_ids:
        return {"code": -1, "data": {"deleted": 0}, "message": "No store ids provided"}

    stores = db.query(Store).filter(Store.id.in_(unique_ids)).all()
    for model in [CampaignResult, BusinessMetricsDaily, SkuPerformance, ExternalFactor, Staff, MarketingCampaign, AgentMemory, AgentTrace]:
        db.query(model).filter(model.store_id.in_(unique_ids)).delete(synchronize_session=False)
    db.query(Store).filter(Store.id.in_(unique_ids)).delete(synchronize_session=False)
    db.commit()
    return {"code": 0, "data": {"deleted": len(stores), "ids": unique_ids}, "message": f"Deleted {len(stores)} stores"}


@router.get("/stores/{store_id}")
def get_store_detail(store_id: int, db: Session = Depends(get_db)):
    """Get single store details."""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        return {"code": -1, "data": None, "message": "门店不存在"}
    today = _latest_date(db)
    start = today - datetime.timedelta(days=29)
    agg = db.query(
        func.sum(BusinessMetricsDaily.revenue).label("revenue"),
        func.sum(BusinessMetricsDaily.order_count).label("orders"),
        func.avg(BusinessMetricsDaily.gross_margin).label("margin"),
    ).filter(
        BusinessMetricsDaily.store_id == store_id,
        BusinessMetricsDaily.date >= start,
    ).first()
    return {
        "code": 0,
        "data": {
            "id": store.id, "name": store.name, "city": store.city,
            "address": store.address, "area": store.area,
            "store_type": store.store_type, "manager_name": store.manager_name,
            "status": store.status, "seats": store.seats,
            "staff_count": store.staff_count, "rating": store.rating,
            "opened_at": str(store.opened_at) if store.opened_at else None,
            "month_revenue": round(agg.revenue or 0, 2),
            "month_orders": int(agg.orders or 0),
            "avg_margin": round((agg.margin or 0) * 100, 2),
        },
        "message": "ok",
    }


@router.post("/stores")
def create_store(body: dict, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Create a new store."""
    store = Store(
        name=body.get("name", "新门店"),
        city=body.get("city", ""),
        address=body.get("address", ""),
        area=body.get("area", ""),
        store_type=body.get("store_type", "coffee_shop"),
        manager_name=body.get("manager_name", ""),
        status="open",
        seats=body.get("seats", 0),
        staff_count=body.get("staff_count", 0),
        rating=body.get("rating", 4.5),
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return {"code": 0, "data": {"id": store.id, "name": store.name}, "message": "门店已创建"}


@router.put("/stores/{store_id}")
def update_store(store_id: int, body: dict, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Update store info."""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        return {"code": -1, "data": None, "message": "门店不存在"}
    for field in ["name", "city", "address", "area", "manager_name", "status", "seats", "staff_count", "rating"]:
        if field in body:
            setattr(store, field, body[field])
    db.commit()
    return {"code": 0, "data": {"id": store.id, "name": store.name}, "message": "门店已更新"}


# ============ Campaign CRUD ============

@router.post("/campaigns/batch-delete")
def batch_delete_campaigns(
    ids: list[int] = Body(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete multiple marketing campaigns."""
    unique_ids = sorted({int(item) for item in ids if item})
    if not unique_ids:
        return {"code": -1, "data": {"deleted": 0}, "message": "No campaign ids provided"}

    campaigns = db.query(MarketingCampaign).filter(MarketingCampaign.id.in_(unique_ids)).all()
    db.query(CampaignResult).filter(CampaignResult.campaign_id.in_(unique_ids)).delete(synchronize_session=False)
    db.query(MarketingCampaign).filter(MarketingCampaign.id.in_(unique_ids)).delete(synchronize_session=False)
    db.commit()
    return {"code": 0, "data": {"deleted": len(campaigns), "ids": unique_ids}, "message": f"Deleted {len(campaigns)} campaigns"}


@router.post("/campaigns")
def create_campaign(body: dict, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Create a new marketing campaign."""
    campaign = MarketingCampaign(
        campaign_name=body.get("campaign_name") or body.get("name", "新活动"),
        channel=body.get("channel", "全渠道"),
        status=body.get("status", "draft"),
        target_audience=body.get("target_audience", ""),
        budget=body.get("budget", 0),
        content_text=body.get("content_text", ""),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return {"code": 0, "data": {"id": campaign.id, "name": campaign.campaign_name}, "message": "活动已创建"}


@router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, body: dict, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Update a marketing campaign."""
    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not campaign:
        return {"code": -1, "data": None, "message": "活动不存在"}
    for field in ["campaign_name", "channel", "status", "target_audience", "budget", "content_text"]:
        if field in body:
            setattr(campaign, field, body[field])
    db.commit()
    return {"code": 0, "data": {"id": campaign.id}, "message": "活动已更新"}


# ============ Products ============

@router.get("/products")
def list_products(
    limit: int = Query(20, ge=1, le=50),
    days: int = Query(7, ge=1, le=30),
    store_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """List products aggregated from SKU performance data."""
    today = _latest_date(db)
    start = today - datetime.timedelta(days=days - 1)
    q = db.query(
        SkuPerformance.sku_name,
        SkuPerformance.category,
        func.sum(SkuPerformance.sales_count).label("sales"),
        func.sum(SkuPerformance.revenue).label("revenue"),
        func.avg(SkuPerformance.gross_margin).label("margin"),
        func.avg(SkuPerformance.refund_rate).label("refund_rate"),
    ).filter(SkuPerformance.date >= start, SkuPerformance.date <= today)
    if store_id:
        q = q.filter(SkuPerformance.store_id == store_id)
    rows = q.group_by(SkuPerformance.sku_name, SkuPerformance.category).order_by(desc("sales")).limit(limit).all()

    return {
        "code": 0,
        "data": [
            {
                "name": r.sku_name,
                "category": r.category,
                "sales": int(r.sales or 0),
                "revenue": round(r.revenue or 0, 2),
                "margin": round((r.margin or 0) * 100, 1),
                "refund_rate": round((r.refund_rate or 0) * 100, 2),
            }
            for r in rows
        ],
        "message": "ok",
    }
