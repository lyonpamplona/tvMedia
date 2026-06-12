"""Endpoints consumidos diretamente pelo player nas TVs.

Inclui:

* ``GET /api/display/{slug}`` — retorna o conteúdo resolvido da tela (a
  playlist vinculada, com URLs absolutas e durações), pronto para reprodução.
* ``WS  /ws/display/{slug}`` — canal WebSocket pelo qual o servidor avisa o
  player para recarregar quando algo muda.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import SessionLocal, get_db
from ..websocket_manager import manager

router = APIRouter(tags=["display"])


def _media_to_display_item(
    item: models.PlaylistItem, base_url: str
) -> schemas.DisplayItem:
    """Converte um item de playlist no formato consumido pelo player.

    Resolve a URL pública de mídias baseadas em arquivo e repassa conteúdo
    textual/HTML/URL conforme o tipo.

    Args:
        item: item de playlist com mídia carregada.
        base_url: URL base do servidor (ex.: ``http://host:8000``).

    Returns:
        schemas.DisplayItem: item pronto para exibição.
    """
    media = item.media
    url: str | None = None
    content: str | None = None

    if media.type in (models.MediaType.image, models.MediaType.video):
        url = f"{base_url}/media/{media.path}"
    elif media.type == models.MediaType.url:
        url = media.source_url
    else:  # text / html
        content = media.content

    return schemas.DisplayItem(
        type=media.type,
        duration=item.duration,
        name=media.name,
        url=url,
        content=content,
    )


def _compute_revision(screen: models.Screen) -> str:
    """Calcula um hash curto que muda sempre que a playlist da tela muda.

    O player usa esse valor para evitar reinicializar a reprodução quando o
    conteúdo não mudou de fato.

    Args:
        screen: tela com playlist (e itens) carregada.

    Returns:
        str: hash hexadecimal curto (12 caracteres).
    """
    parts: list[str] = [str(screen.id)]
    if screen.playlist is not None:
        parts.append(screen.playlist.updated_at.isoformat())
        for item in screen.playlist.items:
            parts.append(f"{item.id}:{item.position}:{item.duration}")
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return digest[:12]


@router.get("/api/display/{slug}", response_model=schemas.DisplayPayload)
def get_display(
    slug: str, request: Request, db: Session = Depends(get_db)
) -> schemas.DisplayPayload:
    """Retorna o conteúdo completo que o player deve reproduzir.

    Também atualiza ``last_seen`` da tela, funcionando como heartbeat.

    Args:
        slug: identificador público da tela.
        request: requisição (usada para derivar a URL base).
        db: sessão de banco injetada.

    Raises:
        HTTPException: se a tela não existir.
    """
    screen = crud.get_screen_by_slug(db, slug)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada.")

    # Heartbeat: registra que a tela está online.
    screen.last_seen = datetime.now(timezone.utc)
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    items: list[schemas.DisplayItem] = []
    playlist_name: str | None = None

    if screen.playlist is not None:
        playlist_name = screen.playlist.name
        ordered = sorted(screen.playlist.items, key=lambda it: it.position)
        items = [_media_to_display_item(it, base_url) for it in ordered]

    return schemas.DisplayPayload(
        screen=screen.slug,
        playlist_name=playlist_name,
        revision=_compute_revision(screen),
        items=items,
    )


@router.websocket("/ws/display/{slug}")
async def display_socket(websocket: WebSocket, slug: str) -> None:
    """Canal WebSocket que mantém o player sincronizado em tempo real.

    Fluxo:
        1. Valida que a tela existe (encerra com código 4404 caso contrário).
        2. Registra a conexão no :class:`ConnectionManager`.
        3. Permanece ouvindo; mensagens recebidas do player (ex.: "ping") são
           respondidas com "pong" para manter a conexão viva.
        4. Ao desconectar, remove a conexão do gerenciador.

    Args:
        websocket: conexão WebSocket de entrada.
        slug: identificador público da tela.
    """
    # Valida a existência da tela usando uma sessão curta e independente.
    with SessionLocal() as db:
        screen = crud.get_screen_by_slug(db, slug)
        if screen is None:
            await websocket.close(code=4404)
            return

    await manager.connect(slug, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(slug, websocket)
