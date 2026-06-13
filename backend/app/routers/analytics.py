"""Endpoints de analytics: proof-of-play e saúde das telas.

* ``GET /api/analytics/proof-of-play`` — agrega reproduções por mídia em uma
  janela de tempo (contagem e tempo total exibido).
* ``GET /api/analytics/screens/health`` — estado de cada tela (online/offline
  por último contato e número de players conectados via WebSocket).

Todas as rotas exigem autenticação.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import Scope, get_scope, require_auth
from ..database import get_db
from ..websocket_manager import manager

router = APIRouter(
    prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(require_auth)]
)

# Tela é considerada online se vista nos últimos N segundos (heartbeat ~60s).
_ONLINE_WINDOW_SECONDS = 120


@router.get("/proof-of-play", response_model=list[schemas.ProofOfPlayRow])
def proof_of_play(
    days: int = Query(7, ge=1, le=365),
    screen: str | None = Query(None, description="Filtra por slug de tela."),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[schemas.ProofOfPlayRow]:
    """Agrega os eventos de reprodução dos últimos ``days`` dias."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return crud.proof_of_play(db, since=since, screen_slug=screen, limit=limit)


@router.get("/screens/health", response_model=list[schemas.ScreenHealth])
def screens_health(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[schemas.ScreenHealth]:
    """Retorna o estado de saúde das telas da empresa em foco."""
    now = datetime.now(timezone.utc)
    health: list[schemas.ScreenHealth] = []
    for screen in crud.list_screens(db, company_id=scope.company_id):
        seconds_since: int | None = None
        online = False
        if screen.last_seen is not None:
            last_seen = screen.last_seen
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            seconds_since = int((now - last_seen).total_seconds())
            online = seconds_since <= _ONLINE_WINDOW_SECONDS
        health.append(
            schemas.ScreenHealth(
                id=screen.id,
                name=screen.name,
                slug=screen.slug,
                last_seen=screen.last_seen,
                online=online,
                connected_players=manager.connection_count(screen.slug),
                seconds_since_seen=seconds_since,
            )
        )
    return health
