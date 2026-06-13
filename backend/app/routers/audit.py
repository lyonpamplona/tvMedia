"""Endpoint de consulta à trilha de auditoria (somente administradores)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import require_admin
from ..database import get_db

router = APIRouter(
    prefix="/api/audit", tags=["audit"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=schemas.Page[schemas.AuditLogRead])
def list_audit(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> schemas.Page[schemas.AuditLogRead]:
    """Lista registros de auditoria (mais recentes primeiro), paginados."""
    rows, total = crud.list_audit(db, limit=limit, offset=offset)
    items = [schemas.AuditLogRead.model_validate(row) for row in rows]
    return schemas.Page[schemas.AuditLogRead](
        total=total, limit=limit, offset=offset, items=items
    )
