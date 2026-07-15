"""BI Agent Tools — data query, external context, RAG, memory and marketing helpers."""

from __future__ import annotations

import datetime
import json
import uuid
from sqlalchemy import func, desc
from app.database import SessionLocal
from app.models.models import (
    AgentMemory,
    BusinessMetricsDaily,
    ExternalFactor,
    KnowledgeDocument,
    MarketingCampaign,
    SkuPerformance,
    Staff,
    Store,
    Task,
)
from app.services.rag_service import query_knowledge


def tool_result(success: bool = True, data=None, error: str | None = None, trace_id: str | None = None) -> dict:
    """Return a unified tool response envelope."""

    return {
        "success": success,
        "data": data,
        "error": error,
        "trace_id": trace_id or str(uuid.uuid4()),
    }


def _parse_date(value: str | datetime.date | None, default: datetime.date) -> datetime.date:
    if value is None:
        return default
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(value)


def get_store_overview(store_id: int | None = None, start_date: str | None = None, end_date: str | None = None) -> dict:
    """Structured overview data for one store or all stores."""

    db = SessionLocal()
    try:
        today = datetime.date.today()
        end = _parse_date(end_date, today)
        start = _parse_date(start_date, end - datetime.timedelta(days=6))
        q = db.query(
            func.sum(BusinessMetricsDaily.revenue).label("revenue"),
            func.sum(BusinessMetricsDaily.order_count).label("orders"),
            func.avg(BusinessMetricsDaily.avg_ticket).label("avg_ticket"),
            func.avg(BusinessMetricsDaily.gross_margin).label("gross_margin"),
            func.avg(BusinessMetricsDaily.refund_rate).label("refund_rate"),
            func.avg(BusinessMetricsDaily.delivery_ratio).label("delivery_ratio"),
            func.sum(BusinessMetricsDaily.net_profit).label("net_profit"),
        ).filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= end)
        if store_id:
            q = q.filter(BusinessMetricsDaily.store_id == store_id)
        row = q.first()
        data = {
            "store_id": store_id,
            "start_date": str(start),
            "end_date": str(end),
            "revenue": round(row.revenue or 0, 2),
            "order_count": int(row.orders or 0),
            "avg_ticket": round(row.avg_ticket or 0, 2),
            "gross_margin": round((row.gross_margin or 0) * 100, 2),
            "refund_rate": round((row.refund_rate or 0) * 100, 2),
            "delivery_ratio": round((row.delivery_ratio or 0) * 100, 2),
            "net_profit": round(row.net_profit or 0, 2),
        }
        return tool_result(data=data)
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def compare_stores(metric: str = "revenue", start_date: str | None = None, end_date: str | None = None) -> dict:
    """Rank stores by a metric in a date range."""

    db = SessionLocal()
    try:
        today = datetime.date.today()
        end = _parse_date(end_date, today)
        start = _parse_date(start_date, end - datetime.timedelta(days=6))
        metric_map = {
            "revenue": BusinessMetricsDaily.revenue,
            "order_count": BusinessMetricsDaily.order_count,
            "gross_margin": BusinessMetricsDaily.gross_margin,
            "refund_rate": BusinessMetricsDaily.refund_rate,
        }
        col = metric_map.get(metric, BusinessMetricsDaily.revenue)
        aggregate = func.avg(col) if metric in {"gross_margin", "refund_rate"} else func.sum(col)
        rows = db.query(Store.id, Store.name, Store.city, aggregate.label("value")).join(
            BusinessMetricsDaily, BusinessMetricsDaily.store_id == Store.id
        ).filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= end).group_by(Store.id).order_by(desc("value")).all()
        return tool_result(data=[{"store_id": r.id, "store_name": r.name, "city": r.city, "metric": metric, "value": round(r.value or 0, 4)} for r in rows])
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def detect_business_anomalies(store_id: int | None = None, days: int = 7) -> dict:
    """Detect revenue drops, margin deterioration and refund spikes."""

    db = SessionLocal()
    try:
        today = datetime.date.today()
        current_start = today - datetime.timedelta(days=days - 1)
        prev_end = current_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=days - 1)
        stores = db.query(Store).filter(Store.id == store_id).all() if store_id else db.query(Store).order_by(Store.id).all()
        anomalies = []
        for store in stores:
            def agg(start, end):
                return db.query(
                    func.sum(BusinessMetricsDaily.revenue).label("revenue"),
                    func.avg(BusinessMetricsDaily.gross_margin).label("margin"),
                    func.avg(BusinessMetricsDaily.refund_rate).label("refund"),
                    func.avg(BusinessMetricsDaily.delivery_ratio).label("delivery"),
                ).filter(
                    BusinessMetricsDaily.store_id == store.id,
                    BusinessMetricsDaily.date >= start,
                    BusinessMetricsDaily.date <= end,
                ).first()

            cur = agg(current_start, today)
            prev = agg(prev_start, prev_end)
            if prev.revenue and cur.revenue and cur.revenue < prev.revenue * 0.88:
                anomalies.append({"store_id": store.id, "store_name": store.name, "type": "revenue_drop", "severity": "high", "evidence": f"近{days}天营收较前周期下降{(1-cur.revenue/prev.revenue)*100:.1f}%"})
            if prev.margin and cur.margin and cur.margin < prev.margin - 0.06:
                anomalies.append({"store_id": store.id, "store_name": store.name, "type": "margin_drop", "severity": "medium", "evidence": f"毛利率下降{(prev.margin-cur.margin)*100:.1f}个百分点"})
            if prev.refund and cur.refund and cur.refund > max(prev.refund * 1.8, 0.03):
                anomalies.append({"store_id": store.id, "store_name": store.name, "type": "refund_spike", "severity": "high", "evidence": f"退单率升至{cur.refund*100:.2f}%"})
            if prev.delivery and cur.delivery and cur.delivery < prev.delivery - 0.08:
                anomalies.append({"store_id": store.id, "store_name": store.name, "type": "delivery_ratio_drop", "severity": "medium", "evidence": f"外卖占比下降{(prev.delivery-cur.delivery)*100:.1f}个百分点"})
        return tool_result(data=anomalies)
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def analyze_sku_trends(date_range: int = 7, store_id: int | None = None) -> str:
    """Query recent SKU performance, identify declining or anomalous items."""
    db = SessionLocal()
    today = datetime.date.today()
    start = today - datetime.timedelta(days=date_range - 1)

    q = db.query(
        SkuPerformance.sku_name, SkuPerformance.category,
        func.sum(SkuPerformance.sales_count).label("total_sales"),
        func.sum(SkuPerformance.revenue).label("total_revenue"),
        func.avg(SkuPerformance.gross_margin).label("avg_margin"),
        func.avg(SkuPerformance.refund_rate).label("avg_refund"),
        func.sum(SkuPerformance.stockout_count).label("stockouts"),
    ).filter(SkuPerformance.date >= start)
    if store_id:
        q = q.filter(SkuPerformance.store_id == store_id)
    rows = q.group_by(SkuPerformance.sku_name, SkuPerformance.category).order_by(desc("total_sales")).all()

    prev_start = start - datetime.timedelta(days=date_range)
    pq = db.query(SkuPerformance.sku_name, func.sum(SkuPerformance.sales_count).label("total_sales")).filter(
        SkuPerformance.date >= prev_start, SkuPerformance.date < start
    )
    if store_id:
        pq = pq.filter(SkuPerformance.store_id == store_id)
    prev_map = {r.sku_name: r.total_sales for r in pq.group_by(SkuPerformance.sku_name).all()}

    result = [f"=== 近{date_range}天 SKU 销售分析 ===\n"]
    anomalies = []
    for r in rows:
        prev = prev_map.get(r.sku_name, 0)
        change = ""
        if prev > 0:
            pct = (r.total_sales - prev) / prev * 100
            if pct < -20:
                change = f" ⚠️ 销量下跌{abs(pct):.0f}%"
                anomalies.append(f"  - {r.sku_name}({r.category}): {prev}→{r.total_sales}，跌幅{abs(pct):.0f}%")
            elif pct > 20:
                change = f" 📈 上涨{pct:.0f}%"
        margin_flag = " 🔴低毛利" if (r.avg_margin or 0) < 0.45 else ""
        refund_flag = " ⚠️高退单" if (r.avg_refund or 0) > 0.03 else ""
        stockout_flag = f" ⚠️缺货{int(r.stockouts or 0)}次" if (r.stockouts or 0) else ""
        result.append(f"  {r.sku_name}({r.category}): 销量{int(r.total_sales or 0)}, 营收¥{(r.total_revenue or 0):.0f}, 毛利率{(r.avg_margin or 0)*100:.1f}%{change}{margin_flag}{refund_flag}{stockout_flag}")

    if anomalies:
        result.append("\n⚠️ 异常预警:")
        result.extend(anomalies)

    db.close()
    return "\n".join(result)


def fetch_cost_anomalies(store_id: int | None = None) -> str:
    """Query cost anomalies — commission spikes, margin drops."""
    db = SessionLocal()
    today = datetime.date.today()
    last7 = today - datetime.timedelta(days=6)
    prev7 = last7 - datetime.timedelta(days=7)

    def agg(start, end):
        q = db.query(func.sum(BusinessMetricsDaily.platform_commission).label("comm"),
                     func.sum(BusinessMetricsDaily.revenue).label("rev"),
                     func.avg(BusinessMetricsDaily.gross_margin).label("margin")).filter(
            BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= end)
        if store_id:
            q = q.filter(BusinessMetricsDaily.store_id == store_id)
        return q.first()

    l7 = agg(last7, today)
    p7 = agg(prev7, last7 - datetime.timedelta(days=1))

    result = ["=== 成本异常检测 ===\n"]
    if l7.comm and p7.comm:
        comm_chg = (l7.comm - p7.comm) / p7.comm * 100
        rate = l7.comm / max(l7.rev or 1, 1) * 100
        result.append(f"  近7天抽佣: ¥{l7.comm:.0f} (率{rate:.1f}%) 环比{comm_chg:+.1f}%")
        if comm_chg > 20:
            result.append("  ⚠️ 抽佣异常上涨! 建议检查外卖平台费率和配送结构")
    if l7.margin and p7.margin and l7.margin < p7.margin - 0.05:
        result.append(f"  ⚠️ 毛利率下降{(p7.margin-l7.margin)*100:.1f}个百分点")

    db.close()
    return "\n".join(result)


def check_external_context(store_id: int | None = None, date: str | None = None) -> str:
    """Query external factors — weather, holidays, events."""
    db = SessionLocal()
    target_date = _parse_date(date, datetime.date.today())
    q = db.query(ExternalFactor).filter(ExternalFactor.date == target_date)
    if store_id:
        q = q.filter(ExternalFactor.store_id == store_id)
    factors = q.all()

    if not factors:
        recent = db.query(ExternalFactor).order_by(ExternalFactor.date.desc()).limit(5).all()
        result = ["=== 近期外部环境因素 ===\n"] if recent else ["=== 外部环境 ===\n  无特殊外部因素"]
        for f in recent:
            result.append(f"  [{f.date}] {f.factor_type}: {f.description} (影响:{f.impact_level})")
    else:
        result = [f"=== {target_date} 外部环境 ===\n"]
        for f in factors:
            icon = {"weather": "🌧", "holiday": "🎉", "event": "📍"}.get(f.factor_type, "📌")
            store_label = f"门店{f.store_id}" if f.store_id else "全局"
            result.append(f"  {icon} {store_label}: {f.description}; 天气:{f.weather or '-'}; 活动:{f.nearby_event or '-'}; 影响:{f.impact_level}")

    db.close()
    return "\n".join(result)


def get_weather_impact_summary(store_id: int, date: str | None = None) -> dict:
    return tool_result(data={"summary": check_external_context(store_id=store_id, date=date)})


def get_holiday_context(store_id: int, date: str | None = None) -> dict:
    return tool_result(data={"summary": check_external_context(store_id=store_id, date=date)})


def retrieve_sop_knowledge(query: str, top_k: int = 4) -> str:
    """Search knowledge base for relevant SOP/cases."""
    docs = query_knowledge(query, top_k=top_k)
    if docs:
        output = ["=== 知识库检索结果 ===\n"]
        for doc in docs:
            output.append(f"\n📄 {doc['title']} (来源:{doc['source']}, 分数:{doc['score']:.2f})")
            output.append(doc["snippet"])
        return "\n".join(output)

    # DB fallback for legacy seeded records.
    db = SessionLocal()
    keywords = query.lower().split()
    db_docs = db.query(KnowledgeDocument).all()
    results = []
    for doc in db_docs:
        score = sum(1 for kw in keywords if kw in doc.content.lower() or kw in doc.title.lower() or kw in (doc.tags or "").lower())
        if score > 0:
            results.append((score, doc))
    results.sort(key=lambda x: -x[0])
    db.close()
    if not results:
        return "=== 知识库检索 ===\n  未找到相关知识文档"
    output = ["=== 知识库检索结果 ===\n"]
    for score, doc in results[:top_k]:
        output.append(f"\n📄 {doc.title} (类型:{doc.doc_type}, 相关度:{score})")
        output.append(doc.content[:500])
    return "\n".join(output)


def retrieve_marketing_cases(query: str, top_k: int = 4) -> dict:
    return tool_result(data=query_knowledge(f"营销 案例 {query}", top_k=top_k))


def retrieve_historical_reviews(query: str, top_k: int = 4) -> dict:
    return tool_result(data=query_knowledge(f"复盘 评价 差评 {query}", top_k=top_k))


def generate_marketing_strategy(store_id: int, problem: str, budget_limit: float = 2000, target: str = "提升订单") -> dict:
    """Generate a marketing strategy via LLM, with a template fallback."""
    budget = min(float(budget_limit), 3000)

    store_name = f"门店{store_id}"
    try:
        from app.database import SessionLocal as _SL
        db = _SL()
        try:
            s = db.query(Store).filter(Store.id == store_id).first()
            if s:
                store_name = s.name
        finally:
            db.close()
    except Exception:
        pass

    fallback = {
        "store_id": store_id,
        "name": f"{target}低预算行动方案",
        "problem": problem,
        "budget": budget,
        "target": target,
        "actions": [
            "向近30天未复购会员发放定向券",
            "上线高毛利套餐并优先展示",
            "店员执行一句话推荐话术",
            "每2小时复盘订单、退单和毛利表现",
        ],
        "expected_result": "预计提升订单 8%-15%，同时控制补贴成本。",
        "generation_mode": "template_fallback",
    }

    try:
        from app.services.deepseek_client import chat as _llm, has_valid_api_key as _has_key
        if not _has_key():
            return tool_result(data=fallback)

        prompt = (
            f"你是一个咖啡轻食连锁品牌的营销策略专家。请基于以下信息生成一个JSON格式的低预算营销方案：\n\n"
            f"门店：{store_name}\n"
            f"待解决问题：{problem}\n"
            f"预算上限：¥{budget}\n"
            f"目标：{target}\n\n"
            f"输出严格JSON（不要markdown代码块标记）：\n"
            f'{{"name": "方案名称", "actions": ["具体动作1", "具体动作2", "具体动作3"], '
            f'"expected_result": "预期效果描述"}}'
        )
        raw = _llm(
            "You are a marketing strategist. Output strictly valid JSON only, no markdown fences.",
            prompt,
            "",
            temperature=0.5,
            max_tokens=500,
        )
        if raw:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            parsed = json.loads(raw.strip())
            return tool_result(data={
                "store_id": store_id,
                "name": parsed.get("name", fallback["name"]),
                "problem": problem,
                "budget": budget,
                "target": target,
                "actions": parsed.get("actions", fallback["actions"]),
                "expected_result": parsed.get("expected_result", fallback["expected_result"]),
                "generation_mode": "llm",
            })
    except Exception:
        pass

    return tool_result(data=fallback)


def evaluate_strategy_risk(strategy: dict) -> dict:
    """Evaluate strategy risk via LLM analysis, with a heuristic fallback."""
    budget = float(strategy.get("budget", 0) or 0)
    problem = strategy.get("problem", "")
    target = strategy.get("target", "")

    fallback_risk = "low" if budget <= 2000 else "medium" if budget <= 5000 else "high"
    fallback = {
        "risk_level": fallback_risk,
        "requires_approval": fallback_risk != "low",
        "reasons": ["预算较高需审批"] if fallback_risk != "low" else ["预算可控"],
        "generation_mode": "heuristic_fallback",
    }

    try:
        from app.services.deepseek_client import chat as _llm, has_valid_api_key as _has_key
        if not _has_key():
            return tool_result(data=fallback)

        prompt = (
            f"评估以下营销策略的风险等级，输出严格JSON：\n\n"
            f"预算：¥{budget}\n"
            f"问题：{problem}\n"
            f"目标：{target}\n\n"
            f'输出格式：{{"risk_level": "low|medium|high", '
            f'"reasons": ["原因1", "原因2"]}}\n'
            f"评判标准：预算≤2000且方案具体→low；预算2000-5000或涉及价格调整→medium；"
            f"预算>5000或涉及高风险操作→high。"
        )
        raw = _llm(
            "You are a risk analyst. Output strictly valid JSON only, no markdown fences.",
            prompt,
            "",
            temperature=0.2,
            max_tokens=300,
        )
        if raw:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            parsed = json.loads(raw.strip())
            risk_level = parsed.get("risk_level", fallback_risk)
            return tool_result(data={
                "risk_level": risk_level,
                "requires_approval": risk_level != "low",
                "reasons": parsed.get("reasons", fallback["reasons"]),
                "generation_mode": "llm",
            })
    except Exception:
        pass

    return tool_result(data=fallback)


def generate_campaign_copy(strategy: dict, tone: str = "friendly") -> dict:
    """Generate campaign copy via LLM, with a template fallback."""
    name = strategy.get("name", "门店福利")
    target = strategy.get("target", "提升订单")
    fallback = {
        "sms": f"【AuraSaaS】{name}上线啦！今天到店/外卖下单享专属福利，数量有限，先到先得。",
        "mini_program_push": f"{name}：为你准备了一份限时经营福利，点击领取并立即下单。",
        "wechat_article": f"围绕「{target}」，门店推出限时套餐与会员专属权益，兼顾体验与品质。",
        "delivery_title": f"限时福利｜{name}",
        "staff_script": "您好，今天推荐我们的高毛利明星套餐，口味稳定、出餐快，现在还有会员专属权益。",
        "tone": tone,
        "generation_mode": "template_fallback",
    }

    try:
        from app.services.deepseek_client import chat as _llm, has_valid_api_key as _has_key
        if not _has_key():
            return tool_result(data=fallback)

        prompt = (
            f"你是一个咖啡轻食连锁品牌的营销文案专家。请基于以下信息生成多渠道营销文案，输出严格JSON：\n\n"
            f"活动名称：{name}\n"
            f"活动目标：{target}\n"
            f"文案风格：{tone}\n\n"
            f'输出格式：{{"sms": "短信文案(67字以内)", "mini_program_push": "小程序Push文案", '
            f'"wechat_article": "公众号摘要", "delivery_title": "外卖平台标题", '
            f'"staff_script": "员工推荐话术"}}'
        )
        raw = _llm(
            "You are a marketing copywriter for a coffee chain. Output strictly valid JSON only, no markdown fences.",
            prompt,
            "",
            temperature=0.7,
            max_tokens=600,
        )
        if raw:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            parsed = json.loads(raw.strip())
            return tool_result(data={
                "sms": parsed.get("sms", fallback["sms"]),
                "mini_program_push": parsed.get("mini_program_push", fallback["mini_program_push"]),
                "wechat_article": parsed.get("wechat_article", fallback["wechat_article"]),
                "delivery_title": parsed.get("delivery_title", fallback["delivery_title"]),
                "staff_script": parsed.get("staff_script", fallback["staff_script"]),
                "tone": tone,
                "generation_mode": "llm",
            })
    except Exception:
        pass

    return tool_result(data=fallback)


def simulate_marketing_webhook(campaign: dict) -> dict:
    db = SessionLocal()
    try:
        record = MarketingCampaign(
            store_id=campaign.get("store_id"),
            campaign_name=campaign.get("name", "AI 生成营销活动"),
            channel=campaign.get("channel", "demo_webhook"),
            status="active",
            target_audience=campaign.get("target", "门店用户"),
            budget=float(campaign.get("budget", 0) or 0),
            content_text=json.dumps(campaign, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        return tool_result(data={"campaign_id": record.id, "status": "demo_sent", "message": "Demo Webhook 执行成功"})
    except Exception as exc:
        db.rollback()
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def save_agent_memory(store_id: int | None, memory_type: str, content: str) -> dict:
    db = SessionLocal()
    try:
        memory = AgentMemory(store_id=store_id, memory_type=memory_type, content=content)
        db.add(memory)
        db.commit()
        return tool_result(data={"id": memory.id})
    except Exception as exc:
        db.rollback()
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def search_agent_memory(query: str, store_id: int | None = None) -> dict:
    db = SessionLocal()
    try:
        q = db.query(AgentMemory)
        if store_id:
            q = q.filter(AgentMemory.store_id == store_id)
        rows = q.order_by(AgentMemory.created_at.desc()).limit(50).all()
        tokens = query.lower().split()
        matches = [m for m in rows if any(token in m.content.lower() or token in (m.tags or "").lower() for token in tokens)] or rows[:5]
        return tool_result(data=[{"id": m.id, "store_id": m.store_id, "memory_type": m.memory_type, "content": m.content, "created_at": str(m.created_at)} for m in matches[:10]])
    finally:
        db.close()


def summarize_store_history(store_id: int) -> dict:
    memories = search_agent_memory("", store_id=store_id).get("data", [])
    summary = "；".join(item["content"] for item in memories[:5]) if memories else "暂无长期记忆。"
    return tool_result(data={"store_id": store_id, "summary": summary})


def generate_business_report(store_id: int | None = None, start_date: str | None = None, end_date: str | None = None) -> dict:
    overview = get_store_overview(store_id, start_date, end_date)
    anomalies = detect_business_anomalies(store_id)
    return tool_result(data={"overview": overview.get("data"), "anomalies": anomalies.get("data")})


def export_report_to_markdown(report: dict) -> dict:
    content = ["# AuraSaaS 经营诊断报告", "", "## 核心数据", "```json", json.dumps(report, ensure_ascii=False, indent=2), "```"]
    return tool_result(data={"markdown": "\n".join(content)})


def export_report_to_pdf(report: dict) -> dict:
    return tool_result(data={"status": "demo", "message": "PDF 导出为 MVP Demo，可后续接入 WeasyPrint/Playwright。", "report": report})


# =============================================================================
# New tools — forecast, compare, rank, anomaly-to-task
# =============================================================================

def forecast_metric(
    metric: str = "revenue",
    store_id: int | None = None,
    forecast_days: int = 7,
) -> dict:
    """Simple moving-average revenue/profit forecast for the next N days."""
    db = SessionLocal()
    try:
        today = datetime.date.today()
        start = today - datetime.timedelta(days=30)
        col = {
            "revenue": BusinessMetricsDaily.revenue,
            "net_profit": BusinessMetricsDaily.net_profit,
            "order_count": BusinessMetricsDaily.order_count,
        }.get(metric, BusinessMetricsDaily.revenue)

        q = db.query(BusinessMetricsDaily.date, col).filter(
            BusinessMetricsDaily.date >= start,
            BusinessMetricsDaily.date <= today,
        )
        if store_id:
            q = q.filter(BusinessMetricsDaily.store_id == store_id)
        rows = q.order_by(BusinessMetricsDaily.date.asc()).all()

        if not rows:
            return tool_result(False, error="No data for forecast")

        values = [r[1] or 0 for r in rows]
        avg = sum(values) / len(values)
        # Simple 7-day moving average as forecast baseline
        window = min(7, len(values))
        recent_avg = sum(values[-window:]) / window if window else avg
        trend = (recent_avg - avg) / avg if avg else 0

        forecast = []
        for i in range(1, forecast_days + 1):
            day = today + datetime.timedelta(days=i)
            predicted = recent_avg * (1 + trend * min(i, 7) / 7)
            forecast.append({
                "date": str(day),
                "predicted": round(predicted, 2),
                "confidence": round(max(0.5, 1.0 - 0.05 * i), 2),
            })

        return tool_result(data={
            "metric": metric,
            "store_id": store_id,
            "historical_avg": round(avg, 2),
            "recent_avg": round(recent_avg, 2),
            "trend_pct": round(trend * 100, 2),
            "forecast": forecast,
        })
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def compare_periods(
    store_id: int | None = None,
    metric: str = "revenue",
) -> dict:
    """Compare current period (last 7 days) with previous period."""
    db = SessionLocal()
    try:
        today = datetime.date.today()
        cur_end = today
        cur_start = today - datetime.timedelta(days=6)
        prev_end = cur_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=6)

        col = {
            "revenue": BusinessMetricsDaily.revenue,
            "net_profit": BusinessMetricsDaily.net_profit,
            "order_count": BusinessMetricsDaily.order_count,
            "gross_margin": BusinessMetricsDaily.gross_margin,
            "refund_rate": BusinessMetricsDaily.refund_rate,
            "avg_ticket": BusinessMetricsDaily.avg_ticket,
        }.get(metric, BusinessMetricsDaily.revenue)

        is_avg = metric in ("gross_margin", "refund_rate", "avg_ticket")

        def _get(period_start, period_end):
            q = db.query(
                func.avg(col) if is_avg else func.sum(col)
            ).filter(
                BusinessMetricsDaily.date >= period_start,
                BusinessMetricsDaily.date <= period_end,
            )
            if store_id:
                q = q.filter(BusinessMetricsDaily.store_id == store_id)
            return q.scalar() or 0

        cur_val = _get(cur_start, cur_end)
        prev_val = _get(prev_start, prev_end)
        change_pct = ((cur_val - prev_val) / prev_val * 100) if prev_val else 0

        return tool_result(data={
            "metric": metric,
            "store_id": store_id,
            "current_period": f"{cur_start} ~ {cur_end}",
            "previous_period": f"{prev_start} ~ {prev_end}",
            "current_value": round(cur_val, 2),
            "previous_value": round(prev_val, 2),
            "change_pct": round(change_pct, 2),
            "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat",
        })
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def rank_stores(
    metric: str = "revenue",
    top_n: int = 5,
    days: int = 7,
) -> dict:
    """Rank stores by a given metric over the last N days."""
    db = SessionLocal()
    try:
        today = datetime.date.today()
        start = today - datetime.timedelta(days=days - 1)

        col = {
            "revenue": BusinessMetricsDaily.revenue,
            "net_profit": BusinessMetricsDaily.net_profit,
            "order_count": BusinessMetricsDaily.order_count,
            "gross_margin": BusinessMetricsDaily.gross_margin,
            "refund_rate": BusinessMetricsDaily.refund_rate,
            "avg_ticket": BusinessMetricsDaily.avg_ticket,
        }.get(metric, BusinessMetricsDaily.revenue)

        is_avg = metric in ("gross_margin", "refund_rate", "avg_ticket")
        aggregate = func.avg(col) if is_avg else func.sum(col)

        rows = (
            db.query(
                Store.id, Store.name, Store.city, aggregate.label("value")
            )
            .join(BusinessMetricsDaily, BusinessMetricsDaily.store_id == Store.id)
            .filter(BusinessMetricsDaily.date >= start, BusinessMetricsDaily.date <= today)
            .group_by(Store.id)
            .order_by(desc("value") if metric != "refund_rate" else asc("value"))
            .limit(top_n)
            .all()
        )

        return tool_result(data=[{
            "rank": i + 1,
            "store_id": r.id,
            "name": r.name,
            "city": r.city,
            "metric": metric,
            "value": round(r.value or 0, 2),
        } for i, r in enumerate(rows)])
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def create_anomaly_tasks(store_id: int | None = None, days: int = 7) -> dict:
    """Detect anomalies and create Task records for them."""
    anomaly_result = detect_business_anomalies(store_id=store_id, days=days)
    anomalies = anomaly_result.get("data", [])
    if not anomalies:
        return tool_result(data={"tasks_created": 0, "message": "No anomalies detected."})

    db = SessionLocal()
    created = []
    try:
        for a in anomalies:
            task = Task(
                title=f"[{a.get('severity', 'medium').upper()}] {a.get('store_name', '门店')}: {a.get('type', '异常')}",
                description=a.get("evidence", ""),
                task_type="system",
                urgency=a.get("severity", "medium"),
                status="pending",
                icon={"revenue_drop": "📉", "margin_drop": "📊", "refund_spike": "⚠️", "delivery_ratio_drop": "🛵"}.get(a.get("type", ""), "🔔"),
                tag="自动告警",
                related_id=a.get("store_id"),
            )
            db.add(task)
            db.flush()
            created.append({"task_id": task.id, "title": task.title, "urgency": task.urgency})
        db.commit()
        return tool_result(data={"tasks_created": len(created), "tasks": created})
    except Exception as exc:
        db.rollback()
        return tool_result(False, error=str(exc))
    finally:
        db.close()

def add_product(data=None, **kwargs):
    """Add a product/SKU record.  Accepts either a single dict or keyword args."""
    if data is None:
        data = kwargs
    elif isinstance(data, dict) and kwargs:
        data = {**data, **kwargs}
    db = SessionLocal()
    try:
        sku = SkuPerformance(
            store_id=data.get("store_id", 1),
            date=datetime.date.today(),
            sku_name=data["sku_name"],
            category=data.get("category", ""),
            price=float(data.get("price", 0)),
            cost=float(data.get("cost", 0)),
            sales_count=0, sales_volume=0, revenue=0, gross_margin=0,
        )
        db.add(sku)
        db.commit()
        db.refresh(sku)
        return tool_result(data={"id": sku.id, "sku_name": sku.sku_name, "category": sku.category, "price": sku.price})
    except Exception as exc:
        db.rollback()
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def add_store_metric(data=None, **kwargs):
    """Add a daily business metric record.  Accepts either a single dict or keyword args."""
    if data is None:
        data = kwargs
    elif isinstance(data, dict) and kwargs:
        data = {**data, **kwargs}
    db = SessionLocal()
    try:
        rev = float(data.get("revenue", 0))
        metric = BusinessMetricsDaily(
            store_id=data.get("store_id", 1),
            date=_parse_date(data.get("date"), datetime.date.today()),
            revenue=rev, total_revenue=rev,
            order_count=int(data.get("order_count", 0)),
            avg_ticket=float(data.get("avg_ticket", 0)),
            gross_margin=float(data.get("gross_margin", 0)),
            refund_rate=float(data.get("refund_rate", 0)),
            delivery_ratio=float(data.get("delivery_ratio", 0)),
            net_profit=float(data.get("net_profit", rev * 0.15)),
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return tool_result(data={"id": metric.id, "store_id": metric.store_id, "date": str(metric.date), "revenue": metric.revenue})
    except Exception as exc:
        db.rollback()
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def add_staff_member(data=None, **kwargs):
    """Add a staff member.  Accepts either a single dict or keyword args."""
    if data is None:
        data = kwargs
    elif isinstance(data, dict) and kwargs:
        data = {**data, **kwargs}
    db = SessionLocal()
    try:
        staff = Staff(
            store_id=data.get("store_id", 1),
            name=data["name"],
            phone=data.get("phone", ""),
            role=data.get("role", "staff"),
            email=data.get("email", ""),
            id_number=data.get("id_number", ""),
            salary=float(data.get("salary", 0)),
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)
        return tool_result(data={"id": staff.id, "name": staff.name, "role": staff.role})
    except Exception as exc:
        db.rollback()
        return tool_result(False, error=str(exc))
    finally:
        db.close()


# =============================================================================
# New utility tools — search, detail, summary, ROI
# =============================================================================

def search_products(query: str = "", store_id: int | None = None, limit: int = 10) -> dict:
    """Fuzzy search products by name or category."""
    db = SessionLocal()
    try:
        q = db.query(SkuPerformance).filter(
            (SkuPerformance.sku_name.contains(query)) |
            (SkuPerformance.category.contains(query))
        )
        if store_id:
            q = q.filter(SkuPerformance.store_id == store_id)
        rows = q.group_by(SkuPerformance.sku_name, SkuPerformance.category).order_by(
            func.sum(SkuPerformance.sales_count).desc()
        ).limit(limit).all()
        return tool_result(data=[{
            "sku_name": r.sku_name, "category": r.category,
            "price": r.price, "cost": r.cost,
            "sales_count": r.sales_count,
        } for r in rows])
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def get_store_detail(store_id: int) -> dict:
    """Get detailed store info including staff count and recent metrics."""
    db = SessionLocal()
    try:
        store = db.query(Store).filter(Store.id == store_id).first()
        if not store:
            return tool_result(False, error="Store not found")
        staff_count = db.query(func.count(Staff.id)).filter(Staff.store_id == store_id, Staff.status == "active").scalar() or 0
        today = datetime.date.today()
        metric = db.query(
            func.sum(BusinessMetricsDaily.revenue),
            func.sum(BusinessMetricsDaily.order_count),
        ).filter(
            BusinessMetricsDaily.store_id == store_id,
            BusinessMetricsDaily.date == today,
        ).first()
        return tool_result(data={
            "id": store.id, "name": store.name, "city": store.city, "area": store.area,
            "manager_name": store.manager_name, "status": store.status,
            "staff_count": staff_count, "rating": store.rating,
            "today_revenue": round(metric[0] or 0, 2),
            "today_orders": int(metric[1] or 0),
        })
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def get_daily_summary(store_id: int | None = None, date: str | None = None) -> dict:
    """Get a one-day business summary: revenue, orders, top SKUs, anomalies."""
    db = SessionLocal()
    try:
        d = _parse_date(date, datetime.date.today())
        q = db.query(
            func.sum(BusinessMetricsDaily.revenue).label("revenue"),
            func.sum(BusinessMetricsDaily.order_count).label("orders"),
            func.avg(BusinessMetricsDaily.avg_ticket).label("avg_ticket"),
        ).filter(BusinessMetricsDaily.date == d)
        if store_id:
            q = q.filter(BusinessMetricsDaily.store_id == store_id)
        row = q.first()
        top_sku = db.query(
            SkuPerformance.sku_name,
            func.sum(SkuPerformance.sales_count).label("cnt"),
        ).filter(SkuPerformance.date == d)
        if store_id:
            top_sku = top_sku.filter(SkuPerformance.store_id == store_id)
        top_sku = top_sku.group_by(SkuPerformance.sku_name).order_by(desc("cnt")).limit(5).all()

        return tool_result(data={
            "date": str(d),
            "store_id": store_id,
            "revenue": round(row.revenue or 0, 2) if row else 0,
            "orders": int(row.orders or 0) if row else 0,
            "avg_ticket": round(row.avg_ticket or 0, 2) if row else 0,
            "top_skus": [{"name": s.sku_name, "sales": int(s.cnt)} for s in top_sku],
        })
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()


def calculate_roi(budget: float = 1000, revenue_generated: float = 0, conversion_rate: float = 0, expected_orders: int = 0) -> dict:
    """Calculate marketing ROI scenarios."""
    scenarios = []
    if revenue_generated:
        roi = (revenue_generated - budget) / budget * 100
        scenarios.append({"scenario": "actual", "budget": budget, "revenue": revenue_generated, "roi_pct": round(roi, 1), "verdict": "positive" if roi > 0 else "negative"})
    for cr in [0.02, 0.05, 0.08]:
        orders = int(budget / 5 * cr) if not expected_orders else expected_orders
        est_revenue = orders * 35
        roi = (est_revenue - budget) / budget * 100
        scenarios.append({"scenario": f"CR {cr*100:.0f}%", "budget": budget, "est_orders": orders, "est_revenue": round(est_revenue, 2), "roi_pct": round(roi, 1)})
    return tool_result(data={"budget": budget, "scenarios": scenarios})


def list_all_stores() -> dict:
    """List all stores with basic stats (revenue, staff count)."""
    db = SessionLocal()
    try:
        stores = db.query(Store).order_by(Store.id).all()
        result = []
        for s in stores:
            rev = db.query(func.sum(BusinessMetricsDaily.revenue)).filter(
                BusinessMetricsDaily.store_id == s.id,
                BusinessMetricsDaily.date >= datetime.date.today() - datetime.timedelta(days=7),
            ).scalar() or 0
            staff_count = db.query(func.count(Staff.id)).filter(
                Staff.store_id == s.id, Staff.status == "active"
            ).scalar() or 0
            result.append({
                "id": s.id, "name": s.name, "city": s.city, "status": s.status,
                "manager": s.manager_name, "staff_count": staff_count,
                "weekly_revenue": round(rev, 2),
            })
        return tool_result(data=result)
    except Exception as exc:
        return tool_result(False, error=str(exc))
    finally:
        db.close()
