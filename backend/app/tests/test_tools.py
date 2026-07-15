"""Unit tests for core Agent tools — data query, anomaly detection, analysis."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

test_db = Path(tempfile.mkdtemp()) / "aurasaas_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db.as_posix()}"
os.environ["SEED_DEMO_ON_STARTUP"] = "false"
os.environ["DEEPSEEK_API_KEY"] = "sk-placeholder"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ENVIRONMENT"] = "test"

from app.database import Base, engine, SessionLocal
from app.models.models import Store, BusinessMetricsDaily, SkuPerformance, ExternalFactor
import datetime

Base.metadata.create_all(bind=engine)


def _seed():
    db = SessionLocal()
    try:
        s = Store(name="Test Store", city="Shanghai", status="open", manager_name="Alice")
        db.add(s)
        db.flush()
        sid = s.id

        for i in range(30):
            d = datetime.date.today() - datetime.timedelta(days=29 - i)
            db.add(BusinessMetricsDaily(
                store_id=sid, date=d,
                revenue=5000 + i * 50, total_revenue=5000 + i * 50,
                order_count=120 + i, avg_ticket=42.0, gross_margin=0.62,
                refund_rate=0.03 if i < 28 else 0.09,
                net_profit=800 + i * 10,
            ))
        for i in range(10):
            d = datetime.date.today() - datetime.timedelta(days=9 - i)
            db.add(SkuPerformance(
                store_id=sid, date=d,
                sku_name=f"SKU-{i}", category="drink" if i < 5 else "food",
                price=25.0, cost=10.0, sales_count=50 - i * 3,
                sales_volume=50 - i * 3, revenue=(50 - i * 3) * 25,
                gross_margin=0.55 if i < 7 else 0.38, refund_rate=0.02,
            ))
        db.add(ExternalFactor(
            store_id=sid, date=datetime.date.today(),
            weather="rain", temperature=18.0, is_holiday=False,
            factor_type="weather", description="暴雨天气",
            impact_level="high",
        ))
        db.commit()
        return sid
    finally:
        db.close()


STORE_ID = _seed()


# ── Level 1: 只读 tools ───────────────────────────────────────────────────

def test_get_store_detail():
    from app.agents.tools import get_store_detail
    r = get_store_detail(STORE_ID)
    assert r["success"]
    assert r["data"]["name"] == "Test Store"
    assert r["data"]["city"] == "Shanghai"


def test_list_all_stores():
    from app.agents.tools import list_all_stores
    r = list_all_stores()
    assert r["success"]
    assert len(r["data"]) >= 1
    assert any(s["name"] == "Test Store" for s in r["data"])


def test_get_daily_summary():
    from app.agents.tools import get_daily_summary
    r = get_daily_summary(STORE_ID)
    assert r["success"]
    assert r["data"]["revenue"] > 0
    assert r["data"]["orders"] > 0


def test_search_products():
    from app.agents.tools import search_products
    r = search_products("SKU-0")
    assert r["success"]
    assert len(r["data"]) >= 1
    assert "SKU-0" in str(r["data"])


# ── Level 2: 分析 tools ───────────────────────────────────────────────────

def test_detect_business_anomalies():
    from app.agents.tools import detect_business_anomalies
    r = detect_business_anomalies(STORE_ID, days=7)
    assert r["success"]
    # With refund_rate spike at the end, should detect at least one anomaly
    assert isinstance(r["data"], list)


def test_analyze_sku_trends():
    from app.agents.tools import analyze_sku_trends
    result = analyze_sku_trends(7, STORE_ID)
    assert len(result) > 0
    assert "SKU" in result


def test_compare_periods():
    from app.agents.tools import compare_periods
    r = compare_periods(STORE_ID, metric="revenue")
    assert r["success"]
    assert "current_value" in r["data"]
    assert "previous_value" in r["data"]
    assert "change_pct" in r["data"]


def test_rank_stores():
    from app.agents.tools import rank_stores
    r = rank_stores("revenue", top_n=3)
    assert r["success"]
    assert len(r["data"]) >= 1
    assert r["data"][0]["rank"] == 1


def test_forecast_metric():
    from app.agents.tools import forecast_metric
    r = forecast_metric("revenue", STORE_ID, forecast_days=3)
    assert r["success"]
    assert len(r["data"]["forecast"]) == 3


def test_calculate_roi():
    from app.agents.tools import calculate_roi
    r = calculate_roi(budget=1000)
    assert r["success"]
    assert "scenarios" in r["data"]


def test_check_external_context():
    from app.agents.tools import check_external_context
    result = check_external_context(STORE_ID)
    assert "暴雨" in result or "rain" in result.lower() or "天气" in result


# ── Level 3: 检索 tools ───────────────────────────────────────────────────

def test_retrieve_sop_knowledge():
    from app.agents.tools import retrieve_sop_knowledge
    result = retrieve_sop_knowledge("退单率", top_k=3)
    assert len(result) > 0
    assert "知识库" in result or "SOP" in result or "退单" in result


def test_search_agent_memory():
    from app.agents.tools import search_agent_memory
    r = search_agent_memory("test", STORE_ID)
    assert r["success"]
    assert isinstance(r["data"], list)


# ── Level 4: 生成 tools ───────────────────────────────────────────────────

def test_generate_marketing_strategy_fallback():
    from app.agents.tools import generate_marketing_strategy
    r = generate_marketing_strategy(STORE_ID, "退单率过高", budget_limit=1500)
    assert r["success"]
    assert "actions" in str(r["data"])
    # In demo mode (no API key), should use template fallback
    assert r["data"].get("generation_mode") == "template_fallback"


def test_evaluate_strategy_risk():
    from app.agents.tools import evaluate_strategy_risk
    r = evaluate_strategy_risk({"budget": 3000, "problem": "test"})
    assert r["success"]
    assert r["data"]["risk_level"] in ("low", "medium", "high")
    assert "requires_approval" in r["data"]


def test_generate_campaign_copy_fallback():
    from app.agents.tools import generate_campaign_copy
    r = generate_campaign_copy({"name": "test", "target": "test"})
    assert r["success"]
    assert "sms" in r["data"]
    assert r["data"].get("generation_mode") == "template_fallback"


# ── Level 5: 写入 tools ───────────────────────────────────────────────────

def test_save_and_search_memory():
    from app.agents.tools import save_agent_memory, search_agent_memory
    r = save_agent_memory(STORE_ID, "diagnosis", "测试记忆内容")
    assert r["success"]
    r2 = search_agent_memory("测试", STORE_ID)
    assert r2["success"]
    assert any("测试记忆" in m.get("content", "") for m in r2["data"])


def test_create_anomaly_tasks():
    from app.agents.tools import create_anomaly_tasks
    r = create_anomaly_tasks(STORE_ID)
    assert r["success"]
    assert "tasks_created" in r["data"]


def test_add_product():
    from app.agents.tools import add_product
    r = add_product({
        "store_id": STORE_ID,
        "sku_name": "测试新品",
        "category": "food",
        "price": 30,
        "cost": 12,
    })
    assert r["success"]
    assert r["data"]["sku_name"] == "测试新品"
