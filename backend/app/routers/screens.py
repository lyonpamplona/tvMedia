"""Endpoints de gerenciamento de telas (TVs).

Cada tela possui um ``slug`` público usado pela URL do player e é composta por
uma ou mais zonas (criada com uma zona principal por padrão). Todas as rotas
exigem autenticação.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import require_auth
from ..database import get_db
from ..realtime import notify_screen

router = APIRouter(
    prefix="/api/screens", tags=["screens"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=list[schemas.ScreenRead])
def list_screens(db: Session = Depends(get_db)) -> list[models.Screen]:
    """Lista todas as telas cadastradas com suas zonas."""
    return crud.list_screens(db)


@router.post("", response_model=schemas.ScreenRead, status_code=201)
def create_screen(
    data: schemas.ScreenCreate, db: Session = Depends(get_db)
) -> models.Screen:
    """Cria uma nova tela com ``slug`` e uma zona principal (100%)."""
    if (
        data.default_playlist_id is not None
        and crud.get_playlist(db, data.default_playlist_id) is None
    ):
        raise HTTPException(status_code=400, detail="Playlist inexistente.")
    return crud.create_screen(db, data)


@router.get("/{screen_id}", response_model=schemas.ScreenRead)
def get_screen(screen_id: int, db: Session = Depends(get_db)) -> models.Screen:
    """Recupera uma tela pelo ID, com zonas e agendamentos."""
    screen = crud.get_screen(db, screen_id)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    return screen


@router.patch("/{screen_id}", response_model=schemas.ScreenRead)
async def update_screen(
    screen_id: int, data: schemas.ScreenUpdate, db: Session = Depends(get_db)
) -> models.Screen:
    """Atualiza nome/fuso da tela e notifica o player em tempo real."""
    screen = crud.get_screen(db, screen_id)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    screen = crud.update_screen(db, screen, data)
    await notify_screen(screen.slug, reason="screen-updated")
    return screen


@router.delete(
    "/{screen_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_screen(screen_id: int, db: Session = Depends(get_db)) -> None:
    """Remove uma tela."""
    screen = crud.get_screen(db, screen_id)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    crud.delete_screen(db, screen)
