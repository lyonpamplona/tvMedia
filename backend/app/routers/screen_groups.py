"""Endpoints de grupos de telas (P4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db

router = APIRouter(
    prefix="/api/screen-groups",
    tags=["screen-groups"],
    dependencies=[Depends(require_auth)],
)


def _read_group(db: Session, group: models.ScreenGroup) -> schemas.ScreenGroupRead:
    """Serializa um grupo com a contagem resolvida."""
    item = schemas.ScreenGroupRead.model_validate(group)
    return item.model_copy(update={"screen_count": crud.screen_group_count(db, group)})


def _validate_screen_ids(db: Session, ids: list[int], scope: Scope) -> None:
    """Garante que todos os IDs informados pertencem ao escopo."""
    for screen_id in ids:
        screen = crud.get_screen(db, screen_id)
        if screen is None or not scope_can_access(scope, screen.company_id):
            raise HTTPException(status_code=400, detail="Tela inexistente no escopo.")


@router.get("", response_model=list[schemas.ScreenGroupRead])
def list_groups(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[schemas.ScreenGroupRead]:
    """Lista grupos de telas."""
    return [
        _read_group(db, group)
        for group in crud.list_screen_groups(db, company_id=scope.company_id)
    ]


@router.post("", response_model=schemas.ScreenGroupRead, status_code=201)
def create_group(
    data: schemas.ScreenGroupCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.ScreenGroupRead:
    """Cria grupo estático ou dinâmico por tags."""
    if data.screen_ids:
        _validate_screen_ids(db, data.screen_ids, scope)
    group = crud.create_screen_group(db, data, company_id=scope.write_company_id)
    return _read_group(db, group)


@router.get("/{group_id}", response_model=schemas.ScreenGroupRead)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.ScreenGroupRead:
    """Detalha um grupo."""
    group = crud.get_screen_group(db, group_id)
    if group is None or not scope_can_access(scope, group.company_id):
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    return _read_group(db, group)


@router.get("/{group_id}/screens", response_model=list[schemas.ScreenRead])
def group_screens(
    group_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[models.Screen]:
    """Resolve as telas atuais de um grupo."""
    group = crud.get_screen_group(db, group_id)
    if group is None or not scope_can_access(scope, group.company_id):
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    return crud.resolve_group_screens(db, group)


@router.patch("/{group_id}", response_model=schemas.ScreenGroupRead)
def update_group(
    group_id: int,
    data: schemas.ScreenGroupUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.ScreenGroupRead:
    """Atualiza um grupo."""
    group = crud.get_screen_group(db, group_id)
    if group is None or not scope_can_access(scope, group.company_id):
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    if data.screen_ids:
        _validate_screen_ids(db, data.screen_ids, scope)
    group = crud.update_screen_group(db, group, data)
    return _read_group(db, group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove um grupo."""
    group = crud.get_screen_group(db, group_id)
    if group is None or not scope_can_access(scope, group.company_id):
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    crud.delete_screen_group(db, group)
