"""Quick test: seed mock data and query it."""
import sys
sys.path.insert(0, ".")

from scripts.generate_mock_data import init_mock_data
init_mock_data()

from app.database import SessionLocal
from app.models.models import BusinessMetricsDaily, SkuPerformance
from sqlalchemy import func

db = SessionLocal()
metrics_count = db.query(func.count(BusinessMetricsDaily.id)).scalar()
sku_count = db.query(func.count(SkuPerformance.id)).scalar()
print(f"Metrics rows: {metrics_count}")
print(f"SKU rows: {sku_count}")

# Test a query similar to the dashboard API
import datetime
today = datetime.date.today()
month_start = today.replace(day=1)
month_rev = db.query(func.sum(BusinessMetricsDaily.total_revenue)).filter(
    BusinessMetricsDaily.date >= month_start
).scalar()
print(f"This month revenue: {month_rev:.0f}" if month_rev else "No data yet")
db.close()
