"""Generate AuraSaaS multi-store demo data with planned anomalies."""

import random
import datetime
from app.database import SessionLocal, engine
from app.models.models import (
    Base,
    User,
    Store,
    BusinessMetricsDaily,
    SkuPerformance,
    MarketingCampaign,
    CampaignResult,
    ExternalFactor,
    KnowledgeDocument,
    AgentMemory,
)

STORES = [
    {
        "name": "北京国贸店",
        "city": "北京",
        "address": "北京市朝阳区建国门外大街1号",
        "area": "国贸商圈",
        "store_type": "coffee_shop",
        "manager_name": "李然",
        "seats": 56,
        "staff_count": 9,
    },
    {
        "name": "上海静安店",
        "city": "上海",
        "address": "上海市静安区南京西路1601号",
        "area": "静安寺商圈",
        "store_type": "coffee_shop",
        "manager_name": "周晴",
        "seats": 48,
        "staff_count": 8,
    },
    {
        "name": "深圳南山店",
        "city": "深圳",
        "address": "深圳市南山区科技园高新南一道",
        "area": "科技园",
        "store_type": "coffee_shop",
        "manager_name": "陈宇",
        "seats": 64,
        "staff_count": 10,
    },
    {
        "name": "杭州西湖店",
        "city": "杭州",
        "address": "杭州市西湖区湖滨路步行街",
        "area": "西湖景区",
        "store_type": "coffee_shop",
        "manager_name": "王棠",
        "seats": 72,
        "staff_count": 11,
    },
]

SKU_CATALOG = [
    ("冰美式", "咖啡", 22, 4.8, 110, 0.008),
    ("生椰拿铁", "咖啡", 29, 8.5, 96, 0.010),
    ("燕麦拿铁", "咖啡", 31, 9.2, 78, 0.012),
    ("桂花冷萃", "咖啡", 33, 7.6, 54, 0.010),
    ("抹茶拿铁", "茶饮", 28, 8.0, 64, 0.014),
    ("柠檬气泡美式", "特调", 30, 7.0, 58, 0.011),
    ("可颂三明治", "轻食", 36, 17, 46, 0.018),
    ("牛油果鸡胸沙拉", "轻食", 42, 21, 35, 0.020),
    ("巴斯克蛋糕", "甜品", 32, 10, 42, 0.012),
    ("提拉米苏", "甜品", 35, 12, 38, 0.012),
]

SOP_DOCS = [
    ("雨天外卖提升 SOP", "sop", "rainy_day_delivery_sop.md", "雨天,外卖,配送,满减", "雨天优先检查外卖包装、骑手运力、满减活动和出餐节奏，避免外卖订单因天气下滑。"),
    ("高毛利 SKU 经营策略", "sop", "high_margin_sku_strategy.md", "SKU,毛利,爆品,陈列", "高毛利 SKU 应通过入口陈列、套餐搭配、员工推荐和限时权益提升销量。"),
    ("节假日营销作战手册", "playbook", "holiday_marketing_playbook.md", "节假日,客流,毛利,套餐", "节假日客流暴涨时要控制折扣深度，使用高毛利套餐和分时段供给提升利润。"),
    ("退单率治理 SOP", "sop", "refund_rate_reduction_sop.md", "退单,品控,配送,售后", "退单率升高时优先排查出品稳定性、包装、配送时效和客服补偿策略。"),
]


def _external_context(store_name: str, day: datetime.date) -> dict:
    is_weekend = day.weekday() >= 5
    context = {
        "weather": random.choice(["晴", "多云", "小雨", "阴"]),
        "temperature": random.randint(12, 34),
        "is_holiday": False,
        "holiday_name": "",
        "nearby_event": "",
        "traffic_level": random.choice(["low", "medium", "high"]),
        "factor_type": "weather",
        "impact_level": "low",
        "description": "常规天气波动",
    }

    if is_weekend:
        context.update({"is_holiday": True, "holiday_name": "周末", "factor_type": "holiday", "impact_level": "medium", "description": "周末客流增加"})
    if store_name == "上海静安店" and day >= datetime.date.today() - datetime.timedelta(days=7):
        context.update({"weather": "大雨", "factor_type": "weather", "impact_level": "high", "description": "大雨影响堂食与配送履约"})
    if store_name == "杭州西湖店" and day >= datetime.date.today() - datetime.timedelta(days=5):
        context.update({"is_holiday": True, "holiday_name": "景区客流高峰", "nearby_event": "西湖音乐市集", "factor_type": "event", "impact_level": "high", "description": "景区活动带来客流暴涨"})
    if store_name == "深圳南山店" and day >= datetime.date.today() - datetime.timedelta(days=6):
        context.update({"nearby_event": "科技园发布会密集", "factor_type": "event", "impact_level": "medium", "description": "企业团购与峰值配送压力增加"})
    return context


def init_mock_data(reset: bool = False):
    """Seed demo data. Set reset=True to clear and regenerate all demo tables."""

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if reset:
        for model in [AgentMemory, CampaignResult, MarketingCampaign, KnowledgeDocument, ExternalFactor, SkuPerformance, BusinessMetricsDaily, Store]:
            db.query(model).delete()
        db.commit()

    if db.query(Store).count() > 0:
        print("[Mock] Data already exists, skipping. Use reset=True to regenerate.")
        db.close()
        return

    print("[Mock] Generating AuraSaaS multi-store demo data...")
    today = datetime.date.today()
    random.seed(20260531)

    store_objs = []
    for idx, item in enumerate(STORES):
        store = Store(
            **item,
            opened_at=today - datetime.timedelta(days=365 + idx * 80),
            status="open",
            rating=round(random.uniform(4.5, 4.9), 1),
        )
        db.add(store)
        store_objs.append(store)
    db.flush()

    for store in store_objs:
        for offset in range(89, -1, -1):
            day = today - datetime.timedelta(days=offset)
            ctx = _external_context(store.name, day)
            db.add(ExternalFactor(
                store_id=store.id,
                date=day,
                weather=ctx["weather"],
                temperature=ctx["temperature"],
                is_holiday=ctx["is_holiday"],
                holiday_name=ctx["holiday_name"],
                nearby_event=ctx["nearby_event"],
                traffic_level=ctx["traffic_level"],
                note=ctx["description"],
                factor_type=ctx["factor_type"],
                description=ctx["description"],
                impact_level=ctx["impact_level"],
            ))

            store_factor = {
                "北京国贸店": 1.18,
                "上海静安店": 1.08,
                "深圳南山店": 1.12,
                "杭州西湖店": 1.05,
            }[store.name]
            revenue = random.uniform(18000, 32000) * store_factor
            orders = int(random.uniform(320, 520) * store_factor)
            delivery_ratio = random.uniform(0.30, 0.52)
            gross_margin = random.uniform(0.58, 0.68)
            refund_rate = random.uniform(0.006, 0.018)

            if day.weekday() >= 5:
                revenue *= 1.15
                orders = int(orders * 1.12)
            if store.name == "上海静安店" and offset <= 7:
                revenue *= 0.76
                orders = int(orders * 0.78)
                delivery_ratio *= 0.72  # 雨天外卖不升反降
            if store.name == "深圳南山店" and offset <= 6:
                refund_rate = random.uniform(0.045, 0.075)
                revenue *= 0.94
            if store.name == "杭州西湖店" and offset <= 5:
                revenue *= 1.38
                orders = int(orders * 1.45)
                gross_margin -= 0.11
            if store.name == "北京国贸店" and offset <= 8:
                gross_margin -= 0.04

            avg_ticket = revenue / max(orders, 1)
            commission = revenue * delivery_ratio * 0.15
            net_profit = revenue * gross_margin - commission
            new_customers = int(orders * random.uniform(0.22, 0.36))

            db.add(BusinessMetricsDaily(
                store_id=store.id,
                date=day,
                revenue=round(revenue, 2),
                total_revenue=round(revenue, 2),
                order_count=orders,
                avg_ticket=round(avg_ticket, 2),
                avg_order_value=round(avg_ticket, 2),
                gross_margin=round(gross_margin, 4),
                refund_rate=round(refund_rate, 4),
                delivery_ratio=round(delivery_ratio, 4),
                dine_in_ratio=round(1 - delivery_ratio, 4),
                new_customers=new_customers,
                returning_customers=max(0, orders - new_customers),
                platform_commission=round(commission, 2),
                net_profit=round(net_profit, 2),
            ))

            for sku_name, category, price, cost, base_sales, base_refund in SKU_CATALOG:
                sales = max(1, int(base_sales * random.uniform(0.65, 1.35) * store_factor))
                stockout = 0
                refund = base_refund * random.uniform(0.7, 1.8)

                if store.name == "北京国贸店" and sku_name in {"生椰拿铁", "桂花冷萃"} and offset <= 8:
                    sales = int(sales * 0.48)  # 高毛利 SKU 销量突然下降
                    stockout = random.randint(2, 8)
                if store.name == "深圳南山店" and offset <= 6 and category in {"轻食", "甜品"}:
                    refund *= 4.2
                if store.name == "杭州西湖店" and offset <= 5:
                    sales = int(sales * 1.35)
                    if category in {"轻食", "甜品"}:
                        cost *= 1.18

                sku_revenue = round(sales * price, 2)
                total_cost = round(sales * cost, 2)
                margin = round((sku_revenue - total_cost) / max(sku_revenue, 1), 4)
                db.add(SkuPerformance(
                    store_id=store.id,
                    date=day,
                    sku_name=sku_name,
                    category=category,
                    sales_count=sales,
                    sales_volume=sales,
                    revenue=sku_revenue,
                    cost=total_cost,
                    gross_margin=margin,
                    refund_rate=round(refund, 4),
                    stockout_count=stockout,
                    cost_warning=margin < 0.45 or stockout > 0,
                ))

    campaigns = [
        MarketingCampaign(store_id=1, campaign_name="雨天暖心外卖包", channel="外卖平台", status="draft", target_audience="3公里内老客", budget=1800, conversion_rate=0, spend=0, revenue_generated=0),
        MarketingCampaign(store_id=2, campaign_name="静安白领早餐召回", channel="短信", status="active", target_audience="近30天未复购会员", budget=1200, conversion_rate=0.036, spend=860, revenue_generated=14600),
        MarketingCampaign(store_id=4, campaign_name="西湖节假日高毛利套餐", channel="小程序 Push", status="completed", target_audience="景区游客", budget=2400, conversion_rate=0.052, spend=2200, revenue_generated=38600),
    ]
    db.add_all(campaigns)
    db.flush()
    db.add_all([
        CampaignResult(campaign_id=campaigns[1].id, store_id=2, revenue_lift=14600, order_lift=168, roi=7.1, summary="短信召回带来早餐时段回流，但雨天配送体验仍需优化。"),
        CampaignResult(campaign_id=campaigns[2].id, store_id=4, revenue_lift=38600, order_lift=420, roi=16.5, summary="节假日套餐提升客流转化，但毛利因临时补货成本下降。"),
    ])

    for title, dtype, source, tags, content in SOP_DOCS:
        db.add(KnowledgeDocument(title=title, doc_type=dtype, source=source, category=dtype, content=content, tags=tags))

    db.add_all([
        AgentMemory(store_id=1, memory_type="user_preference", content="国贸店优先选择低预算、可快速上线的白领午间营销策略。", tags="低预算,白领,国贸"),
        AgentMemory(store_id=2, memory_type="store_issue", content="上海静安店雨天外卖履约和包装体验反复影响营收。", tags="雨天,外卖,静安"),
        AgentMemory(store_id=3, memory_type="store_issue", content="深圳南山店轻食类 SKU 在峰值配送日退单率偏高。", tags="退单,轻食,南山"),
    ])

    db.commit()
    print(f"[Mock] Done: {len(store_objs)} stores, 90 days metrics, {len(SKU_CATALOG)} SKUs OK")
    db.close()


if __name__ == "__main__":
    init_mock_data(reset=True)
