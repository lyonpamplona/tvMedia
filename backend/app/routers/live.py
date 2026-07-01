"""Mesa de transmissao ao vivo (L4).

Permite ao operador empurrar graficos (lower-thirds, banners, HUDs) e tomadas
de tela (takeover) para uma TV **instantaneamente**, sem recarregar a playlist.

A entrega reaproveita a infraestrutura ja existente:

* :class:`~app.models.PlayerCommand` como fila/registro de comandos por tela;
* :func:`~app.realtime.send_player_command` para empurrar via WebSocket
  (canal ``/ws/display/{slug}``);
* o player consome o comando em ``handleCommand`` e aplica o grafico em uma
  camada propria (``#live-layer``), preservando o conteudo em exibicao.

Comandos emitidos:

* ``live_gfx``       -> mostra um grafico (payload :class:`schemas.LiveGfxTrigger`).
* ``live_clear``     -> limpa um grafico (por ``slot_id``) ou todos.
* ``takeover``       -> tomada de tela com mensagem (:class:`schemas.LiveTakeover`).
* ``takeover_clear`` -> encerra a tomada de tela.

Todas as rotas exigem autenticacao e respeitam o escopo de empresa.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_current_user, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import send_player_command
from ..websocket_manager import manager

router = APIRouter(
    prefix="/api/live", tags=["live"], dependencies=[Depends(require_auth)]
)


def _resolve_screen(db: Session, scope: Scope, screen_id: int) -> models.Screen:
    """Carrega a tela garantindo que pertence ao escopo do solicitante."""
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela nao encontrada.")
    return screen


async def _dispatch(
    db: Session,
    screen: models.Screen,
    command_type: str,
    payload: dict,
    actor: models.User,
) -> models.PlayerCommand:
    """Cria o comando, empurra via WebSocket e marca como enviado se houver player."""
    command = crud.create_player_command(
        db,
        screen,
        schemas.PlayerCommandCreate(command_type=command_type, payload=payload),
        requested_by=actor.username,
    )
    await send_player_command(screen.slug, command)
    if manager.connection_count(screen.slug) > 0:
        command = crud.mark_command_sent(db, command)
    # Trilha de auditoria: registra o disparo ao vivo (mesa de transmissao).
    crud.record_audit(
        db,
        actor=actor.username,
        action=f"live.{command_type}",
        entity_type="screen",
        entity_id=screen.id,
        detail=f"{command_type} -> {screen.slug}",
        company_id=screen.company_id,
    )
    return command


@router.post(
    "/{screen_id}/trigger",
    response_model=schemas.PlayerCommandRead,
    status_code=201,
)
async def trigger_gfx(
    screen_id: int,
    data: schemas.LiveGfxTrigger,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> models.PlayerCommand:
    """Empurra um grafico ao vivo (lower-third/banner/HUD) para a tela."""
    screen = _resolve_screen(db, scope, screen_id)
    return await _dispatch(db, screen, "live_gfx", data.model_dump(), actor)


@router.post(
    "/{screen_id}/clear",
    response_model=schemas.PlayerCommandRead,
    status_code=201,
)
async def clear_gfx(
    screen_id: int,
    data: schemas.LiveClear | None = None,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> models.PlayerCommand:
    """Limpa um grafico ao vivo especifico (por ``slot_id``) ou todos."""
    screen = _resolve_screen(db, scope, screen_id)
    payload = {"slot_id": data.slot_id} if (data and data.slot_id) else {}
    return await _dispatch(db, screen, "live_clear", payload, actor)


@router.post(
    "/{screen_id}/takeover",
    response_model=schemas.PlayerCommandRead,
    status_code=201,
)
async def trigger_takeover(
    screen_id: int,
    data: schemas.LiveTakeover,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> models.PlayerCommand:
    """Dispara uma tomada de tela (full-screen) com mensagem em destaque."""
    screen = _resolve_screen(db, scope, screen_id)
    return await _dispatch(db, screen, "takeover", data.model_dump(), actor)


@router.post(
    "/{screen_id}/takeover/clear",
    response_model=schemas.PlayerCommandRead,
    status_code=201,
)
async def clear_takeover(
    screen_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(get_current_user),
    scope: Scope = Depends(get_scope),
) -> models.PlayerCommand:
    """Encerra a tomada de tela em exibicao."""
    screen = _resolve_screen(db, scope, screen_id)
    return await _dispatch(db, screen, "takeover_clear", {}, actor)
