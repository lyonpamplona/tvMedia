"""Endpoints de gestão de usuários do painel (somente administradores).

Permite listar, criar, atualizar (papel, estado, senha) e remover usuários.
Todas as rotas exigem o papel ``admin``. Ações são registradas na auditoria.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import require_admin
from ..database import get_db

router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db)) -> list[models.User]:
    """Lista todos os usuários cadastrados."""
    return crud.list_users(db)


@router.post("", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: schemas.UserCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
) -> models.User:
    """Cria um novo usuário.

    Raises:
        HTTPException: 409 se o nome de usuário já existir.
    """
    if crud.get_user_by_username(db, data.username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Nome de usuário já existe."
        )
    user = crud.create_user(db, data)
    crud.record_audit(
        db,
        actor=actor.username,
        action="create_user",
        entity_type="user",
        entity_id=user.id,
        detail=f"{user.username} ({user.role.value})",
    )
    return user


@router.patch("/{user_id}", response_model=schemas.UserRead)
def update_user(
    user_id: int,
    data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
) -> models.User:
    """Atualiza papel, estado ou senha de um usuário.

    Impede que o administrador desative a si mesmo (evita travamento).
    """
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if user.id == actor.id and data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar o próprio usuário.",
        )
    user = crud.update_user(db, user, data)
    crud.record_audit(
        db,
        actor=actor.username,
        action="update_user",
        entity_type="user",
        entity_id=user.id,
    )
    return user


@router.delete(
    "/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
) -> None:
    """Remove um usuário.

    Raises:
        HTTPException: 400 ao tentar remover a si mesmo ou o último admin.
    """
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if user.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode remover o próprio usuário.",
        )
    admins = [u for u in crud.list_users(db) if u.role == models.UserRole.admin]
    if user.role == models.UserRole.admin and len(admins) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover o último administrador.",
        )
    crud.delete_user(db, user)
    crud.record_audit(
        db,
        actor=actor.username,
        action="delete_user",
        entity_type="user",
        entity_id=user_id,
    )
