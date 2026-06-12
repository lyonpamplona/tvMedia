"""Endpoints públicos consumidos pelo player na TV.

Inclui:

* ``GET /api/display/{slug}`` — monta o payload de exibição resolvendo, para
  cada zona, a playlist ativa no momento (considerando agendamentos e fuso da
  tela). Também registra um "heartbeat" (``last_seen``).
* ``WS /ws/display/{slug}`` — canal de tempo real; o servidor envia
  ``{"type": "reload"}`` quando o conteúdo da tela muda.

Estes endpoints são públicos (sem autenticação): a TV só conhece o ``slug``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import SessionLocal, get_db
from ..embeds import build_embed_url
from ..websocket_manager import manager

router = APIRouter(tags=["display"])


def _media_url(request: Request, media: models.Media) -> str | None:
    """Resolve a URL pública de uma mídia conforme o tipo.

    Args:
        request: requisição atual (para montar URL absoluta de arquivos).
        media: mídia a resolver.

    Returns:
        str | None: URL absoluta do arquivo/origem, ou None para texto/HTML.
    """
    if media.type in (models.MediaType.image, models.MediaType.video) and media.path:
        return str(request.base_url) + f"media/{media.path}"
    if media.type == models.MediaType.url:
        return media.source_url
    return None


def _now_in_timezone(tz_name: str) -> datetime:
    """Retorna o instante atual no fuso informado (com fallback para UTC)."""
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = timezone.utc
    return datetime.now(tz)


def _build_zone_payload(
    request: Request, db: Session, zone: models.Zone, now: datetime
) -> schemas.DisplayZone:
    """Monta o payload de uma zona resolvendo a playlist ativa no momento."""
    playlist_id = crud.resolve_active_playlist_id(zone, now)
    playlist = crud.get_playlist(db, playlist_id) if playlist_id else None

    items: list[schemas.DisplayItem] = []
    if playlist is not None:
        for item in sorted(playlist.items, key=lambda i: i.position):
            if item.media.type in (models.MediaType.youtube, models.MediaType.embed):
                media_url = build_embed_url(item.media, muted=item.muted)
            else:
                media_url = _media_url(request, item.media)
            items.append(
                schemas.DisplayItem(
                    type=item.media.type,
                    duration=item.duration,
                    name=item.media.name,
                    fit=item.fit,
                    transition=item.transition,
                    muted=item.muted,
                    url=media_url,
                    content=item.media.content,
                )
            )

    return schemas.DisplayZone(
        id=zone.id,
        name=zone.name,
        x=zone.x,
        y=zone.y,
        width=zone.width,
        height=zone.height,
        z_index=zone.z_index,
        playlist_name=playlist.name if playlist else None,
        items=items,
    )


def _compute_revision(payload: schemas.DisplayPayload) -> str:
    """Calcula um hash curto e estável do conteúdo (detecta mudanças).

    O player compara a ``revision`` entre buscas para decidir se reinicia a
    reprodução. Excluindo o próprio campo ``revision`` do cálculo.
    """
    snapshot = payload.model_dump(exclude={"revision"})
    raw = repr(snapshot).encode()
    return hashlib.sha256(raw).hexdigest()[:12]


@router.get("/api/display/{slug}", response_model=schemas.DisplayPayload)
def get_display(
    slug: str, request: Request, db: Session = Depends(get_db)
) -> schemas.DisplayPayload:
    """Retorna o conteúdo resolvido de uma tela para o player.

    Resolve cada zona para a playlist ativa no momento (agendamento + fuso),
    registra o heartbeat da tela e calcula a ``revision`` do conteúdo.

    Raises:
        HTTPException: 404 quando o ``slug`` não corresponde a uma tela.
    """
    screen = crud.get_screen_by_slug(db, slug)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada.")

    # Heartbeat: marca a tela como online.
    screen.last_seen = datetime.now(timezone.utc)
    db.commit()

    now = _now_in_timezone(screen.timezone)
    zones = [
        _build_zone_payload(request, db, zone, now)
        for zone in sorted(screen.zones, key=lambda z: z.z_index)
    ]

    payload = schemas.DisplayPayload(screen=screen.slug, revision="", zones=zones)
    payload.revision = _compute_revision(payload)
    return payload


@router.websocket("/ws/display/{slug}")
async def display_socket(websocket: WebSocket, slug: str) -> None:
    """Canal WebSocket que avisa o player quando a tela deve recarregar.

    Valida o ``slug`` antes de aceitar, registra a conexão no gerenciador e
    mantém um loop de ping/pong. Mensagens de difusão (``reload``) são enviadas
    pelos helpers em :mod:`app.realtime` quando o conteúdo muda.
    """
    # Valida o slug usando uma sessão própria (fora do ciclo de dependências).
    with SessionLocal() as db:
        screen = crud.get_screen_by_slug(db, slug)
        if screen is None:
            await websocket.close(code=4404)
            return

    await manager.connect(slug, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            # Responde ao keep-alive do cliente.
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(slug, websocket)
