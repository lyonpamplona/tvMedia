"""Endpoints de gerenciamento de telas (TVs).

Cada tela possui um ``slug`` público usado pela URL do player e é composta por
uma ou mais zonas (criada com uma zona principal por padrão). Inclui ainda um
endpoint de pré-visualização que devolve exatamente o que o player exibiria
agora. Todas as rotas exigem autenticação.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas, services
from ..auth import Scope, get_current_user, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import notify_screen, notify_sync_group

router = APIRouter(
    prefix="/api/screens", tags=["screens"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=list[schemas.ScreenRead])
def list_screens(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[models.Screen]:
    """Lista as telas da empresa em foco com suas zonas."""
    return crud.list_screens(db, company_id=scope.company_id)


@router.post("", response_model=schemas.ScreenRead, status_code=201)
def create_screen(
    data: schemas.ScreenCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> models.Screen:
    """Cria uma nova tela (com template opcional) na empresa em foco."""
    if data.default_playlist_id is not None:
        ref_playlist = crud.get_playlist(db, data.default_playlist_id)
        if ref_playlist is None or not scope_can_access(scope, ref_playlist.company_id):
            raise HTTPException(status_code=400, detail="Playlist inexistente.")
    screen = crud.create_screen(db, data, company_id=scope.write_company_id)
    crud.record_audit(
        db,
        actor=actor.username,
        action="create_screen",
        entity_type="screen",
        entity_id=screen.id,
        detail=screen.name,
    )
    return screen


@router.get("/{screen_id}", response_model=schemas.ScreenRead)
def get_screen(
    screen_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Screen:
    """Recupera uma tela pelo ID, com zonas e agendamentos."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    return screen


@router.get("/{screen_id}/preview", response_model=schemas.DisplayPayload)
def preview_screen(
    screen_id: int,
    request: Request,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.DisplayPayload:
    """Pré-visualiza o conteúdo atual da tela (mesma resolução do player).

    Útil para o painel mostrar exatamente o que está no ar agora, sem precisar
    abrir a URL pública do player. Não registra heartbeat.
    """
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    return services.build_display_payload(str(request.base_url), db, screen)


@router.patch("/{screen_id}", response_model=schemas.ScreenRead)
async def update_screen(
    screen_id: int,
    data: schemas.ScreenUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Screen:
    """Atualiza nome/fuso da tela e notifica o player em tempo real."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    screen = crud.update_screen(db, screen, data)
    await notify_screen(screen.slug, reason="screen-updated")
    await notify_sync_group(db, screen.sync_group, reason="sync-group-updated")
    return screen


@router.delete(
    "/{screen_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_screen(
    screen_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove uma tela e suas zonas/agendamentos."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    slug = screen.slug
    name = screen.name
    crud.delete_screen(db, screen)
    await notify_screen(slug, reason="screen-deleted")
    crud.record_audit(
        db,
        actor=actor.username,
        action="delete_screen",
        entity_type="screen",
        entity_id=screen_id,
        detail=name,
    )
