"""User API — avatar upload, profile management."""

import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/user", tags=["user"])

# Resolve absolute path for uploads directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
UPLOADS_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _save_avatar(file: UploadFile) -> str:
    """Save uploaded avatar file and return the relative URL path."""
    ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}")

    # Generate unique filename
    filename = f"avatar_{uuid.uuid4().hex}{ext}"
    filepath = UPLOADS_DIR / filename

    # Stream to disk
    with open(filepath, "wb") as buffer:
        # Read in chunks to handle large files
        file.file.seek(0)
        total = 0
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


@router.post("/upload-avatar")
def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload or replace the current user's avatar."""
    # Delete old avatar file if it exists and is local
    if user.avatar_url and user.avatar_url.startswith("/uploads/"):
        old_path = BASE_DIR / user.avatar_url.lstrip("/")
        if old_path.exists():
            old_path.unlink()

    url = _save_avatar(file)
    user.avatar_url = url
    db.commit()
    db.refresh(user)

    return {
        "code": 0,
        "data": {
            "avatar_url": url,
            "username": user.username,
            "email": user.email,
        },
        "message": "头像上传成功",
    }


@router.get("/profile")
def get_profile(
    user: User = Depends(get_current_user),
):
    """Get current user profile."""
    return {
        "code": 0,
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url or "",
            "created_at": str(user.created_at) if user.created_at else None,
        },
        "message": "ok",
    }


@router.put("/profile")
def update_profile(
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile fields (username, email)."""
    if "username" in body:
        new_name = body["username"].strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="用户名不能为空")
        user.username = new_name

    if "email" in body:
        new_email = body["email"].strip().lower()
        existing = db.query(User).filter(User.email == new_email, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="该邮箱已被使用")
        user.email = new_email

    db.commit()
    db.refresh(user)

    return {
        "code": 0,
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url or "",
        },
        "message": "个人信息已更新",
    }
