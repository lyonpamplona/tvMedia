"""Endpoints de gerenciamento de overlays (HUD) de uma tela.

Um overlay e um widget sobreposto (relogio, clima, ticker, texto) exibido por
cima das zonas, podendo ficar fixo ou aparecer/sumir em intervalos (estilo HUD
de TV). As rotas ficam sob ``/api/screens/{screen_id}/overlays`` e exigem
autenticacao. Toda alteracao notifica o player da tela em tempo real.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import notify_screen

router = APIRouter(
    prefix="/api/screens", tags=["overlays"], dependencies=[Depends(require_auth)]
)


def _get_owned_screen(db: Session, screen_id: int, scope: Scope) -> models.Screen:
    """Recupera a tela garantindo que pertence a empresa em foco."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela nao encontrada.")
    return screen


def _get_owned_overlay(
    db: Session, screen_id: int, overlay_id: int, scope: Scope
) -> models.Overlay:
    """Recupera um overlay garantindo que pertence a tela e a empresa em foco."""
    overlay = crud.get_overlay(db, overlay_id)
    if overlay is None or overlay.screen_id != screen_id:
        raise HTTPException(status_code=404, detail="Overlay nao encontrado.")
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Overlay nao encontrado.")
    return overlay


@router.get("/{screen_id}/overlays", response_model=list[schemas.OverlayRead])
async def list_overlays(
    screen_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[models.Overlay]:
    """Lista os overlays de uma tela."""
    screen = _get_owned_screen(db, screen_id, scope)
    return list(screen.overlays)


@router.post(
    "/{screen_id}/overlays", response_model=schemas.OverlayRead, status_code=201
)
async def create_overlay(
    screen_id: int,
    data: schemas.OverlayCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Overlay:
    """Cria um overlay na tela e notifica o player."""
    screen = _get_owned_screen(db, screen_id, scope)
    overlay = crud.create_overlay(db, screen, data)
    await notify_screen(screen.slug, reason="overlay-created")
    return overlay


@router.patch(
    "/{screen_id}/overlays/{overlay_id}", response_model=schemas.OverlayRead
)
async def update_overlay(
    screen_id: int,
    overlay_id: int,
    data: schemas.OverlayUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Overlay:
    """Atualiza um overlay e notifica o player."""
    overlay = _get_owned_overlay(db, screen_id, overlay_id, scope)
    overlay = crud.update_overlay(db, overlay, data)
    screen = crud.get_screen(db, screen_id)
    if screen is not None:
        await notify_screen(screen.slug, reason="overlay-updated")
    return overlay


@router.delete(
    "/{screen_id}/overlays/{overlay_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_overlay(
    screen_id: int,
    overlay_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove um overlay da tela e notifica o player."""
    overlay = _get_owned_overlay(db, screen_id, overlay_id, scope)
    screen = crud.get_screen(db, screen_id)
    crud.delete_overlay(db, overlay)
    if screen is not None:
        await notify_screen(screen.slug, reason="overlay-deleted")
