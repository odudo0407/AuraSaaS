"""Agent benchmark — intent accuracy, tool success, RAG hit rate, response time.

Usage:  python -m app.scripts.benchmark_agent
Output: prints a markdown report to stdout and saves JSON to backend/logs/benchmark.json
"""

from __future__ import annotations

import json
import os
import sys
import time
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-placeholder")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SEED_DEMO_ON_STARTUP", "false")

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models.models import Store, BusinessMetricsDaily, SkuPerformance, KnowledgeDocument  # noqa: E402
from app.agents.tool_schemas import TOOL_SCHEMAS, TOOL_MAP, execute_tool, set_privilege_level, PrivilegeLevel  # noqa: E402
from app.services.rag_service import query_knowledge, ingest_documents  # noqa: E402

Base.metadata.create_all(bind=engine)


def _seed_data():
    """Minimal seed for benchmarking."""
    db = SessionLocal()
    try:
        if db.query(Store).count() == 0:
            s = Store(name="Benchmark Store", city="Beijing", status="open", manager_name="Test")
            db.add(s)
            db.flush()
            sid = s.id
            today = datetime.date.today()
            for i in range(90):
                d = today - datetime.timedelta(days=89 - i)
                db.add(BusinessMetricsDaily(
                    store_id=sid, date=d,
                    revenue=5000 + i * 30, total_revenue=5000 + i * 30,
                    order_count=120 + i, avg_ticket=42.0, gross_margin=0.62,
                    refund_rate=0.03 if i < 85 else 0.09,
                    net_profit=800 + i * 5,
                ))
            for i in range(15):
                d = today - datetime.timedelta(days=14 - i)
                db.add(SkuPerformance(
                    store_id=sid, date=d,
                    sku_name=f"SKU-{i}", category="drink" if i < 8 else "food",
                    price=28.0, cost=11.0, sales_count=60 - i * 2,
                    sales_volume=60 - i * 2, revenue=(60 - i * 2) * 28,
                    gross_margin=0.58 if i < 10 else 0.35, refund_rate=0.02,
                ))
            db.commit()
            store_id = sid
        else:
            store_id = db.query(Store).first().id
    finally:
        db.close()
    return store_id


# ── 1. Intent classification accuracy ──────────────────────────────────────

def benchmark_intent_accuracy():
    """Test all 11 keyword intent classifiers."""
    from app.agents.graph import _keyword_intent

    test_cases = [
        ("你好", "general_chat"),
        ("门店营收排行", "data_query"),
        ("为什么退款率下降了", "anomaly_diagnosis"),
        ("查SOP知识库流程规范", "knowledge_query"),
        ("帮我做营销推广方案", "marketing_plan"),
        ("新增一个商品", "data_management"),
        ("生成上周战报", "report_generation"),
        ("排班考勤怎么安排", "store_operation"),
        ("ROI投资回报率分析", "financial_analysis"),
        ("客户复购率怎么样", "customer_insight"),
        ("竞品定价对比分析", "competitor_analysis"),
    ]

    correct = 0
    results = []
    for query, expected in test_cases:
        result = _keyword_intent(query)
        actual = result["intent"]
        ok = actual == expected
        if ok:
            correct += 1
        results.append({"query": query, "expected": expected, "actual": actual, "pass": ok})

    accuracy = correct / len(test_cases) if test_cases else 0
    return {"total": len(test_cases), "correct": correct, "accuracy": accuracy, "details": results}


# ── 2. Tool call success rate ──────────────────────────────────────────────

def benchmark_tool_success_rate(store_id: int):
    """Test key tools across all 5 privilege levels."""
    set_privilege_level(PrivilegeLevel.WRITE)  # Full access for testing

    test_cases = [
        # (tool_name, args, tier, should_succeed)
        ("get_daily_summary", {"store_id": store_id}, 1, True),
        ("list_all_stores", {}, 1, True),
        ("get_store_detail", {"store_id": store_id}, 1, True),
        ("compare_periods", {"store_id": store_id, "metric": "revenue"}, 2, True),
        ("rank_stores", {}, 2, True),
        ("forecast_metric", {"store_id": store_id, "metric": "revenue"}, 2, True),
        ("search_knowledge_base", {"query": "退单处理", "top_k": 2}, 3, True),
        ("search_agent_memory", {"query": "退单"}, 3, True),
        ("generate_marketing_strategy", {"store_id": store_id, "problem": "提升毛利", "budget_limit": 2000}, 4, True),
        ("evaluate_strategy_risk", {"strategy": {"budget": 2000, "problem": "测试策略", "name": "test"}}, 4, True),
    ]

    success = 0
    results = []
    for tool_name, args, tier, _should_succeed in test_cases:
        try:
            result = execute_tool(tool_name, args)
            parsed = json.loads(result) if isinstance(result, str) else result
            ok = parsed.get("success", False)
        except Exception as e:
            ok = False
            parsed = {"error": str(e)}
        if ok:
            success += 1
        results.append({"tool": tool_name, "tier": tier, "success": ok, "result": str(parsed)[:120]})

    rate = success / len(test_cases) if test_cases else 0
    return {"total": len(test_cases), "success": success, "rate": rate, "details": results}


# ── 3. RAG retrieval hit rate ─────────────────────────────────────────────

def benchmark_rag_hit_rate():
    """Test RAG retrieval against known SOP content."""
    # Index knowledge docs first
    try:
        count = ingest_documents()
    except Exception:
        count = 0

    queries = [
        "退单处理流程",
        "差评回复规范",
        "营销活动策划",
        "门店SOP标准",
        "食品安全规范",
        "员工排班制度",
        "库存盘点流程",
        "设备维护保养",
    ]

    hits = 0
    results = []
    for q in queries:
        try:
            docs = query_knowledge(q, top_k=3)
            hit = len(docs) > 0
            if hit:
                hits += 1
            top_score = docs[0].get("score", 0) if docs else 0
            results.append({"query": q, "hits": len(docs), "top_score": round(top_score, 4)})
        except Exception:
            results.append({"query": q, "hits": 0, "top_score": 0, "error": True})

    rate = hits / len(queries) if queries else 0
    return {"total": len(queries), "hits": hits, "rate": rate, "details": results, "indexed_docs": count}


# ── 4. Test suite summary ─────────────────────────────────────────────────

def benchmark_test_summary():
    """Collect test counts (pytest must be run separately)."""
    test_dir = ROOT / "backend" / "app" / "tests"
    test_files = sorted(test_dir.glob("test_*.py"))
    total_tests = 0
    files = []
    for tf in test_files:
        content = tf.read_text(encoding="utf-8")
        count = content.count("\ndef test_")
        total_tests += count
        files.append({"file": tf.name, "test_count": count})

    return {"total_tests": total_tests, "files": files}


# ── 5. Agent response time ─────────────────────────────────────────────────

def benchmark_response_time(store_id: int):
    """Measure end-to-end tool execution latency in demo mode (no LLM)."""
    tools_to_measure = [
        ("get_daily_summary", {"store_id": store_id}),
        ("detect_anomalies", {"store_id": store_id}),
        ("rank_stores", {}),
        ("compare_periods", {"store_id": store_id, "metric": "revenue"}),
        ("forecast_metric", {"store_id": store_id, "metric": "revenue"}),
    ]

    set_privilege_level(PrivilegeLevel.WRITE)
    results = []
    latencies = []

    for tool_name, args in tools_to_measure:
        t0 = time.perf_counter()
        try:
            execute_tool(tool_name, args)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        except Exception:
            elapsed_ms = -1
        latencies.append(elapsed_ms)
        results.append({"tool": tool_name, "latency_ms": elapsed_ms})

    avg_latency = round(sum(l for l in latencies if l > 0) / len([l for l in latencies if l > 0]), 2) if latencies else 0
    return {"tools_tested": len(tools_to_measure), "avg_latency_ms": avg_latency, "details": results}


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("AuraSaaS Agent Benchmark")
    print("=" * 60)

    store_id = _seed_data()

    print("\n[1/5] Intent classification accuracy ...")
    intent = benchmark_intent_accuracy()
    print(f"  Accuracy: {intent['accuracy']:.1%} ({intent['correct']}/{intent['total']})")

    print("\n[2/5] Tool call success rate ...")
    tools = benchmark_tool_success_rate(store_id)
    print(f"  Success: {tools['rate']:.1%} ({tools['success']}/{tools['total']})")

    print("\n[3/5] RAG retrieval hit rate ...")
    rag = benchmark_rag_hit_rate()
    print(f"  Hit rate: {rag['rate']:.1%} ({rag['hits']}/{rag['total']}), indexed: {rag['indexed_docs']} docs")

    print("\n[4/5] Test suite summary ...")
    test_summary = benchmark_test_summary()
    print(f"  Tests: {test_summary['total_tests']} in {len(test_summary['files'])} files")

    print("\n[5/5] Tool execution latency ...")
    latency = benchmark_response_time(store_id)
    print(f"  Avg latency: {latency['avg_latency_ms']} ms")

    # ── Report ──
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "intent_accuracy": intent,
        "tool_success_rate": tools,
        "rag_hit_rate": rag,
        "test_summary": test_summary,
        "latency": latency,
    }

    # Save JSON
    log_dir = ROOT / "backend" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    report_path = log_dir / "benchmark.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nReport saved to {report_path}")

    # Print markdown summary
    print("\n" + "=" * 60)
    print("SUMMARY (for resume)")
    print("=" * 60)
    print(f"""
| Metric | Value |
|--------|-------|
| Keyword Intent Accuracy | {intent['accuracy']:.1%} ({intent['correct']}/{intent['total']}) |
| Tool Call Success Rate | {tools['rate']:.1%} ({tools['success']}/{tools['total']}) |
| RAG Retrieval Hit Rate | {rag['rate']:.1%} ({rag['hits']}/{rag['total']}) |
| Total Test Cases | {test_summary['total_tests']} |
| Avg Tool Latency | {latency['avg_latency_ms']} ms |
| Indexed SOP Documents | {rag['indexed_docs']} |
""")


if __name__ == "__main__":
    main()
