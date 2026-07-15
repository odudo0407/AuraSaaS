"""Staff management API - CRUD for store employees."""

import datetime

from fastapi import APIRouter, Depends, Body, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.response import api_response
from app.database import get_db
from app.models.models import Staff, Store, User

router = APIRouter(prefix="/api/staff", tags=["staff"])


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))


def _ensure_store(db: Session, store_id: int):
    if not db.query(Store).filter(Store.id == store_id).first():
        raise HTTPException(status_code=400, detail="门店不存在")


def _staff_payload(row: Staff) -> dict:
    return {
        "id": row.id,
        "store_id": row.store_id,
        "name": row.name,
        "phone": row.phone,
        "role": row.role,
        "email": row.email,
        "id_number": row.id_number,
        "hire_date": str(row.hire_date) if row.hire_date else None,
        "status": row.status,
        "salary": row.salary,
        "notes": row.notes,
        "created_at": str(row.created_at),
    }


@router.get("")
def list_staff(
    store_id: int = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    """List staff, optionally filtered by store and status."""
    q = db.query(Staff)
    if store_id:
        q = q.filter(Staff.store_id == store_id)
    if status:
        q = q.filter(Staff.status == status)
    rows = q.order_by(Staff.store_id, Staff.name).all()
    return api_response(data=[_staff_payload(row) for row in rows])


@router.post("")
def create_staff(
    body: dict,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Add a new staff member."""
    store_id = int(body.get("store_id", 0))
    _ensure_store(db, store_id)
    staff = Staff(
        store_id=store_id,
        name=body["name"],
        phone=body.get("phone", ""),
        role=body.get("role", "staff"),
        email=body.get("email", ""),
        id_number=body.get("id_number", ""),
        hire_date=_parse_date(body.get("hire_date")),
        status=body.get("status", "active"),
        salary=body.get("salary", 0),
        notes=body.get("notes", ""),
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return api_response(data={"id": staff.id, "name": staff.name}, message="员工已添加")


@router.put("/{staff_id}")
def update_staff(
    staff_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update staff info."""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        return api_response(code=-1, message="员工不存在")
    if "store_id" in body:
        _ensure_store(db, int(body["store_id"]))
    for field in ["name", "phone", "role", "email", "id_number", "hire_date", "status", "salary", "notes", "store_id"]:
        if field in body:
            value = _parse_date(body[field]) if field == "hire_date" else body[field]
            setattr(staff, field, value)
    db.commit()
    return api_response(data={"id": staff.id, "name": staff.name}, message="员工信息已更新")


@router.post("/batch-delete")
def batch_delete_staff(
    ids: list[int] = Body(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete multiple staff members."""
    unique_ids = sorted({int(item) for item in ids if item})
    if not unique_ids:
        return api_response(code=-1, data={"deleted": 0}, message="No staff ids provided")

    rows = db.query(Staff).filter(Staff.id.in_(unique_ids)).all()
    for staff in rows:
        db.delete(staff)
    db.commit()
    return api_response(data={"deleted": len(rows), "ids": unique_ids}, message=f"Deleted {len(rows)} staff records")


@router.delete("/{staff_id}")
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Remove a staff member."""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        return api_response(code=-1, message="员工不存在")
    db.delete(staff)
    db.commit()
    return api_response(message="员工已删除")
