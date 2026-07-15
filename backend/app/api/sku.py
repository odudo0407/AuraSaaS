"""SKU CRUD API — create, read, update, delete products with optional image."""

import uuid
import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Body
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import SkuPerformance, Store
from app.core.deps import get_current_user
from app.models.models import User

router = APIRouter(prefix="/api/sku", tags=["sku"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
UPLOADS_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _save_sku_image(file: UploadFile) -> str:
    """Save SKU image and return relative URL."""
    ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}")

    filename = f"sku_{uuid.uuid4().hex}{ext}"
    filepath = UPLOADS_DIR / filename

    file.file.seek(0)
    total = 0
    with open(filepath, "wb") as buffer:
        while True:
            chunk = file.file.read(8192)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                filepath.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="文件大小不能超过 5MB")
            buffer.write(chunk)

    return f"/uploads/{filename}"


@router.post("/add")
def add_sku(
    store_id: int = Form(...),
    sku_name: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    cost: float = Form(default=0),
    sales_count: int = Form(default=0),
    revenue: float = Form(default=0),
    date: str = Form(default=None),
    image: UploadFile = File(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Add a new SKU with optional image upload."""
    # Validate store exists
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=400, detail="门店不存在")

    # Parse date
    d = datetime.date.today()
    if date:
        for fmt in ['%Y-%m-%d', '%Y/%m/%d']:
            try:
                d = datetime.datetime.strptime(date.strip(), fmt).date()
                break
            except ValueError:
                continue

    # Calculate gross margin
    gross_margin = 0
    if price > 0:
        gross_margin = round((price - cost) / price, 4)

    # Save image
    image_url = ""
    if image and image.filename:
        image_url = _save_sku_image(image)

    sku = SkuPerformance(
        store_id=store_id,
        date=d,
        sku_name=sku_name.strip(),
        category=category.strip(),
        image_url=image_url,
        price=price,
        cost=cost,
        sales_count=sales_count,
        sales_volume=sales_count,
        revenue=revenue if revenue else price * sales_count,
        gross_margin=gross_margin,
    )
    db.add(sku)
    db.commit()
    db.refresh(sku)

    return {
        "code": 0,
        "data": {
            "id": sku.id,
            "store_id": sku.store_id,
            "sku_name": sku.sku_name,
            "category": sku.category,
            "image_url": sku.image_url,
            "price": sku.price,
            "cost": sku.cost,
            "sales_count": sku.sales_count,
            "revenue": sku.revenue,
            "gross_margin": round(sku.gross_margin * 100, 2),
        },
        "message": "商品添加成功",
    }


@router.delete("/delete/{sku_id}")
def delete_sku(
    sku_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete a SKU by ID. Also removes its image file if local."""
    sku = db.query(SkuPerformance).filter(SkuPerformance.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="商品不存在")

    # Delete associated image file
    if sku.image_url and sku.image_url.startswith("/uploads/"):
        img_path = BASE_DIR / sku.image_url.lstrip("/")
        if img_path.exists():
            img_path.unlink()

    db.delete(sku)
    db.commit()

    return {
        "code": 0,
        "data": {"id": sku_id},
        "message": "商品已删除",
    }


@router.post("/batch-delete")
def batch_delete_skus(
    ids: list[int] = Body(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete multiple SKU records by ID."""
    unique_ids = sorted({int(item) for item in ids if item})
    if not unique_ids:
        return {"code": -1, "data": {"deleted": 0}, "message": "No SKU ids provided"}

    rows = db.query(SkuPerformance).filter(SkuPerformance.id.in_(unique_ids)).all()
    for sku in rows:
        if sku.image_url and sku.image_url.startswith("/uploads/"):
            img_path = BASE_DIR / sku.image_url.lstrip("/")
            if img_path.exists():
                img_path.unlink()
        db.delete(sku)
    db.commit()
    return {"code": 0, "data": {"deleted": len(rows), "ids": unique_ids}, "message": f"Deleted {len(rows)} SKU records"}


@router.put("/update/{sku_id}")
def update_sku(
    sku_id: int,
    store_id: int = Form(default=None),
    sku_name: str = Form(default=None),
    category: str = Form(default=None),
    price: float = Form(default=None),
    cost: float = Form(default=None),
    sales_count: int = Form(default=None),
    revenue: float = Form(default=None),
    date: str = Form(default=None),
    image: UploadFile = File(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update a SKU with optional image overwrite."""
    sku = db.query(SkuPerformance).filter(SkuPerformance.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="商品不存在")

    # Update text fields
    if sku_name is not None:
        sku.sku_name = sku_name.strip()
    if category is not None:
        sku.category = category.strip()
    if price is not None:
        sku.price = price
    if cost is not None:
        sku.cost = cost
    if sales_count is not None:
        sku.sales_count = sales_count
        sku.sales_volume = sales_count
    if revenue is not None:
        sku.revenue = revenue
    if store_id is not None:
        store = db.query(Store).filter(Store.id == store_id).first()
        if not store:
            raise HTTPException(status_code=400, detail="门店不存在")
        sku.store_id = store_id

    # Parse date
    if date is not None:
        for fmt in ['%Y-%m-%d', '%Y/%m/%d']:
            try:
                sku.date = datetime.datetime.strptime(date.strip(), fmt).date()
                break
            except ValueError:
                continue

    # Recalculate gross margin
    if sku.price > 0:
        sku.gross_margin = round((sku.price - (sku.cost or 0)) / sku.price, 4)

    # Recalculate revenue if not explicitly set
    if revenue is None and price is not None:
        sku.revenue = sku.price * (sku.sales_count or 0)

    # Handle image upload (overwrite)
    if image and image.filename:
        # Delete old image
        if sku.image_url and sku.image_url.startswith("/uploads/"):
            old_path = BASE_DIR / sku.image_url.lstrip("/")
            if old_path.exists():
                old_path.unlink()
        sku.image_url = _save_sku_image(image)

    db.commit()
    db.refresh(sku)

    return {
        "code": 0,
        "data": {
            "id": sku.id,
            "store_id": sku.store_id,
            "sku_name": sku.sku_name,
            "category": sku.category,
            "image_url": sku.image_url,
            "price": sku.price,
            "cost": sku.cost,
            "sales_count": sku.sales_count,
            "revenue": sku.revenue,
            "gross_margin": round(sku.gross_margin * 100, 2),
            "date": str(sku.date),
        },
        "message": "商品已更新",
    }


@router.get("/list")
def list_skus(
    store_id: int = Query(None),
    category: str = Query(None),
    search: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List SKUs with optional filters. No auth required for viewing."""
    q = db.query(SkuPerformance)

    if store_id:
        q = q.filter(SkuPerformance.store_id == store_id)
    category_q = q
    if search:
        q = q.filter(SkuPerformance.sku_name.contains(search))

    category_rows = (
        category_q.with_entities(SkuPerformance.category, func.count(SkuPerformance.id))
        .filter(SkuPerformance.category != None)
        .group_by(SkuPerformance.category)
        .all()
    )
    all_total = category_q.count()

    if category:
        q = q.filter(SkuPerformance.category == category)

    total = q.count()
    rows = q.order_by(SkuPerformance.id.desc()).offset(offset).limit(limit).all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "all_total": all_total,
            "category_counts": [
                {"category": category, "count": count}
                for category, count in category_rows
                if category
            ],
            "items": [
                {
                    "id": r.id,
                    "store_id": r.store_id,
                    "sku_name": r.sku_name,
                    "category": r.category,
                    "image_url": r.image_url,
                    "price": r.price,
                    "cost": r.cost,
                    "sales_count": r.sales_count,
                    "revenue": r.revenue,
                    "gross_margin": round(r.gross_margin * 100, 2),
                    "refund_rate": round((r.refund_rate or 0) * 100, 2),
                    "date": str(r.date),
                }
                for r in rows
            ],
        },
        "message": "ok",
    }


@router.get("/{sku_id}")
def get_sku(
    sku_id: int,
    db: Session = Depends(get_db),
):
    """Get a single SKU by ID."""
    sku = db.query(SkuPerformance).filter(SkuPerformance.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="商品不存在")

    return {
        "code": 0,
        "data": {
            "id": sku.id,
            "store_id": sku.store_id,
            "sku_name": sku.sku_name,
            "category": sku.category,
            "image_url": sku.image_url,
            "price": sku.price,
            "cost": sku.cost,
            "sales_count": sku.sales_count,
            "revenue": sku.revenue,
            "gross_margin": round(sku.gross_margin * 100, 2),
            "refund_rate": round((sku.refund_rate or 0) * 100, 2),
            "stockout_count": sku.stockout_count or 0,
            "cost_warning": bool(sku.cost_warning),
            "date": str(sku.date),
        },
        "message": "ok",
    }
