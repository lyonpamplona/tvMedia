"""Endpoints de pastas de mídia (organização da biblioteca).

Pastas não afetam o que é exibido nas telas; servem apenas para organizar a
biblioteca de mídias. Todas as rotas exigem autenticação.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db

router = APIRouter(
    prefix="/api/folders", tags=["folders"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=list[schemas.FolderRead])
def list_folders(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[models.MediaFolder]:
    """Lista as pastas de mídia da empresa em foco."""
    return crud.list_folders(db, company_id=scope.company_id)


@router.post("", response_model=schemas.FolderRead, status_code=status.HTTP_201_CREATED)
def create_folder(
    data: schemas.FolderCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.MediaFolder:
    """Cria uma nova pasta de mídia na empresa em foco."""
    if data.parent_id is not None:
        parent = crud.get_folder(db, data.parent_id)
        if parent is None or not scope_can_access(scope, parent.company_id):
            raise HTTPException(status_code=400, detail="Pasta pai inexistente.")
    return crud.create_folder(db, data, company_id=scope.write_company_id)


@router.patch("/{folder_id}", response_model=schemas.FolderRead)
def update_folder(
    folder_id: int,
    data: schemas.FolderUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.MediaFolder:
    """Atualiza nome ou pasta-pai de uma pasta."""
    folder = crud.get_folder(db, folder_id)
    if folder is None or not scope_can_access(scope, folder.company_id):
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if data.parent_id == folder_id:
        raise HTTPException(status_code=400, detail="Uma pasta não pode ser pai de si mesma.")
    return crud.update_folder(db, folder, data)


@router.delete(
    "/{folder_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove uma pasta (as mídias dentro dela ficam sem pasta)."""
    folder = crud.get_folder(db, folder_id)
    if folder is None or not scope_can_access(scope, folder.company_id):
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    crud.delete_folder(db, folder)
