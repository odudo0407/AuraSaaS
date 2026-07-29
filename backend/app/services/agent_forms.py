"""Agent-operated form previews and submissions for business CRUD actions."""

from __future__ import annotations

import datetime
import json
import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import AgentTrace, SkuPerformance, Staff, Store
from app.core.redis_client import redis_client


FORM_CACHE_TTL = 1800  # 30 minutes — form previews expire after this
BULK_PRODUCT_TARGET = "__ALL_PRODUCTS__"
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
PRODUCT_ENTITY_TOKENS = ["商品", "物品", "sku", "菜品", "产品"]


PRODUCT_FIELDS = [
    {"key": "store_id", "label": "门店", "type": "store", "required": True},
    {"key": "sku_name", "label": "商品名称", "type": "text", "required": True},
    {"key": "category", "label": "品类", "type": "text", "required": True},
    {"key": "price", "label": "售价", "type": "number", "required": True, "min": 0.01},
    {"key": "cost", "label": "成本", "type": "number", "required": False, "min": 0},
    {"key": "sales_count", "label": "初始销量", "type": "integer", "required": False, "min": 0},
    {"key": "notes", "label": "备注", "type": "text", "required": False},
]

PRODUCT_UPDATE_FIELDS = [
    {"key": "store_id", "label": "门店", "type": "store", "required": False},
    {"key": "target_product", "label": "目标商品", "type": "product_search", "required": False},
    {"key": "sku_name", "label": "商品名称", "type": "text", "required": False},
    {"key": "category", "label": "品类", "type": "text", "required": False},
    {"key": "price", "label": "售价", "type": "number", "required": False, "min": 0.01},
    {"key": "cost", "label": "成本", "type": "number", "required": False, "min": 0},
    {"key": "sales_count", "label": "销量", "type": "integer", "required": False, "min": 0},
    {"key": "notes", "label": "备注", "type": "text", "required": False},
]

PRODUCT_DELETE_FIELDS = [
    {"key": "store_id", "label": "门店", "type": "store", "required": False},
    {"key": "target_product", "label": "目标商品", "type": "product_search", "required": False},
    {"key": "delete_reason", "label": "删除原因", "type": "text", "required": True},
]

STAFF_FIELDS = [
    {"key": "store_id", "label": "门店", "type": "store", "required": True},
    {"key": "name", "label": "姓名", "type": "text", "required": True},
    {"key": "phone", "label": "手机号", "type": "text", "required": False},
    {"key": "role", "label": "角色", "type": "select", "required": True, "options": ["manager", "staff", "chef", "barista", "cashier"]},
    {"key": "hire_date", "label": "入职日期", "type": "date", "required": False},
    {"key": "salary", "label": "薪资", "type": "number", "required": False, "min": 0},
    {"key": "status", "label": "状态", "type": "select", "required": False, "options": ["active", "leave", "resigned"]},
    {"key": "notes", "label": "备注", "type": "text", "required": False},
]

STAFF_UPDATE_FIELDS = [
    {"key": "store_id", "label": "门店", "type": "store", "required": False},
    {"key": "target_staff", "label": "目标员工", "type": "text", "required": True},
    {"key": "name", "label": "姓名", "type": "text", "required": False},
    {"key": "phone", "label": "手机号", "type": "text", "required": False},
    {"key": "role", "label": "角色", "type": "select", "required": False, "options": ["manager", "staff", "chef", "barista", "cashier"]},
    {"key": "hire_date", "label": "入职日期", "type": "date", "required": False},
    {"key": "salary", "label": "薪资", "type": "number", "required": False, "min": 0},
    {"key": "status", "label": "状态", "type": "select", "required": False, "options": ["active", "leave", "resigned"]},
    {"key": "notes", "label": "备注", "type": "text", "required": False},
]

STAFF_DELETE_FIELDS = [
    {"key": "store_id", "label": "门店", "type": "store", "required": False},
    {"key": "target_staff", "label": "目标员工", "type": "text", "required": True},
    {"key": "handling", "label": "处理方式", "type": "select", "required": True, "options": ["resign", "delete"]},
    {"key": "reason", "label": "原因", "type": "text", "required": True},
]


def preview_agent_form(query: str, store_id: int | None = None, history: list[dict] | None = None) -> dict:
    """Create a fixed-schema form preview from a natural-language operation."""

    intent = detect_form_intent(query)
    form_id = f"form_{uuid.uuid4().hex}"
    fields = _fields_for(intent)
    rows = _prefill_rows(query, intent, store_id)
    preview = {
        "form_id": form_id,
        "form_type": intent["entity"],
        "action": intent["action"],
        "title": _title_for(intent),
        "description": _description_for(intent),
        "fields": fields,
        "rows": rows,
        "required_fields": [field["key"] for field in fields if field.get("required")],
        "risk_level": _risk_level(intent, rows),
        "requires_confirmation": _requires_confirmation(intent, rows),
        "source_query": query,
        "history": history or [],
    }
    redis_client.set_json(f"form:{form_id}", preview, ttl=FORM_CACHE_TTL)
    return preview


def detect_form_intent(query: str) -> dict:
    q = (query or "").lower()
    entity = "staff" if _has_any(q, ["员工", "人员", "店员", "收银", "店长", "barista", "cashier", "staff", "employee"]) else "product"
    if _has_any(q, ["删除", "删掉", "移除", "下架", "delete", "remove"]):
        action = "delete"
    elif _has_any(q, ["修改", "更新", "改成", "调整", "调价", "改价", "离职", "请假", "update", "edit"]):
        action = "update"
    else:
        action = "create"
    if entity == "staff" and _has_any(q, ["离职", "辞职"]):
        action = "delete"
    return {"entity": entity, "action": action}


def is_form_intent(query: str) -> bool:
    q = (query or "").lower()
    entity_hit = _has_any(q, [*PRODUCT_ENTITY_TOKENS, "员工", "人员", "店员", "收银", "店长", "staff", "employee"])
    action_hit = _has_any(q, ["添加", "增加", "新增", "录入", "批量", "删除", "下架", "修改", "更新", "调整", "离职", "add", "create", "delete", "update"])
    return entity_hit and action_hit


def submit_agent_form(db: Session, form_id: str, rows: list[dict], confirm: bool = False, user_id: int | None = None) -> dict:
    preview = redis_client.get_json(f"form:{form_id}")
    if not preview:
        return {"code": -1, "data": None, "message": "表格已过期，请重新生成。"}

    rows = rows or []
    validation_errors = validate_rows(db, preview, rows)
    if validation_errors:
        return {
            "code": 0,
            "data": {"status": "validation_failed", "errors": validation_errors, "rows": rows},
            "message": "表格校验失败，请修正后再提交。",
        }

    requires_confirmation = _requires_confirmation({"entity": preview["form_type"], "action": preview["action"]}, rows)
    if requires_confirmation and not confirm:
        return {
            "code": 0,
            "data": {
                "status": "confirmation_required",
                "requires_confirmation": True,
                "risk_level": _risk_level({"entity": preview["form_type"], "action": preview["action"]}, rows),
                "summary": _submission_summary(preview, rows),
            },
            "message": "该操作需要二次确认。",
        }

    result = _execute_rows(db, preview, rows)
    _save_form_trace(db, preview, rows, result, user_id=user_id)
    return {"code": 0, "data": result, "message": "表格已提交。"}


def validate_rows(db: Session, preview: dict, rows: list[dict]) -> list[dict]:
    errors = []
    fields = preview.get("fields", [])
    field_map = {field["key"]: field for field in fields}
    required = [field["key"] for field in fields if field.get("required")]

    for index, row in enumerate(rows):
        row_errors = {}
        for key in required:
            if _empty(row.get(key)):
                row_errors[key] = "必填"

        for key, field in field_map.items():
            value = row.get(key)
            if _empty(value):
                continue
            if field.get("type") in {"number", "integer"}:
                number = _to_float(value)
                if number is None:
                    row_errors[key] = "必须是数字"
                elif field.get("min") is not None and number < field["min"]:
                    row_errors[key] = f"不能小于 {field['min']}"
                elif field.get("type") == "integer" and int(number) != number:
                    row_errors[key] = "必须是整数"
            if key == "phone" and value and not re.fullmatch(r"[\d+\-\s]{6,20}", str(value)):
                row_errors[key] = "手机号格式不正确"
            if field.get("type") == "date" and value:
                try:
                    datetime.date.fromisoformat(str(value))
                except ValueError:
                    row_errors[key] = "日期格式应为 YYYY-MM-DD"

        store_id = row.get("store_id")
        if not _empty(store_id) and not db.query(Store).filter(Store.id == int(float(store_id))).first():
            row_errors["store_id"] = "门店不存在"

        if preview["form_type"] == "product" and preview["action"] in {"update", "delete"}:
            target = _normalize_product_target(row.get("target_product"))
            selected_id = row.get("target_product_id") or row.get("__selected_product_id")
            if not row_errors.get("target_product") and not target and _empty(selected_id):
                row_errors["target_product"] = "请选择目标商品"
            elif not row_errors.get("target_product") and not _find_product(db, row):
                row_errors["target_product"] = "未找到目标商品"
        if preview["form_type"] == "staff" and preview["action"] in {"update", "delete"}:
            if not row_errors.get("target_staff") and not _find_staff(db, row):
                row_errors["target_staff"] = "未找到目标员工"

        if row_errors:
            errors.append({"row_index": index, "fields": row_errors})
    return errors


def form_event_from_query(query: str, store_id: int | None = None, history: list[dict] | None = None) -> dict | None:
    if not is_form_intent(query):
        return None
    return preview_agent_form(query=query, store_id=store_id, history=history)


def _fields_for(intent: dict) -> list[dict]:
    if intent["entity"] == "staff":
        return {"create": STAFF_FIELDS, "update": STAFF_UPDATE_FIELDS, "delete": STAFF_DELETE_FIELDS}[intent["action"]]
    return {"create": PRODUCT_FIELDS, "update": PRODUCT_UPDATE_FIELDS, "delete": PRODUCT_DELETE_FIELDS}[intent["action"]]


def _prefill_rows(query: str, intent: dict, store_id: int | None) -> list[dict]:
    fragments = [item.strip() for item in re.split(r"[;\n；]+", query or "") if item.strip()]
    if len(fragments) <= 1:
        fragments = [query or ""]
    rows = [_prefill_one(fragment, intent, store_id) for fragment in fragments]
    return rows or [_prefill_one("", intent, store_id)]


def _is_bulk_product_delete_request(text: str) -> bool:
    q = (text or "").lower()
    has_product = _has_any(q, [*PRODUCT_ENTITY_TOKENS, "鍟嗗搧", "浜у搧", "鑿滃搧"])
    has_bulk = any(word in q for word in ["全部", "所有", "全都", "全删", "清空", "all"])
    has_delete = _has_any(q, ["删除", "删掉", "移除", "下架", "delete", "remove", "鍒犻櫎"])
    return has_product and has_bulk and has_delete


def _prefill_one(text: str, intent: dict, store_id: int | None) -> dict:
    row: dict[str, Any] = {"store_id": store_id or ""}
    if intent["entity"] == "staff":
        if intent["action"] == "delete":
            row.update({"target_staff": _extract_staff_name(text), "handling": "resign", "reason": ""})
        elif intent["action"] == "update":
            row.update({
                "target_staff": _extract_staff_name(text),
                "name": "",
                "phone": _extract_phone(text),
                "role": _extract_role(text),
                "hire_date": _extract_date(text),
                "salary": _extract_salary(text),
                "status": "resigned" if "离职" in text else "",
                "notes": "",
            })
        else:
            row.update({
                "name": _extract_staff_name(text),
                "phone": _extract_phone(text),
                "role": _extract_role(text) or "staff",
                "hire_date": _extract_date(text),
                "salary": _extract_salary(text),
                "status": "active",
                "notes": "",
            })
        return row

    if intent["action"] == "delete":
        if _is_bulk_product_delete_request(text):
            row.update({"target_product": BULK_PRODUCT_TARGET, "delete_reason": "用户要求清空全部商品"})
        else:
            row.update({"target_product": _extract_product_name(text), "delete_reason": ""})
    elif intent["action"] == "update":
        row.update({
            "target_product": _extract_product_name(text),
            "sku_name": "",
            "category": _extract_category(text),
            "price": _extract_price(text),
            "cost": _extract_cost(text),
            "sales_count": _extract_sales_count(text),
            "notes": "",
        })
    else:
        row.update({
            "sku_name": _extract_product_name(text),
            "category": _extract_category(text),
            "price": _extract_price(text),
            "cost": _extract_cost(text),
            "sales_count": _extract_sales_count(text) or 0,
            "notes": "",
        })
    return row


def _execute_rows(db: Session, preview: dict, rows: list[dict]) -> dict:
    successes = []
    failures = []
    for index, row in enumerate(rows):
        try:
            if preview["form_type"] == "product":
                item = _execute_product(db, preview["action"], row)
            else:
                item = _execute_staff(db, preview["action"], row)
            successes.append({"row_index": index, **item})
        except Exception as exc:
            db.rollback()
            failures.append({"row_index": index, "error": str(exc)})
    db.commit()
    return {
        "status": "submitted",
        "success_count": len(successes),
        "failure_count": len(failures),
        "successes": successes,
        "failures": failures,
        "form_type": preview["form_type"],
        "action": preview["action"],
    }


def _execute_product(db: Session, action: str, row: dict) -> dict:
    if action == "create":
        price = float(row.get("price") or 0)
        cost = float(row.get("cost") or 0)
        sales_count = int(float(row.get("sales_count") or 0))
        sku = SkuPerformance(
            store_id=int(float(row["store_id"])),
            date=datetime.date.today(),
            sku_name=str(row["sku_name"]).strip(),
            category=str(row["category"]).strip(),
            price=price,
            cost=cost,
            sales_count=sales_count,
            sales_volume=sales_count,
            revenue=price * sales_count,
            gross_margin=round((price - cost) / price, 4) if price else 0,
        )
        db.add(sku)
        db.flush()
        return {"id": sku.id, "name": sku.sku_name}
    if action == "delete" and _is_bulk_product_delete_row(row):
        rows = _bulk_product_query(db, row).all()
        for sku in rows:
            _delete_product_image(sku)
            db.delete(sku)
        return {"id": None, "name": "全部商品", "deleted_count": len(rows)}
    sku = _find_product(db, row)
    if not sku:
        raise ValueError("商品不存在")
    if action == "delete":
        _delete_product_image(sku)
        deleted = {"id": sku.id, "name": sku.sku_name}
        db.delete(sku)
        return deleted
    for field in ["sku_name", "category", "price", "cost", "sales_count", "store_id"]:
        if not _empty(row.get(field)):
            value = row[field]
            if field in {"price", "cost"}:
                value = float(value)
            elif field in {"sales_count", "store_id"}:
                value = int(float(value))
            setattr(sku, field, value)
            if field == "sales_count":
                sku.sales_volume = value
    if sku.price:
        sku.gross_margin = round((sku.price - (sku.cost or 0)) / sku.price, 4)
    sku.revenue = (sku.price or 0) * (sku.sales_count or 0)
    db.flush()
    return {"id": sku.id, "name": sku.sku_name}


def _execute_staff(db: Session, action: str, row: dict) -> dict:
    if action == "create":
        staff = Staff(
            store_id=int(float(row["store_id"])),
            name=str(row["name"]).strip(),
            phone=str(row.get("phone") or ""),
            role=str(row.get("role") or "staff"),
            hire_date=_date_or_none(row.get("hire_date")),
            salary=float(row.get("salary") or 0),
            status=str(row.get("status") or "active"),
            notes=str(row.get("notes") or ""),
        )
        db.add(staff)
        db.flush()
        return {"id": staff.id, "name": staff.name}
    staff = _find_staff(db, row)
    if not staff:
        raise ValueError("员工不存在")
    if action == "delete":
        result = {"id": staff.id, "name": staff.name}
        if row.get("handling") == "delete":
            db.delete(staff)
        else:
            staff.status = "resigned"
            if row.get("reason"):
                staff.notes = f"{staff.notes or ''}\n离职原因: {row.get('reason')}".strip()
        return result
    for field in ["name", "phone", "role", "hire_date", "salary", "status", "notes", "store_id"]:
        if not _empty(row.get(field)):
            value = row[field]
            if field == "salary":
                value = float(value)
            elif field == "store_id":
                value = int(float(value))
            elif field == "hire_date":
                value = _date_or_none(value)
            setattr(staff, field, value)
    db.flush()
    return {"id": staff.id, "name": staff.name}


def _delete_product_image(sku: SkuPerformance) -> None:
    image_url = getattr(sku, "image_url", "") or ""
    if not image_url.startswith("/uploads/"):
        return
    img_path = BASE_DIR / image_url.lstrip("/")
    if img_path.exists():
        img_path.unlink()


def _find_product(db: Session, row: dict):
    selected_id = row.get("target_product_id") or row.get("__selected_product_id")
    if not _empty(selected_id):
        try:
            q = db.query(SkuPerformance).filter(SkuPerformance.id == int(float(selected_id)))
            if not _empty(row.get("store_id")):
                q = q.filter(SkuPerformance.store_id == int(float(row["store_id"])))
            selected = q.first()
            if selected:
                return selected
        except (TypeError, ValueError):
            pass

    target = _normalize_product_target(row.get("target_product") or row.get("sku_name"))
    if not target:
        return None
    if target == BULK_PRODUCT_TARGET:
        return _bulk_product_query(db, row).first()
    q = db.query(SkuPerformance).filter(SkuPerformance.sku_name.contains(target))
    if not _empty(row.get("store_id")):
        q = q.filter(SkuPerformance.store_id == int(float(row["store_id"])))
    return q.order_by(SkuPerformance.id.desc()).first()


def _is_bulk_product_delete_row(row: dict) -> bool:
    return _normalize_product_target(row.get("target_product")) == BULK_PRODUCT_TARGET


def _normalize_product_target(value) -> str:
    target = str(value or "").strip()
    if target in {BULK_PRODUCT_TARGET, "全部商品", "所有商品"}:
        return BULK_PRODUCT_TARGET
    return target


def _bulk_product_query(db: Session, row: dict):
    q = db.query(SkuPerformance)
    if not _empty(row.get("store_id")):
        q = q.filter(SkuPerformance.store_id == int(float(row["store_id"])))
    return q.order_by(SkuPerformance.id.desc())


def _find_staff(db: Session, row: dict):
    target = str(row.get("target_staff") or row.get("name") or "").strip()
    if not target:
        return None
    q = db.query(Staff).filter(or_(Staff.name.contains(target), Staff.phone.contains(target)))
    if not _empty(row.get("store_id")):
        q = q.filter(Staff.store_id == int(float(row["store_id"])))
    return q.order_by(Staff.id.desc()).first()


def _save_form_trace(db: Session, preview: dict, rows: list[dict], result: dict, user_id: int | None = None) -> None:
    trace_id = f"form-{uuid.uuid4().hex}"
    steps = [{
        "node": "agent_form_submit",
        "time": datetime.datetime.now().isoformat(),
        "duration_ms": 0,
        "input_summary": preview.get("source_query", "")[:180],
        "event": {
            "type": "form_submitted",
            "title": preview.get("title"),
            "content": json.dumps(result, ensure_ascii=False),
            "form_id": preview.get("form_id"),
            "done": True,
        },
    }]
    trace = AgentTrace(
        trace_id=trace_id,
        user_query=preview.get("source_query") or f"{preview['form_type']} {preview['action']}",
        store_id=_first_store_id(rows),
        status="completed",
        steps_json=json.dumps(steps, ensure_ascii=False),
        final_answer=json.dumps({"rows": rows, "result": result, "user_id": user_id}, ensure_ascii=False),
    )
    db.add(trace)


def _title_for(intent: dict) -> str:
    entity = "人员" if intent["entity"] == "staff" else "商品"
    action = {"create": "新增", "update": "编辑", "delete": "删除/离职"}[intent["action"]]
    return f"{action}{entity}表格"


def _description_for(intent: dict) -> str:
    if intent["action"] == "create":
        return "请补全必填信息后提交，系统会直接创建记录。"
    return "请确认目标对象和变更信息；敏感操作提交后需要二次确认。"


def _risk_level(intent: dict, rows: list[dict]) -> str:
    if intent["action"] == "delete":
        return "high"
    if len(rows) > 5:
        return "medium"
    if intent["entity"] == "staff" and any(not _empty(row.get("salary")) for row in rows):
        return "medium"
    return "low"


def _requires_confirmation(intent: dict, rows: list[dict]) -> bool:
    return _risk_level(intent, rows) != "low"


def _submission_summary(preview: dict, rows: list[dict]) -> str:
    return f"{preview.get('title')}包含 {len(rows)} 行，风险等级为 {preview.get('risk_level', 'low')}。"


def _extract_price(text: str):
    return _extract_number_after(text, ["售价", "价格", "卖", "price"])


def _extract_cost(text: str):
    return _extract_number_after(text, ["成本", "cost"])


def _extract_salary(text: str):
    return _extract_number_after(text, ["薪资", "工资", "salary"])


def _extract_sales_count(text: str):
    return _extract_number_after(text, ["销量", "初始销量", "sales"])


def _extract_number_after(text: str, labels: list[str]):
    for label in labels:
        match = re.search(rf"{label}\s*(?:是|为|:|：)?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    match = re.search(r"(?:¥|￥|楼)?\s*(\d+(?:\.\d+)?)\s*元", text)
    return float(match.group(1)) if match else ""


def _extract_phone(text: str) -> str:
    match = re.search(r"(1[3-9]\d{9})", text or "")
    return match.group(1) if match else ""


def _extract_date(text: str) -> str:
    match = re.search(r"(20\d{2}-\d{1,2}-\d{1,2})", text or "")
    if not match:
        return ""
    parts = [int(part) for part in match.group(1).split("-")]
    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"


def _extract_role(text: str) -> str:
    role_map = {"店长": "manager", "经理": "manager", "收银": "cashier", "厨师": "chef", "咖啡师": "barista", "员工": "staff"}
    for key, value in role_map.items():
        if key in (text or ""):
            return value
    return ""


def _extract_category(text: str) -> str:
    for label in ["品类", "分类", "category"]:
        match = re.search(rf"{label}\s*(?:是|为|:|：)?\s*([\w\u4e00-\u9fff]+)", text or "", re.IGNORECASE)
        if match:
            return match.group(1)
    for category in ["饮品", "甜品", "主食", "小吃", "咖啡", "热菜", "凉菜"]:
        if category in (text or ""):
            return category
    return ""


def _extract_product_name(text: str) -> str:
    patterns = [
        r"(?:商品|物品|产品|菜品|sku|SKU)(?:名称|名字|叫|是|为|:|：)?\s*([\w\u4e00-\u9fff]+)",
        r"(?:添加|增加|新增|录入|下架|删除|删掉|移除|修改|更新)(?:一款|一个|一份)?\s*([\w\u4e00-\u9fff]+)",
        r"把\s*([\w\u4e00-\u9fff]+)\s*(?:删除|删掉|移除|下架|修改|更新)",
        r"(?:商品|物品|产品|菜品|sku|SKU)(?:名称|名)?(?:叫|为|是|:|：)?\s*([\w\u4e00-\u9fff]+)",
        r"(?:添加|增加|新增|录入|下架|删除|修改|更新)(?:一款|一个)?\s*([\w\u4e00-\u9fff]+)",
    ]
    return _first_match(text, patterns)


def _extract_staff_name(text: str) -> str:
    patterns = [
        r"(?:员工|人员|店员|收银员|店长)(?:姓名|名字|叫|为|是|:|：)?\s*([\w\u4e00-\u9fff]{2,12})",
        r"(?:新增|添加|录入|删除|离职|修改|更新|把)\s*([\w\u4e00-\u9fff]{2,12})",
    ]
    name = _first_match(text, patterns)
    for word in ["一个", "一名", "收银员", "员工", "店员"]:
        name = name.replace(word, "")
    return name


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            value = re.sub(r"(售价|价格|成本|电话|手机号|薪资|工资|品类|分类|原因|吗|么).*$", "", value).strip()
            return re.sub(r"(售价|价格|成本|电话|手机号|薪资|工资|品类|分类).*$", "", value).strip()
    return ""


def _date_or_none(value):
    if _empty(value):
        return None
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _empty(value) -> bool:
    return value is None or value == ""


def _has_any(value: str, tokens: list[str]) -> bool:
    value = (value or "").lower()
    delete_words = {"删除", "删掉", "删了", "移除", "下架", "清空", "全删", "delete", "remove"}
    update_words = {"修改", "更新", "改成", "调整", "调价", "改价", "update", "edit"}

    for token in tokens:
        for variant in _token_variants(token):
            if variant and variant in value:
                return True
            if variant in {"删除", "删掉", "移除", "下架", "delete", "remove"} and any(word in value for word in delete_words):
                return True
            if variant in {"修改", "更新", "调整", "update", "edit"} and any(word in value for word in update_words):
                return True
    return False


def _token_variants(token: str) -> set[str]:
    variants = {(token or "").lower()}
    # Some legacy source strings are UTF-8 Chinese decoded as GBK. Decode that
    # shape at match time so new Chinese prompts still trigger the form flow.
    try:
        variants.add(token.encode("gbk").decode("utf-8").lower())
    except UnicodeError:
        pass
    return variants


def _first_store_id(rows: list[dict]) -> int | None:
    for row in rows:
        if not _empty(row.get("store_id")):
            return int(float(row["store_id"]))
    return None
