"""Unit tests for 5-level privilege gating system."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

test_db = Path(tempfile.mkdtemp()) / "aurasaas_priv_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db.as_posix()}"
os.environ["SEED_DEMO_ON_STARTUP"] = "false"
os.environ["DEEPSEEK_API_KEY"] = "sk-placeholder"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ENVIRONMENT"] = "test"

from app.database import Base, engine, SessionLocal
from app.models.models import Store, BusinessMetricsDaily
import datetime

Base.metadata.create_all(bind=engine)

# Seed minimal data
db = SessionLocal()
s = Store(name="PrivTest", city="Beijing", status="open")
db.add(s)
db.flush()
STORE_ID = s.id
db.add(BusinessMetricsDaily(
    store_id=STORE_ID, date=datetime.date.today(),
    revenue=5000, total_revenue=5000, order_count=100, avg_ticket=50,
    gross_margin=0.6, net_profit=800,
))
db.commit()
db.close()

from app.agents.tool_schemas import (
    TOOL_SCHEMAS, TOOL_MAP, execute_tool,
    PrivilegeLevel, PrivilegeEscalationError,
    set_privilege_level, get_privilege_level,
    get_tool_privilege, get_tools_for_privilege,
    PRIVILEGE_LABELS,
)


# ── Privilege level tagging ────────────────────────────────────────────────

def test_all_tools_have_privilege_level():
    for schema in TOOL_SCHEMAS:
        name = schema["function"]["name"]
        assert "privilege_level" in schema, f"{name} missing privilege_level"
        assert 1 <= schema["privilege_level"] <= 5, f"{name} bad level"


def test_all_tools_in_map():
    tool_names = {s["function"]["name"] for s in TOOL_SCHEMAS}
    for name in TOOL_MAP:
        assert name in tool_names, f"{name} in TOOL_MAP but not in TOOL_SCHEMAS"


def test_tool_privilege_lookup():
    assert get_tool_privilege("get_daily_summary") == PrivilegeLevel.READ
    assert get_tool_privilege("detect_anomalies") == PrivilegeLevel.ANALYZE
    assert get_tool_privilege("search_knowledge_base") == PrivilegeLevel.RETRIEVE
    assert get_tool_privilege("generate_marketing_strategy") == PrivilegeLevel.GENERATE
    assert get_tool_privilege("create_anomaly_tasks") == PrivilegeLevel.WRITE


# ── Privilege filtering ────────────────────────────────────────────────────

def test_filter_tools_level_1():
    tools = get_tools_for_privilege(PrivilegeLevel.READ)
    names = {t["function"]["name"] for t in tools}
    assert "get_daily_summary" in names
    assert "detect_anomalies" not in names
    assert "generate_marketing_strategy" not in names


def test_filter_tools_level_3():
    tools = get_tools_for_privilege(PrivilegeLevel.RETRIEVE)
    names = {t["function"]["name"] for t in tools}
    assert "get_daily_summary" in names
    assert "detect_anomalies" in names
    assert "search_knowledge_base" in names
    assert "generate_marketing_strategy" not in names
    assert "add_product" not in names


def test_filter_tools_level_5():
    tools = get_tools_for_privilege(PrivilegeLevel.WRITE)
    assert len(tools) == len(TOOL_SCHEMAS)  # all tools visible at max level


# ── Execution gating ───────────────────────────────────────────────────────

def test_level_1_tool_runs_at_level_3():
    set_privilege_level(PrivilegeLevel.RETRIEVE)
    result = execute_tool("get_daily_summary", {"store_id": STORE_ID})
    assert '"success": true' in result.lower()


def test_level_4_tool_blocked_at_level_3():
    set_privilege_level(PrivilegeLevel.RETRIEVE)
    try:
        execute_tool("generate_marketing_strategy", {"store_id": STORE_ID, "problem": "test"})
        assert False, "Should have raised PrivilegeEscalationError"
    except PrivilegeEscalationError as e:
        assert "权限" in str(e)


def test_level_4_tool_runs_at_level_5():
    set_privilege_level(PrivilegeLevel.WRITE)
    try:
        result = execute_tool("generate_marketing_strategy", {"store_id": STORE_ID, "problem": "test"})
        assert '"success": true' in result.lower()
    except PrivilegeEscalationError:
        assert False, "Level 5 should allow level 4 tools"


def test_level_5_tool_blocked_at_level_3():
    set_privilege_level(PrivilegeLevel.RETRIEVE)
    try:
        execute_tool("add_product", {"sku_name": "test", "category": "food", "price": 10, "cost": 5})
        assert False, "Should have raised PrivilegeEscalationError"
    except PrivilegeEscalationError as e:
        assert "权限" in str(e)


def test_level_5_tool_runs_at_level_5():
    set_privilege_level(PrivilegeLevel.WRITE)
    try:
        result = execute_tool("add_product", {
            "store_id": STORE_ID, "sku_name": "PrivTestSKU",
            "category": "drink", "price": 18, "cost": 6,
        })
        assert '"success": true' in result.lower()
    except PrivilegeEscalationError:
        assert False, "Level 5 should allow write tools"


# ── Context management ─────────────────────────────────────────────────────

def test_default_privilege():
    set_privilege_level(PrivilegeLevel.RETRIEVE)
    assert get_privilege_level() == PrivilegeLevel.RETRIEVE


def test_privilege_labels():
    assert PRIVILEGE_LABELS[1] == "只读"
    assert PRIVILEGE_LABELS[5] == "写入"


# ── Negative: unknown tool ─────────────────────────────────────────────────

def test_unknown_tool():
    set_privilege_level(PrivilegeLevel.WRITE)
    result = execute_tool("nonexistent_tool", {})
    assert '"success": false' in result.lower()
    assert "未知工具" in result
