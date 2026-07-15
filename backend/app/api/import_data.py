"""Data Import API — CSV/Excel upload for stores, products, metrics."""

import csv
import io
import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.database import get_db
from app.models.models import Store, BusinessMetricsDaily, SkuPerformance, MarketingCampaign, Staff, User

router = APIRouter(prefix="/api/import", tags=["import"])

IMPORT_TYPES = {
    "stores": "stores",
    "store": "stores",
    "门店": "stores",
    "products": "products",
    "product": "products",
    "sku": "products",
    "商品": "products",
    "campaigns": "campaigns",
    "campaign": "campaigns",
    "marketing": "campaigns",
    "营销": "campaigns",
    "metrics": "metrics",
    "metric": "metrics",
    "revenue": "metrics",
    "营收": "metrics",
    "staff": "staff",
    "employee": "staff",
    "employees": "staff",
    "店员": "staff",
}


def _parse_float(v, default=0):
    try:
        return float(str(v).replace(',', '').replace('¥', '').replace('%', ''))
    except:
        return default


def _parse_int(v, default=0):
    try:
        return int(float(str(v).replace(',', '')))
    except:
        return default


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%Y%m%d']:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except:
            continue
    return None


def _clean_rows(rows):
    cleaned = []
    for row in rows:
        item = {}
        for key, value in row.items():
            if key is None:
                continue
            key = str(key).strip()
            if not key:
                continue
            item[key] = "" if value is None else value
        if any(str(value).strip() for value in item.values()):
            cleaned.append(item)
    return cleaned


def _read_rows(file: UploadFile, content: bytes):
    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        text = content.decode('utf-8-sig')
        return list(csv.DictReader(io.StringIO(text)))
    if filename.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        headers = next(rows, None)
        if not headers:
            return []
        keys = [str(header).strip() if header is not None else "" for header in headers]
        return [dict(zip(keys, row)) for row in rows]
    raise HTTPException(status_code=400, detail="Only CSV and Excel .xlsx files are supported")


@router.post("/upload")
async def import_upload(
    file: UploadFile = File(...),
    import_type: str = Form(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Upload CSV to import data. Supports: stores, products, metrics, campaigns."""
    content = await file.read()
    rows = _clean_rows(_read_rows(file, content))

    if not rows:
        raise HTTPException(status_code=400, detail="文件为空")

    normalized_type = IMPORT_TYPES.get(str(import_type).strip().lower()) or IMPORT_TYPES.get(str(import_type).strip())
    if normalized_type == "stores":
        return _import_stores(rows, db)
    if normalized_type == "products":
        return _import_products(rows, db)
    if normalized_type == "campaigns":
        return _import_campaigns(rows, db)
    if normalized_type == "metrics":
        return _import_metrics(rows, db)
    if normalized_type == "staff":
        return _import_staff(rows, db)
    if not normalized_type:
        raise HTTPException(status_code=400, detail="未知导入类型，请选择门店、商品、营销、营收或店员")

    # Detect type by filename or headers
    if 'store' in filename or '门店' in filename or 'store_name' in headers or '门店名称' in headers:
        return _import_stores(rows, db)
    elif 'sku' in filename or '商品' in filename or 'sku_name' in headers or '商品名称' in headers:
        return _import_products(rows, db)
    elif 'campaign' in filename or '活动' in filename or 'campaign_name' in headers or '活动名称' in headers:
        return _import_campaigns(rows, db)
    elif 'revenue' in filename or '营收' in filename or 'date' in headers or '日期' in headers:
        return _import_metrics(rows, db)
    else:
        raise HTTPException(status_code=400, detail="无法识别文件类型，请在文件名中包含: store/sku/campaign/revenue 或 门店/商品/活动/营收")


def _import_stores(rows, db):
    count = 0
    for r in rows:
        name = r.get('store_name') or r.get('门店名称') or r.get('name') or ''
        if not name:
            continue
        store = Store(
            name=name,
            city=r.get('city') or r.get('城市') or '',
            address=r.get('address') or r.get('地址') or '',
            area=r.get('area') or r.get('商圈') or '',
            manager_name=r.get('manager') or r.get('店长') or '',
            status=r.get('status') or 'open',
            seats=_parse_int(r.get('seats') or r.get('座位数'), 0),
            staff_count=_parse_int(r.get('staff') or r.get('员工数'), 0),
            rating=_parse_float(r.get('rating') or r.get('评分'), 4.5),
        )
        db.add(store)
        count += 1
    db.commit()
    return {"code": 0, "data": {"imported": count, "type": "stores"}, "message": f"成功导入 {count} 个门店"}


def _import_products(rows, db):
    valid_store_ids = {s.id for s in db.query(Store).all()}
    today = datetime.date.today()
    count = 0
    for r in rows:
        name = r.get('sku_name') or r.get('商品名称') or r.get('name') or ''
        if not name:
            continue
        store_id = _parse_int(r.get('store_id') or r.get('门店ID'), 1)
        if store_id not in valid_store_ids:
            store_id = list(valid_store_ids)[0] if valid_store_ids else 1
        date_str = r.get('date') or r.get('日期') or ''
        d = today
        if date_str:
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
                try:
                    d = datetime.datetime.strptime(date_str.strip(), fmt).date()
                    break
                except:
                    continue
        revenue = _parse_float(r.get('revenue') or r.get('营收') or r.get('sales_revenue'), 0)
        sales = _parse_int(r.get('sales') or r.get('销量') or r.get('sales_count'), 0)
        margin_raw = _parse_float(r.get('margin') or r.get('毛利率') or r.get('gross_margin'), 0)
        d = _parse_date(r.get('date') or r.get('日期') or r.get('鏃ユ湡')) or d
        sku = SkuPerformance(
            store_id=store_id,
            date=d,
            sku_name=name,
            category=r.get('category') or r.get('品类') or '未分类',
            sales_count=sales,
            sales_volume=_parse_int(r.get('volume') or r.get('销量'), sales),
            revenue=revenue,
            cost=_parse_float(r.get('cost') or r.get('成本'), 0),
            gross_margin=margin_raw / 100 if margin_raw > 1 else margin_raw,
            refund_rate=_parse_float(r.get('refund_rate') or r.get('退单率'), 0) / 100,
        )
        db.add(sku)
        count += 1
    db.commit()
    return {"code": 0, "data": {"imported": count, "type": "products"}, "message": f"成功导入 {count} 条商品数据"}


def _import_metrics(rows, db):
    for row in rows:
        parsed_date = _parse_date(row.get('date') or row.get('日期') or row.get('鏃ユ湡'))
        if parsed_date:
            row['date'] = parsed_date.isoformat()
    # Get valid store IDs
    valid_store_ids = {s.id for s in db.query(Store).all()}
    count = 0
    for r in rows:
        date_str = r.get('date') or r.get('日期') or ''
        if not date_str:
            continue
        # Try multiple date formats
        d = None
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%Y%m%d']:
            try:
                d = datetime.datetime.strptime(date_str.strip(), fmt).date()
                break
            except:
                continue
        if not d:
            continue
        store_id = _parse_int(r.get('store_id') or r.get('门店ID'), 1)
        if store_id not in valid_store_ids:
            store_id = list(valid_store_ids)[0] if valid_store_ids else 1
        revenue = _parse_float(r.get('revenue') or r.get('营收') or r.get('total_revenue'), 0)
        orders = _parse_int(r.get('orders') or r.get('订单数') or r.get('order_count'), 0)
        avg_ticket = _parse_float(r.get('avg_ticket') or r.get('客单价'), 0)
        if not avg_ticket and orders > 0:
            avg_ticket = revenue / orders
        metric = BusinessMetricsDaily(
            store_id=store_id,
            date=d,
            revenue=revenue,
            order_count=orders,
            avg_ticket=avg_ticket,
            gross_margin=_parse_float(r.get('margin') or r.get('毛利率') or r.get('gross_margin'), 0) / 100,
            refund_rate=_parse_float(r.get('refund_rate') or r.get('退单率'), 0) / 100,
            total_revenue=revenue,
            avg_order_value=avg_ticket,
            platform_commission=_parse_float(r.get('commission') or r.get('平台抽佣') or r.get('platform_commission'), 0),
            net_profit=_parse_float(r.get('profit') or r.get('净利润') or r.get('net_profit'), 0),
            new_customers=_parse_int(r.get('new_customers') or r.get('新客数'), 0),
            returning_customers=_parse_int(r.get('returning_customers') or r.get('回头客'), 0),
        )
        db.add(metric)
        count += 1
    db.commit()
    return {"code": 0, "data": {"imported": count, "type": "metrics"}, "message": f"成功导入 {count} 条经营数据"}


def _import_campaigns(rows, db):
    count = 0
    for r in rows:
        name = r.get('campaign_name') or r.get('活动名称') or r.get('name') or ''
        if not name:
            continue
        campaign = MarketingCampaign(
            campaign_name=name,
            channel=r.get('channel') or r.get('渠道') or '全渠道',
            status=r.get('status') or 'draft',
            budget=_parse_float(r.get('budget') or r.get('预算'), 0),
            content_text=r.get('content') or r.get('文案') or '',
        )
        db.add(campaign)
        count += 1
    db.commit()
    return {"code": 0, "data": {"imported": count, "type": "campaigns"}, "message": f"成功导入 {count} 条活动数据"}


def _import_staff(rows, db):
    valid_store_ids = {s.id for s in db.query(Store).all()}
    count = 0
    for r in rows:
        name = r.get('name') or r.get('姓名') or r.get('staff_name') or r.get('店员姓名') or ''
        if not name:
            continue
        store_id = _parse_int(r.get('store_id') or r.get('门店ID') or r.get('闂ㄥ簵ID'), 1)
        if store_id not in valid_store_ids:
            store_id = list(valid_store_ids)[0] if valid_store_ids else 1
        staff = Staff(
            store_id=store_id,
            name=name,
            phone=r.get('phone') or r.get('手机号') or r.get('手机') or '',
            role=r.get('role') or r.get('角色') or 'staff',
            email=r.get('email') or r.get('邮箱') or '',
            id_number=r.get('id_number') or r.get('身份证号') or '',
            hire_date=_parse_date(r.get('hire_date') or r.get('入职日期')),
            status=r.get('status') or r.get('状态') or 'active',
            salary=_parse_float(r.get('salary') or r.get('薪资'), 0),
            notes=r.get('notes') or r.get('备注') or '',
        )
        db.add(staff)
        count += 1
    db.commit()
    return {"code": 0, "data": {"imported": count, "type": "staff"}, "message": f"成功导入 {count} 条店员数据"}


@router.post("/manual")
def manual_entry(body: dict, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Manual single-record entry for various types."""
    entry_type = body.get('type', '')

    if entry_type == 'store':
        store = Store(
            name=body.get('name', '新门店'),
            city=body.get('city', ''),
            address=body.get('address', ''),
            area=body.get('area', ''),
            manager_name=body.get('manager_name', ''),
            seats=body.get('seats', 0),
            staff_count=body.get('staff_count', 0),
            rating=body.get('rating', 4.5),
        )
        db.add(store)
        db.commit()
        return {"code": 0, "data": {"id": store.id}, "message": "门店已添加"}

    elif entry_type == 'product':
        sku = SkuPerformance(
            store_id=body.get('store_id', 1),
            date=datetime.date.today(),
            sku_name=body.get('name', ''),
            category=body.get('category', '未分类'),
            sales_count=body.get('sales', 0),
            revenue=body.get('revenue', 0),
            cost=body.get('cost', 0),
            gross_margin=body.get('margin', 0) / 100,
        )
        db.add(sku)
        db.commit()
        return {"code": 0, "data": {"id": sku.id}, "message": "商品已添加"}

    elif entry_type == 'metric':
        metric = BusinessMetricsDaily(
            store_id=body.get('store_id', 1),
            date=datetime.date.fromisoformat(body.get('date', str(datetime.date.today()))),
            revenue=body.get('revenue', 0),
            order_count=body.get('orders', 0),
            avg_ticket=body.get('avg_ticket', 0),
            gross_margin=body.get('margin', 0) / 100,
            total_revenue=body.get('revenue', 0),
            avg_order_value=body.get('avg_ticket', 0),
            net_profit=body.get('profit', 0),
        )
        db.add(metric)
        db.commit()
        return {"code": 0, "data": {"id": metric.id}, "message": "经营数据已添加"}

    else:
        raise HTTPException(status_code=400, detail="未知类型，支持: store, product, metric")
