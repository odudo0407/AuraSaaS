"""Smart import API: CSV/Excel upload with semantic mapping and cleaning."""

from __future__ import annotations

import csv
import datetime
import io
import json
import re
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.deps import get_current_user
from app.database import get_db
from app.models.models import BusinessMetricsDaily, MarketingCampaign, SkuPerformance, Staff, Store, User
from app.services.data_cleaning import clean_rows, normalize_target_table
from app.services.data_cleaning_rules import COMMON_ALIASES
from app.services.deepseek_client import chat as llm_chat, has_valid_api_key

router = APIRouter(prefix="/api/agent", tags=["agent-import"])


KNOWN_FIELDS = {
    "store_name": "store.name",
    "门店名称": "store.name",
    "店名": "store.name",
    "city": "store.city",
    "城市": "store.city",
    "address": "store.address",
    "地址": "store.address",
    "area": "store.area",
    "商圈": "store.area",
    "manager": "store.manager_name",
    "店长": "store.manager_name",
    "seats": "store.seats",
    "座位数": "store.seats",
    "staff_count": "store.staff_count",
    "员工数": "store.staff_count",
    "rating": "store.rating",
    "评分": "store.rating",
    "sku_name": "sku.sku_name",
    "product_name": "sku.sku_name",
    "商品名称": "sku.sku_name",
    "category": "sku.category",
    "品类": "sku.category",
    "price": "sku.price",
    "售价": "sku.price",
    "cost": "sku.cost",
    "成本": "sku.cost",
    "sales_count": "sku.sales_count",
    "销量": "sku.sales_count",
    "revenue": "sku.revenue",
    "营收": "sku.revenue",
    "gross_margin": "sku.gross_margin",
    "毛利率": "sku.gross_margin",
    "refund_rate": "sku.refund_rate",
    "退单率": "sku.refund_rate",
    "date": "metrics.date",
    "日期": "metrics.date",
    "store_id": "metrics.store_id",
    "门店ID": "metrics.store_id",
    "order_count": "metrics.order_count",
    "订单数": "metrics.order_count",
    "avg_ticket": "metrics.avg_ticket",
    "客单价": "metrics.avg_ticket",
    "net_profit": "metrics.net_profit",
    "净利润": "metrics.net_profit",
    "platform_commission": "metrics.platform_commission",
    "平台抽佣": "metrics.platform_commission",
    "delivery_ratio": "metrics.delivery_ratio",
    "外卖占比": "metrics.delivery_ratio",
    "dine_in_ratio": "metrics.dine_in_ratio",
    "堂食占比": "metrics.dine_in_ratio",
    "new_customers": "metrics.new_customers",
    "新客数": "metrics.new_customers",
    "returning_customers": "metrics.returning_customers",
    "回头客": "metrics.returning_customers",
    "campaign_name": "campaign.campaign_name",
    "活动名称": "campaign.campaign_name",
    "channel": "campaign.channel",
    "渠道": "campaign.channel",
    "budget": "campaign.budget",
    "预算": "campaign.budget",
    "target_audience": "campaign.target_audience",
    "目标受众": "campaign.target_audience",
    "content": "campaign.content_text",
    "文案": "campaign.content_text",
    "staff_name": "staff.name",
    "姓名": "staff.name",
    "店员姓名": "staff.name",
    "phone": "staff.phone",
    "手机号": "staff.phone",
    "mobile": "staff.phone",
    "role": "staff.role",
    "岗位": "staff.role",
    "email": "staff.email",
    "邮箱": "staff.email",
    "id_number": "staff.id_number",
    "身份证号": "staff.id_number",
    "hire_date": "staff.hire_date",
    "入职日期": "staff.hire_date",
    "status": "staff.status",
    "状态": "staff.status",
    "salary": "staff.salary",
    "薪资": "staff.salary",
    "notes": "staff.notes",
    "备注": "staff.notes",
}


def _sse(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _read_file_content(content: bytes, filename: str) -> tuple[list[str], list[list[Any]], str]:
    lower_name = (filename or "").lower()
    if lower_name.endswith(".csv"):
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        lines = list(reader)
        if not lines:
            return [], [], "csv"
        return [str(h).strip() for h in lines[0]], lines[1:], "csv"

    if lower_name.endswith((".xlsx", ".xls", ".xlsm")):
        import pandas as pd

        df = pd.read_excel(io.BytesIO(content))
        headers = [str(h).strip() for h in df.columns.tolist()]
        return headers, df.values.tolist(), "excel"

    raise ValueError(f"Unsupported file format: {filename}. Please upload CSV or Excel.")


def _ai_semantic_map(headers: list[str], sample_rows: list[list[Any]], target_hint: str | None = None) -> dict:
    if target_hint:
        target = normalize_target_table(target_hint)
        return {
            "mapping": {str(header).strip(): _fallback_field_match(str(header), target) for header in headers},
            "target_table": target,
            "confidence": "high",
        }

    fields_desc = "\n".join(f"- {label}: {field}" for label, field in KNOWN_FIELDS.items())
    sample_text = "\n".join(
        f"row {i + 1}: {dict(zip(headers, [str(value)[:40] for value in row]))}"
        for i, row in enumerate(sample_rows[:3])
    )
    prompt = f"""You are a data import expert. Map each uploaded column to the best database field.

Available fields:
{fields_desc}

Headers: {json.dumps(headers, ensure_ascii=False)}
Sample rows:
{sample_text}

Return JSON only:
{{"mapping": {{"original column": "database.field or null"}}, "target_table": "store|sku|metrics|campaign|staff", "confidence": "high|medium|low"}}
"""

    try:
        if has_valid_api_key():
            result = llm_chat(
                "You are a precise data import expert. Return JSON only.",
                prompt,
                json.dumps({"mapping": {}, "target_table": "sku", "confidence": "low"}),
                temperature=0.1,
                max_tokens=800,
            )
            json_match = re.search(r"\{[\s\S]*\}", result or "")
            if json_match:
                parsed = json.loads(json_match.group())
                parsed["target_table"] = normalize_target_table(parsed.get("target_table"))
                parsed["mapping"] = _coerce_mapping_to_target(parsed.get("mapping", {}), parsed["target_table"])
                return parsed
    except Exception:
        pass

    target = _guess_target_table(headers)
    mapping = {}
    for header in headers:
        header_text = str(header).strip()
        mapping[header_text] = _fallback_field_match(header_text, target)

    return {"mapping": mapping, "target_table": target, "confidence": "low"}


def _guess_target_table(headers: list[str]) -> str:
    matches = {"store": 0, "sku": 0, "metrics": 0, "campaign": 0, "staff": 0}
    matched_fields = {target: set() for target in matches}
    for header in headers:
        for target in matches:
            field = _fallback_field_match(str(header), target)
            if field:
                matches[target] += 1
                matched_fields[target].add(field)

    if "campaign.campaign_name" in matched_fields["campaign"]:
        return "campaign"
    if "staff.name" in matched_fields["staff"]:
        return "staff"
    if "sku.sku_name" in matched_fields["sku"]:
        return "sku"
    if matched_fields["metrics"] & {
        "metrics.order_count",
        "metrics.avg_ticket",
        "metrics.net_profit",
        "metrics.platform_commission",
        "metrics.delivery_ratio",
        "metrics.dine_in_ratio",
    }:
        return "metrics"
    if {"metrics.date", "metrics.revenue"}.issubset(matched_fields["metrics"]):
        return "metrics"
    if "store.name" in matched_fields["store"]:
        return "store"
    return max(matches, key=matches.get) if any(matches.values()) else "sku"


def _fallback_field_match(header: str, target: str | None = None) -> str | None:
    header_key = re.sub(r"[\s_\-./]+", "", header.strip().lower())
    if target:
        for field, aliases in COMMON_ALIASES.items():
            if not field.startswith(f"{target}."):
                continue
            candidates = [field, *aliases]
            if any(header_key == re.sub(r"[\s_\-./]+", "", candidate.strip().lower()) for candidate in candidates):
                return field
    for label, field in KNOWN_FIELDS.items():
        label_key = re.sub(r"[\s_\-./]+", "", label.strip().lower())
        if header_key == label_key or header_key in label_key or label_key in header_key:
            return field
    return None


def _coerce_mapping_to_target(mapping: dict, target: str) -> dict:
    coerced = {}
    for header, field in (mapping or {}).items():
        if field and str(field).startswith(f"{target}."):
            coerced[header] = field
        else:
            coerced[header] = _fallback_field_match(str(header), target) or field
    return coerced


def _get_import_context(db: Session, target_table: str) -> dict:
    valid_store_ids = {store.id for store in db.query(Store).all()}
    default_store_id = next(iter(valid_store_ids), 1)
    return {
        "valid_store_ids": valid_store_ids,
        "default_store_id": default_store_id,
        "existing_keys": _existing_keys(db, target_table),
    }


def _existing_keys(db: Session, target_table: str) -> set[tuple]:
    target = normalize_target_table(target_table)
    if target == "store":
        return {(row.name,) for row in db.query(Store.name).all()}
    if target == "sku":
        return {(row.store_id, row.date, row.sku_name) for row in db.query(SkuPerformance.store_id, SkuPerformance.date, SkuPerformance.sku_name).all()}
    if target == "metrics":
        return {(row.store_id, row.date) for row in db.query(BusinessMetricsDaily.store_id, BusinessMetricsDaily.date).all()}
    if target == "campaign":
        return {(row.campaign_name,) for row in db.query(MarketingCampaign.campaign_name).all()}
    if target == "staff":
        return {(row.store_id, row.name) for row in db.query(Staff.store_id, Staff.name).all()}
    return set()


def _import_cleaned_rows(target_table: str, rows: list[dict[str, Any]], db: Session) -> dict:
    target = normalize_target_table(target_table)
    imported = 0
    errors = []

    for row_index, row in enumerate(rows, start=1):
        try:
            if target == "store":
                db.add(Store(
                    name=row.get("store.name"),
                    city=row.get("store.city") or "",
                    address=row.get("store.address") or "",
                    area=row.get("store.area") or "",
                    manager_name=row.get("store.manager_name") or "",
                    seats=row.get("store.seats") or 0,
                    staff_count=row.get("store.staff_count") or 0,
                    rating=row.get("store.rating") or 4.5,
                ))
            elif target == "sku":
                price = row.get("sku.price") or 0
                cost = row.get("sku.cost") or 0
                sales_count = row.get("sku.sales_count") or 0
                revenue = row.get("sku.revenue")
                db.add(SkuPerformance(
                    store_id=row.get("sku.store_id") or 1,
                    date=row.get("sku.date") or datetime.date.today(),
                    sku_name=row.get("sku.sku_name"),
                    category=row.get("sku.category") or "未分类",
                    price=price,
                    cost=cost,
                    sales_count=sales_count,
                    sales_volume=sales_count,
                    revenue=revenue if revenue is not None else price * sales_count,
                    gross_margin=row.get("sku.gross_margin") if row.get("sku.gross_margin") is not None else (round((price - cost) / price, 4) if price else 0),
                    refund_rate=row.get("sku.refund_rate") or 0,
                ))
            elif target == "metrics":
                revenue = row.get("metrics.revenue") or 0
                orders = row.get("metrics.order_count") or 0
                avg_ticket = row.get("metrics.avg_ticket") or (revenue / orders if orders else 0)
                db.add(BusinessMetricsDaily(
                    store_id=row.get("metrics.store_id") or 1,
                    date=row.get("metrics.date"),
                    revenue=revenue,
                    total_revenue=revenue,
                    order_count=orders,
                    avg_ticket=avg_ticket,
                    avg_order_value=avg_ticket,
                    gross_margin=row.get("metrics.gross_margin") or 0,
                    refund_rate=row.get("metrics.refund_rate") or 0,
                    platform_commission=row.get("metrics.platform_commission") or 0,
                    net_profit=row.get("metrics.net_profit") or 0,
                    delivery_ratio=row.get("metrics.delivery_ratio") or 0,
                    dine_in_ratio=row.get("metrics.dine_in_ratio") or 0,
                    new_customers=row.get("metrics.new_customers") or 0,
                    returning_customers=row.get("metrics.returning_customers") or 0,
                ))
            elif target == "campaign":
                db.add(MarketingCampaign(
                    campaign_name=row.get("campaign.campaign_name"),
                    channel=row.get("campaign.channel") or "全渠道",
                    budget=row.get("campaign.budget") or 0,
                    target_audience=row.get("campaign.target_audience") or "",
                    content_text=row.get("campaign.content_text") or "",
                ))
            elif target == "staff":
                db.add(Staff(
                    store_id=row.get("staff.store_id") or 1,
                    name=row.get("staff.name"),
                    phone=row.get("staff.phone") or "",
                    role=row.get("staff.role") or "staff",
                    email=row.get("staff.email") or "",
                    id_number=row.get("staff.id_number") or "",
                    hire_date=row.get("staff.hire_date"),
                    status=row.get("staff.status") or "active",
                    salary=row.get("staff.salary") or 0,
                    notes=row.get("staff.notes") or "",
                ))
            imported += 1
        except Exception as exc:
            errors.append(f"row {row_index}: {exc}")

    if errors:
        db.rollback()
    else:
        db.commit()

    return {"imported": imported if not errors else 0, "errors": errors[:10], "target_table": target}


@router.post("/import-data")
async def agent_import_data(
    file: UploadFile = File(...),
    import_type: str | None = Form(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Stream smart import progress: header detection, mapping, cleaning, import."""

    async def event_stream():
        yield _sse({
            "type": "phase",
            "phase": "header_detect",
            "title": "识别表头",
            "content": f"正在读取文件: {file.filename}",
            "done": False,
        })

        try:
            headers, rows, file_type = _read_file_content(await file.read(), file.filename or "")
        except Exception as exc:
            yield _sse({"type": "error", "content": str(exc), "done": True})
            return

        if not headers:
            yield _sse({"type": "error", "content": "文件为空或无法解析表头", "done": True})
            return

        yield _sse({
            "type": "progress",
            "phase": "header_detect",
            "title": "识别表头",
            "content": f"检测到 {len(headers)} 列，{len(rows)} 行",
            "headers": headers,
            "row_count": len(rows),
            "file_type": file_type,
            "done": True,
        })

        yield _sse({
            "type": "phase",
            "phase": "semantic_map",
            "title": "语义映射",
            "content": "正在识别字段含义...",
            "done": False,
        })
        mapping_result = _ai_semantic_map(headers, rows[:5], target_hint=import_type)
        target_table = normalize_target_table(mapping_result.get("target_table"))

        yield _sse({
            "type": "progress",
            "phase": "semantic_map",
            "title": "语义映射",
            "content": f"映射完成，目标表: {target_table}",
            "mapping": mapping_result.get("mapping", {}),
            "target_table": target_table,
            "confidence": mapping_result.get("confidence", "low"),
            "done": True,
        })

        yield _sse({
            "type": "phase",
            "phase": "clean_validate",
            "title": "清洗校验",
            "content": f"正在清洗校验 {len(rows)} 行数据...",
            "done": False,
        })

        context = _get_import_context(db, target_table)
        cleaning_result = clean_rows(
            target_table,
            mapping_result.get("mapping", {}),
            headers,
            rows,
            valid_store_ids=context["valid_store_ids"],
            existing_keys=context["existing_keys"],
            default_store_id=context["default_store_id"],
        )
        report = cleaning_result["report"]

        yield _sse({
            "type": "progress",
            "phase": "clean_validate",
            "title": "清洗校验",
            "content": f"可导入 {report['valid_rows']} 行，跳过 {report['skipped_rows']} 行，修正 {report['fixed_cells']} 个单元格",
            "cleaning_report": report,
            "preview_rows": cleaning_result["cleaned_rows"][:10],
            "done": True,
        })

        yield _sse({
            "type": "phase",
            "phase": "import",
            "title": "导入数据库",
            "content": f"正在导入 {report['valid_rows']} 行数据...",
            "done": False,
        })

        stats = _import_cleaned_rows(target_table, cleaning_result["cleaned_rows"], db)
        stats["skipped"] = report["skipped_rows"]
        stats["cleaning_report"] = report

        yield _sse({
            "type": "progress",
            "phase": "import",
            "title": "导入数据库",
            "content": f"成功导入 {stats['imported']} 行，跳过 {stats['skipped']} 行，错误 {len(stats['errors'])} 条",
            "stats": stats,
            "done": True,
        })

        yield _sse({
            "type": "done",
            "phase": "complete",
            "title": "导入完成",
            "content": f"共导入 {stats['imported']} 行数据到 {stats['target_table']} 表",
            "stats": stats,
            "done": True,
        })

    return EventSourceResponse(event_stream(), media_type="text/event-stream; charset=utf-8")
