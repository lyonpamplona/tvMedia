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
from ..realtime import notify_screen, notify_sync_group, send_player_command
from ..websocket_manager import manager

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


def _screen_health_item(
    db: Session, screen: models.Screen, groups: list[models.ScreenGroup]
) -> schemas.ScreenMapItem:
    """Monta item de mapa/lista operacional."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    seconds_since: int | None = None
    online = False
    if screen.last_seen is not None:
        last_seen = screen.last_seen
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        seconds_since = int((now - last_seen).total_seconds())
        online = seconds_since <= 120
    return schemas.ScreenMapItem(
        id=screen.id,
        name=screen.name,
        slug=screen.slug,
        last_seen=screen.last_seen,
        online=online,
        connected_players=manager.connection_count(screen.slug),
        seconds_since_seen=seconds_since,
        tags=screen.tags or "",
        location_label=screen.location_label,
        latitude=screen.latitude,
        longitude=screen.longitude,
        sync_group=screen.sync_group,
        open_commands=crud.open_command_count(db, screen.id),
        group_names=crud.group_names_for_screen(db, screen, groups),
    )


@router.get("/map", response_model=list[schemas.ScreenMapItem])
def screens_map(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[schemas.ScreenMapItem]:
    """Lista operacional/mapa de telas com saúde, localização e grupos."""
    groups = crud.list_screen_groups(db, company_id=scope.company_id)
    return [
        _screen_health_item(db, screen, groups)
        for screen in crud.list_screens(db, company_id=scope.company_id)
    ]


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


@router.post("/{screen_id}/publish", response_model=schemas.ScreenRead)
async def publish_screen(
    screen_id: int,
    data: schemas.ScreenPublishRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Screen:
    """Publica agora ou agenda a publicacao futura de uma tela."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    screen = crud.publish_screen(db, screen, publish_at=data.publish_at)
    await notify_screen(screen.slug, reason="screen-published")
    if screen.sync_group:
        await notify_sync_group(db, screen.sync_group, reason="sync-group-screen-published")
    return screen


@router.post("/{screen_id}/layout-lock", response_model=schemas.ScreenRead)
async def set_layout_lock(
    screen_id: int,
    data: dict,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Screen:
    """Liga/desliga a trava de layout da tela."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    screen = crud.set_screen_layout_lock(db, screen, locked=bool(data.get("locked")))
    await notify_screen(screen.slug, reason="layout-lock-updated")
    return screen


@router.get("/{screen_id}/commands", response_model=list[schemas.PlayerCommandRead])
def list_commands(
    screen_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[models.PlayerCommand]:
    """Lista comandos recentes de uma tela."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    return crud.list_player_commands(db, screen_id=screen.id, limit=100)


@router.post("/{screen_id}/commands", response_model=schemas.PlayerCommandRead, status_code=201)
async def create_command(
    screen_id: int,
    data: schemas.PlayerCommandCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> models.PlayerCommand:
    """Enfileira e tenta enviar um comando para o player da tela."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    command = crud.create_player_command(
        db, screen, data, requested_by=actor.username
    )
    await send_player_command(screen.slug, command)
    if manager.connection_count(screen.slug) > 0:
        command = crud.mark_command_sent(db, command)
    return command


@router.post("/{screen_id}/screenshot", response_model=schemas.PlayerCommandRead, status_code=201)
async def request_screenshot(
    screen_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> models.PlayerCommand:
    """Solicita screenshot ao player conectado."""
    return await create_command(
        screen_id,
        schemas.PlayerCommandCreate(command_type="screenshot", payload={}),
        db,
        actor,
        scope,
    )


@router.get("/{screen_id}/layout/export")
def export_layout(
    screen_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> dict:
    """Exporta o layout visual de uma tela como JSON reutilizavel."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    zones = []
    for zone in sorted(screen.zones, key=lambda z: z.z_index):
        playlist_name = None
        if zone.default_playlist_id is not None:
            playlist = crud.get_playlist(db, zone.default_playlist_id)
            if playlist is not None:
                playlist_name = playlist.name
        zones.append(
            {
                "name": zone.name,
                "x": zone.x,
                "y": zone.y,
                "width": zone.width,
                "height": zone.height,
                "z_index": zone.z_index,
                "default_playlist_name": playlist_name,
            }
        )
    overlays = [
        {
            "name": overlay.name,
            "kind": overlay.kind,
            "content": overlay.content,
            "position": overlay.position,
            "width": overlay.width,
            "height": overlay.height,
            "mode": overlay.mode,
            "interval_seconds": overlay.interval_seconds,
            "visible_seconds": overlay.visible_seconds,
            "opacity": overlay.opacity,
            "z_index": overlay.z_index,
            "enabled": overlay.enabled,
        }
        for overlay in sorted(screen.overlays, key=lambda o: o.z_index)
    ]
    return {
        "version": 1,
        "name": screen.name,
        "timezone": screen.timezone,
        "sync_group": screen.sync_group,
        "resolution": screen.resolution,
        "orientation": screen.orientation,
        "size_inches": screen.size_inches,
        "theme_bg": screen.theme_bg,
        "theme_text": screen.theme_text,
        "theme_accent": screen.theme_accent,
        "theme_ticker_bg": screen.theme_ticker_bg,
        "theme_ticker_text": screen.theme_ticker_text,
        "zones": zones,
        "overlays": overlays,
    }


@router.post("/{screen_id}/layout/import", response_model=schemas.ScreenRead)
async def import_layout(
    screen_id: int,
    data: schemas.LayoutImport,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Screen:
    """Importa um layout para uma tela existente, substituindo zonas/overlays."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    if screen.layout_locked:
        raise HTTPException(status_code=423, detail="Layout travado para esta tela.")

    for field in (
        "name",
        "timezone",
        "sync_group",
        "resolution",
        "orientation",
        "size_inches",
        "theme_bg",
        "theme_text",
        "theme_accent",
        "theme_ticker_bg",
        "theme_ticker_text",
        "theme_font",
        "background_mode",
        "background_image_id",
        "background_fit",
    ):
        if field in data.model_fields_set:
            setattr(screen, field, getattr(data, field))

    for zone in list(screen.zones):
        db.delete(zone)
    for overlay in list(screen.overlays):
        db.delete(overlay)
    db.flush()

    playlists = crud.list_playlists(db, company_id=scope.company_id)
    playlist_by_name = {playlist.name: playlist.id for playlist in playlists}
    for zone_data in data.zones:
        db.add(
            models.Zone(
                screen_id=screen.id,
                name=zone_data.name,
                x=zone_data.x,
                y=zone_data.y,
                width=zone_data.width,
                height=zone_data.height,
                z_index=zone_data.z_index,
                default_playlist_id=playlist_by_name.get(
                    zone_data.default_playlist_name or ""
                ),
            )
        )
    for overlay_data in data.overlays:
        db.add(models.Overlay(screen_id=screen.id, **overlay_data.model_dump()))
    db.commit()
    screen = crud.get_screen(db, screen.id)
    await notify_screen(screen.slug, reason="layout-imported")
    await notify_sync_group(db, screen.sync_group, reason="sync-group-layout-imported")
    return screen


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
