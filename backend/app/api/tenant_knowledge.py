"""Tenant private knowledge management API."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.response import UTF8JSONResponse
from app.database import get_db
from app.models.models import TenantKnowledgeDocument
from app.services.tenant_knowledge_service import (
    SUPPORTED_EXTENSIONS,
    delete_tenant_knowledge_document,
    ingest_tenant_knowledge_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tenant/knowledge",
    tags=["tenant-knowledge"],
    default_response_class=UTF8JSONResponse,
)


def _document_payload(doc: TenantKnowledgeDocument) -> dict:
    return {
        "id": doc.id,
        "tenant_id": doc.tenant_id,
        "file_name": doc.file_name,
        "file_size": doc.file_size,
        "file_type": doc.file_type,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "error_message": doc.error_message,
        "uploaded_at": str(doc.uploaded_at) if doc.uploaded_at else None,
        "created_by": doc.created_by,
    }


@router.post("/upload")
async def upload_tenant_knowledge(
    file: UploadFile = File(...),
    tenant_id: int = Form(...),
    created_by: str = Form(""),
    db: Session = Depends(get_db),
):
    """Upload one tenant-scoped private knowledge document."""

    if tenant_id <= 0:
        raise HTTPException(status_code=400, detail="tenant_id must be positive")
    file_name = Path(file.filename or "").name
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    file_bytes = await file.read()
    try:
        doc = ingest_tenant_knowledge_file(
            db,
            tenant_id=tenant_id,
            file_name=file_name,
            file_bytes=file_bytes,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Tenant knowledge upload failed tenant_id=%s file=%s", tenant_id, file_name)
        raise HTTPException(status_code=500, detail="Tenant knowledge upload failed") from exc

    return {"code": 0, "message": "ok", "data": _document_payload(doc)}


@router.get("/list")
def list_tenant_knowledge(
    tenant_id: int = Query(..., gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List tenant private knowledge documents with pagination."""

    query = db.query(TenantKnowledgeDocument).filter(TenantKnowledgeDocument.tenant_id == tenant_id)
    total = query.count()
    docs = (
        query.order_by(TenantKnowledgeDocument.uploaded_at.desc(), TenantKnowledgeDocument.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "tenant_id": tenant_id,
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": [_document_payload(doc) for doc in docs],
        },
    }


@router.delete("/{doc_id}")
def delete_tenant_knowledge(
    doc_id: int,
    tenant_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    """Delete one tenant document and its isolated vector chunks."""

    doc = delete_tenant_knowledge_document(db, doc_id=doc_id, tenant_id=tenant_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tenant knowledge document not found")
    return {
        "code": 0,
        "message": "Tenant knowledge document deleted",
        "data": {"id": doc_id, "tenant_id": tenant_id, "file_name": doc.file_name},
    }