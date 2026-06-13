"""Endpoints de gerenciamento de zonas de uma tela.

Uma zona é uma região retangular (em % da tela) com playlist padrão e
agendamentos próprios. As rotas ficam sob ``/api/screens/{screen_id}/zones`` e
exigem autenticação. Toda alteração notifica o player da tela em tempo real.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import notify_screen

router = APIRouter(
    prefix="/api/screens", tags=["zones"], dependencies=[Depends(require_auth)]
)


def _get_owned_zone(
    db: Session, screen_id: int, zone_id: int, scope: Scope
) -> models.Zone:
    """Recupera uma zona garantindo que pertence à tela e à empresa em foco.

    Raises:
        HTTPException: 404 se a zona não existir, não for da tela ou for de
            outra empresa.
    """
    zone = crud.get_zone(db, zone_id)
    if zone is None or zone.screen_id != screen_id:
        raise HTTPException(status_code=404, detail="Zona não encontrada.")
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Zona não encontrada.")
    return zone


def _validate_playlist(
    db: Session, playlist_id: int | None, scope: Scope
) -> None:
    """Valida que a playlist informada existe na empresa em foco."""
    if playlist_id is not None:
        playlist = crud.get_playlist(db, playlist_id)
        if playlist is None or not scope_can_access(scope, playlist.company_id):
            raise HTTPException(status_code=400, detail="Playlist inexistente.")


@router.post(
    "/{screen_id}/zones", response_model=schemas.ZoneRead, status_code=201
)
async def create_zone(
    screen_id: int,
    data: schemas.ZoneCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Zone:
    """Cria uma nova zona na tela e notifica o player."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    _validate_playlist(db, data.default_playlist_id, scope)
    zone = crud.create_zone(db, screen, data)
    await notify_screen(screen.slug, reason="zone-created")
    return zone


@router.patch("/{screen_id}/zones/{zone_id}", response_model=schemas.ZoneRead)
async def update_zone(
    screen_id: int,
    zone_id: int,
    data: schemas.ZoneUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Zone:
    """Atualiza geometria, nome ou playlist padrão de uma zona."""
    zone = _get_owned_zone(db, screen_id, zone_id, scope)
    _validate_playlist(db, data.default_playlist_id, scope)
    zone = crud.update_zone(db, zone, data)
    screen = crud.get_screen(db, screen_id)
    if screen is not None:
        await notify_screen(screen.slug, reason="zone-updated")
    return zone


@router.delete(
    "/{screen_id}/zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_zone(
    screen_id: int,
    zone_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove uma zona da tela e notifica o player."""
    zone = _get_owned_zone(db, screen_id, zone_id, scope)
    screen = crud.get_screen(db, screen_id)
    crud.delete_zone(db, zone)
    if screen is not None:
        await notify_screen(screen.slug, reason="zone-deleted")
