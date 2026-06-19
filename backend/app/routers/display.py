"""Endpoints públicos consumidos pelo player na TV.

Inclui:

* ``GET /api/display/{slug}`` — monta o payload de exibição resolvendo, para
  cada zona, a playlist ativa no momento (considerando agendamentos e fuso da
  tela). Também registra um "heartbeat" (``last_seen``).
* ``POST /api/display/{slug}/events`` — recebe lotes de eventos de reprodução
  (proof-of-play) reportados pelo player.
* ``WS /ws/display/{slug}`` — canal de tempo real; o servidor envia
  ``{"type": "reload"}`` quando o conteúdo da tela muda.

Estes endpoints são públicos (sem autenticação): a TV só conhece o ``slug``.
A montagem do payload foi extraída para :mod:`app.services`, de modo que a
pré-visualização do painel use exatamente a mesma lógica do player.
"""

from __future__ import annotations

import base64
import binascii

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from .. import crud, models, schemas, services
from ..config import settings
from ..database import SessionLocal, get_db
from ..websocket_manager import manager

router = APIRouter(tags=["display"])


@router.post("/api/display/pair", response_model=schemas.PairResponse)
def pair_screen(data: schemas.PairRequest, db: Session = Depends(get_db)) -> schemas.PairResponse:
    """Empareia uma TV a partir de um código numérico exibido na tela.

    Fluxo para parque grande de TVs: o painel mostra o código de cada tela; ao
    digitá-lo no dispositivo, ele recebe o ``slug`` e passa a tocar o conteúdo.

    Raises:
        HTTPException: 404 quando o código não corresponde a nenhuma tela.
    """
    screen = crud.get_screen_by_code(db, data.code.strip())
    if screen is None:
        raise HTTPException(status_code=404, detail="Código de emparelhamento inválido.")
    return schemas.PairResponse(slug=screen.slug, name=screen.name)


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
    crud.touch_screen_seen(db, screen)

    return services.build_display_payload(str(request.base_url), db, screen)


@router.post(
    "/api/display/{slug}/events", response_model=dict, status_code=202
)
def report_events(
    slug: str, batch: schemas.PlayEventBatch, db: Session = Depends(get_db)
) -> dict:
    """Recebe um lote de eventos de reprodução (proof-of-play) do player.

    O player agrega os eventos em memória e os envia periodicamente para
    reduzir o número de requisições. Endpoint público, idempotente o bastante
    para a finalidade (apenas registra).

    Raises:
        HTTPException: 404 quando o ``slug`` não corresponde a uma tela.
    """
    screen = crud.get_screen_by_slug(db, slug)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    stored = crud.record_play_events(
        db,
        screen_slug=slug,
        events=batch.events,
        company_id=screen.company_id,
    )
    return {"stored": stored}


def _save_screenshot(slug: str, command_id: int, data_url: str | None) -> str | None:
    """Salva screenshot enviado pelo player como PNG em /media/screenshots."""
    if not data_url or "," not in data_url:
        return None
    header, raw = data_url.split(",", 1)
    if "image/png" not in header and "image/jpeg" not in header:
        return None
    ext = ".jpg" if "image/jpeg" in header else ".png"
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(data) > 8 * 1024 * 1024:
        return None
    out_dir = settings.media_dir / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{slug}-{command_id}{ext}"
    (out_dir / name).write_bytes(data)
    return f"screenshots/{name}"


@router.post("/api/display/{slug}/commands/{command_id}/result", response_model=schemas.PlayerCommandRead)
def report_command_result(
    slug: str,
    command_id: int,
    data: schemas.PlayerCommandResult,
    db: Session = Depends(get_db),
) -> models.PlayerCommand:
    """Recebe resultado de comando executado pelo player."""
    screen = crud.get_screen_by_slug(db, slug)
    if screen is None:
        raise HTTPException(status_code=404, detail="Tela não encontrada.")
    command = crud.get_player_command(db, command_id)
    if command is None or command.screen_id != screen.id:
        raise HTTPException(status_code=404, detail="Comando não encontrado.")
    result_path = None
    if command.command_type == "screenshot":
        result_path = _save_screenshot(slug, command_id, data.data_url)
    return crud.complete_player_command(
        db,
        command,
        status=data.status,
        result=data.result,
        result_path=result_path,
    )


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
