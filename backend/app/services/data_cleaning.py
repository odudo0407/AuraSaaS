"""Reusable data-cleaning pipeline for CSV/Excel imports."""

from __future__ import annotations

import datetime
import math
import re
from dataclasses import dataclass, field
from typing import Any

from app.services.data_cleaning_rules import COMMON_ALIASES, TABLE_RULES, TARGET_ALIASES


EMPTY_VALUES = {"", "none", "null", "nan", "na", "n/a", "-", "--"}
MONEY_CHARS = ("¥", "￥", "$", "元", "人民币", "RMB", "rmb", "楼")


@dataclass
class CleaningIssue:
    row: int
    field: str
    message: str
    value: Any = None

    def to_dict(self) -> dict:
        return {
            "row": self.row,
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }


@dataclass
class CleaningReport:
    total_rows: int = 0
    valid_rows: int = 0
    skipped_rows: int = 0
    fixed_cells: int = 0
    duplicate_rows: int = 0
    warnings: list[CleaningIssue] = field(default_factory=list)
    errors: list[CleaningIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "skipped_rows": self.skipped_rows,
            "fixed_cells": self.fixed_cells,
            "duplicate_rows": self.duplicate_rows,
            "warnings": [issue.to_dict() for issue in self.warnings],
            "errors": [issue.to_dict() for issue in self.errors],
        }


def normalize_target_table(target_table: str | None) -> str:
    key = str(target_table or "sku").strip().lower()
    return TARGET_ALIASES.get(key, key)


def normalize_headers(headers: list[str], mapping: dict | None = None, target_table: str | None = None) -> dict:
    """Return a header -> canonical field mapping."""
    normalized = {}
    mapping = mapping or {}
    alias_lookup = _alias_lookup()
    target = normalize_target_table(target_table) if target_table else None

    for raw_header in headers:
        header = str(raw_header or "").strip()
        mapped = mapping.get(header)
        if mapped:
            normalized[header] = mapped
            continue
        normalized[header] = _target_field_match(header, target) or alias_lookup.get(_header_key(header))

    return normalized


def clean_rows(
    target_table: str,
    mapping: dict,
    headers: list[str],
    rows: list[list[Any]] | list[dict[str, Any]],
    *,
    valid_store_ids: set[int] | None = None,
    existing_keys: set[tuple] | None = None,
    default_store_id: int = 1,
    today: datetime.date | None = None,
) -> dict:
    """Clean, validate and summarize uploaded rows.

    The returned rows use canonical field names like ``metrics.revenue`` so
    import callers do not have to repeat value parsing and validation logic.
    """
    target = normalize_target_table(target_table)
    rules = TABLE_RULES.get(target)
    if not rules:
        raise ValueError(f"Unsupported import target: {target_table}")

    today = today or datetime.date.today()
    report = CleaningReport(total_rows=len(rows))
    cleaned_rows: list[dict[str, Any]] = []
    header_mapping = normalize_headers(headers, mapping, target)
    seen_keys: set[tuple] = set()
    existing_keys = existing_keys or set()

    for row_number, raw_row in enumerate(rows, start=2):
        row = _row_to_dict(headers, raw_row)
        if _is_empty_row(row):
            report.skipped_rows += 1
            continue

        cleaned = dict(rules.get("defaults", {}))
        if target in {"sku", "metrics", "staff"} and "store_id" not in cleaned:
            prefix = _target_prefix(target)
            cleaned[f"{prefix}.store_id"] = default_store_id

        row_errors: list[CleaningIssue] = []

        for header, value in row.items():
            field_name = header_mapping.get(str(header).strip())
            if not field_name:
                continue
            field_type = rules.get("types", {}).get(field_name, "str")
            parsed, fixed, error = normalize_value(value, field_type, today=today)
            if error:
                row_errors.append(CleaningIssue(row_number, field_name, error, _display_value(value)))
                continue
            if fixed:
                report.fixed_cells += 1
            cleaned[field_name] = parsed

        _fill_derived_values(target, cleaned, today)
        _validate_required(rules, cleaned, row_number, row_errors)
        _validate_ranges(rules, cleaned, row_number, row_errors, report)
        _validate_store_id(target, cleaned, valid_store_ids, row_number, row_errors)
        _validate_consistency(target, cleaned, row_number, report)

        dedupe_key = _make_dedupe_key(rules, cleaned)
        if dedupe_key:
            if dedupe_key in seen_keys or dedupe_key in existing_keys:
                report.duplicate_rows += 1
                row_errors.append(CleaningIssue(row_number, ",".join(rules.get("dedupe_key", [])), "duplicate row", dedupe_key))
            seen_keys.add(dedupe_key)

        if row_errors:
            report.errors.extend(row_errors)
            report.skipped_rows += 1
            continue

        cleaned_rows.append(cleaned)

    report.valid_rows = len(cleaned_rows)
    return {"cleaned_rows": cleaned_rows, "report": report.to_dict()}


def normalize_value(value: Any, field_type: str = "str", *, today: datetime.date | None = None) -> tuple[Any, bool, str | None]:
    """Normalize one value and return ``(value, changed, error)``."""
    if _is_empty(value):
        return None, False, None

    today = today or datetime.date.today()
    original = value

    if field_type == "str":
        text = str(value).strip()
        return text, text != original, None
    if field_type == "date":
        parsed = _parse_date(value, today)
        if parsed is None:
            return None, False, "invalid date"
        return parsed, parsed != original, None
    if field_type == "int":
        number = _parse_number(value)
        if number is None:
            return None, False, "invalid integer"
        return int(number), int(number) != original, None
    if field_type in {"float", "money"}:
        number = _parse_number(value)
        if number is None:
            return None, False, "invalid number"
        return float(number), float(number) != original, None
    if field_type == "percent":
        percent = _parse_percent(value)
        if percent is None:
            return None, False, "invalid percent"
        return percent, percent != original, None

    return value, False, None


def _alias_lookup() -> dict[str, str]:
    lookup = {}
    for field_name, aliases in COMMON_ALIASES.items():
        lookup[_header_key(field_name)] = field_name
        for alias in aliases:
            lookup[_header_key(alias)] = field_name
    return lookup


def _target_field_match(header: str, target: str | None) -> str | None:
    if not target:
        return None
    key = _header_key(header)
    for field_name, aliases in COMMON_ALIASES.items():
        if not field_name.startswith(f"{target}."):
            continue
        if key == _header_key(field_name) or any(key == _header_key(alias) for alias in aliases):
            return field_name
    return None


def _target_prefix(target: str) -> str:
    return "sku" if target == "sku" else target


def _header_key(value: str) -> str:
    return re.sub(r"[\s_\-./]+", "", str(value or "").strip().lower())


def _row_to_dict(headers: list[str], row: list[Any] | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, dict):
        return {str(k).strip(): v for k, v in row.items() if str(k or "").strip()}
    return {str(header).strip(): row[i] if i < len(row) else None for i, header in enumerate(headers)}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip().lower() in EMPTY_VALUES


def _is_empty_row(row: dict[str, Any]) -> bool:
    return not any(not _is_empty(value) for value in row.values())


def _parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value)):
        return float(value)
    text = str(value).strip()
    for char in MONEY_CHARS:
        text = text.replace(char, "")
    text = text.replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_percent(value: Any) -> float | None:
    has_percent_sign = isinstance(value, str) and "%" in value
    number = _parse_number(value)
    if number is None:
        return None
    if has_percent_sign or abs(number) > 1:
        return number / 100
    return number


def _parse_date(value: Any, today: datetime.date) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, (int, float)) and value > 20000:
        return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(value))
    if hasattr(value, "date"):
        try:
            date_value = value.date()
            if isinstance(date_value, datetime.date):
                return date_value
        except Exception:
            pass

    text = str(value).strip()
    if text.lower() in {"today", "今天"}:
        return today
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y%m%d", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _fill_derived_values(target: str, cleaned: dict[str, Any], today: datetime.date) -> None:
    if target == "sku":
        cleaned.setdefault("sku.date", today)
        price = cleaned.get("sku.price") or 0
        cost = cleaned.get("sku.cost") or 0
        sales = cleaned.get("sku.sales_count") or 0
        cleaned.setdefault("sku.revenue", price * sales)
        if "sku.gross_margin" not in cleaned and price:
            cleaned["sku.gross_margin"] = round((price - cost) / price, 4)
    if target == "metrics":
        revenue = cleaned.get("metrics.revenue") or 0
        orders = cleaned.get("metrics.order_count") or 0
        if "metrics.avg_ticket" not in cleaned and orders:
            cleaned["metrics.avg_ticket"] = revenue / orders


def _validate_required(rules: dict, cleaned: dict[str, Any], row_number: int, errors: list[CleaningIssue]) -> None:
    for field_name in rules.get("required", []):
        if _is_empty(cleaned.get(field_name)):
            errors.append(CleaningIssue(row_number, field_name, "required field missing"))


def _validate_ranges(rules: dict, cleaned: dict[str, Any], row_number: int, errors: list[CleaningIssue], report: CleaningReport) -> None:
    for field_name, limits in rules.get("ranges", {}).items():
        value = cleaned.get(field_name)
        if value is None:
            continue
        minimum = limits.get("min")
        maximum = limits.get("max")
        if minimum is not None and value < minimum:
            errors.append(CleaningIssue(row_number, field_name, f"value below minimum {minimum}", value))
        elif maximum is not None and value > maximum:
            issue = CleaningIssue(row_number, field_name, f"value above maximum {maximum}", value)
            if field_name.endswith(("refund_rate", "delivery_ratio", "dine_in_ratio")):
                errors.append(issue)
            else:
                report.warnings.append(issue)


def _validate_store_id(target: str, cleaned: dict[str, Any], valid_store_ids: set[int] | None, row_number: int, errors: list[CleaningIssue]) -> None:
    if not valid_store_ids or target not in {"sku", "metrics", "staff"}:
        return
    field_name = f"{_target_prefix(target)}.store_id"
    store_id = cleaned.get(field_name)
    if store_id is not None and store_id not in valid_store_ids:
        errors.append(CleaningIssue(row_number, field_name, "store_id does not exist", store_id))


def _validate_consistency(target: str, cleaned: dict[str, Any], row_number: int, report: CleaningReport) -> None:
    if target == "metrics":
        revenue = cleaned.get("metrics.revenue")
        orders = cleaned.get("metrics.order_count")
        avg_ticket = cleaned.get("metrics.avg_ticket")
        if revenue and orders and avg_ticket:
            expected = revenue / orders
            if expected and abs(avg_ticket - expected) / expected > 0.2:
                report.warnings.append(CleaningIssue(row_number, "metrics.avg_ticket", "avg_ticket differs from revenue/order_count by more than 20%", avg_ticket))


def _make_dedupe_key(rules: dict, cleaned: dict[str, Any]) -> tuple | None:
    keys = rules.get("dedupe_key", [])
    if not keys:
        return None
    values = tuple(cleaned.get(key) for key in keys)
    if any(_is_empty(value) for value in values):
        return None
    return values


def _display_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)[:120]
