import datetime
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

from app.services.data_cleaning import clean_rows, normalize_value  # noqa: E402


def test_normalize_value_handles_money_percent_and_dates():
    assert normalize_value("¥1,234.50", "money")[0] == 1234.5
    assert normalize_value("5%", "percent")[0] == 0.05
    assert normalize_value("0.08", "percent")[0] == 0.08
    assert normalize_value("2026/06/15", "date")[0] == datetime.date(2026, 6, 15)


def test_clean_rows_normalizes_metrics_and_filters_empty_rows():
    result = clean_rows(
        "metrics",
        {},
        ["date", "store_id", "revenue", "order_count", "refund_rate"],
        [
            ["2026/06/15", "1", "¥1,200", "40", "5%"],
            ["", "", "", "", ""],
        ],
        valid_store_ids={1},
        today=datetime.date(2026, 6, 16),
    )

    report = result["report"]
    rows = result["cleaned_rows"]
    assert report["total_rows"] == 2
    assert report["valid_rows"] == 1
    assert report["skipped_rows"] == 1
    assert report["fixed_cells"] >= 4
    assert rows[0]["metrics.date"] == datetime.date(2026, 6, 15)
    assert rows[0]["metrics.revenue"] == 1200
    assert rows[0]["metrics.refund_rate"] == 0.05
    assert rows[0]["metrics.avg_ticket"] == 30


def test_clean_rows_rejects_duplicates_and_invalid_store_ids():
    result = clean_rows(
        "metrics",
        {},
        ["date", "store_id", "revenue"],
        [
            ["2026-06-15", "1", "100"],
            ["2026-06-15", "1", "200"],
            ["2026-06-16", "9", "300"],
        ],
        valid_store_ids={1},
    )

    report = result["report"]
    assert report["valid_rows"] == 1
    assert report["skipped_rows"] == 2
    assert report["duplicate_rows"] == 1
    messages = [error["message"] for error in report["errors"]]
    assert "duplicate row" in messages
    assert "store_id does not exist" in messages


def test_clean_rows_rejects_out_of_range_values():
    result = clean_rows(
        "metrics",
        {},
        ["date", "store_id", "revenue", "refund_rate"],
        [["2026-06-15", "1", "-10", "130%"]],
        valid_store_ids={1},
    )

    report = result["report"]
    assert report["valid_rows"] == 0
    assert report["skipped_rows"] == 1
    fields = [error["field"] for error in report["errors"]]
    assert "metrics.revenue" in fields
    assert "metrics.refund_rate" in fields


def test_clean_rows_derives_sku_revenue_and_margin():
    result = clean_rows(
        "sku",
        {},
        ["sku_name", "store_id", "price", "cost", "sales_count"],
        [["Classic Latte", "1", "30", "9", "10"]],
        valid_store_ids={1},
        today=datetime.date(2026, 6, 16),
    )

    report = result["report"]
    row = result["cleaned_rows"][0]
    assert report["valid_rows"] == 1
    assert row["sku.date"] == datetime.date(2026, 6, 16)
    assert row["sku.revenue"] == 300
    assert row["sku.gross_margin"] == 0.7
