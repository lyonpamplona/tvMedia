"""Exposicao de metricas operacionais no formato Prometheus.

``GET /api/metrics`` retorna gauges em texto (exposition format) para alimentar
um scraper Prometheus/Grafana. As metricas sao escopadas a empresa em foco do
solicitante (mesmo modelo multiempresa do restante da API) e exigem token.

O endpoint pode ser desativado via ``METRICS_ENABLED=false``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import crud, models
from ..auth import Scope, get_scope, require_auth
from ..config import settings
from ..database import get_db
from ..websocket_manager import manager

router = APIRouter(prefix="/api/metrics", tags=["metrics"], dependencies=[Depends(require_auth)])

_ONLINE_WINDOW_SECONDS = 120


def _gauge(lines: list[str], name: str, value, help_text: str) -> None:
    """Adiciona um gauge no formato de exposicao do Prometheus."""
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} gauge")
    lines.append(f"{name} {value}")


@router.get("", response_class=PlainTextResponse)
def metrics(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> PlainTextResponse:
    """Retorna metricas da empresa em foco no formato Prometheus."""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metricas desativadas.")

    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    company_id = scope.company_id

    screens = crud.list_screens(db, company_id=company_id)
    online = 0
    connected_players = 0
    for screen in screens:
        connected_players += manager.connection_count(screen.slug)
        last_seen = screen.last_seen
        if last_seen is not None:
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            if (now - last_seen).total_seconds() <= _ONLINE_WINDOW_SECONDS:
                online += 1

    summary = crud.proof_of_play_summary(
        db, since=since_24h, screen_slug=None, company_id=company_id
    )
    ads = crud.proof_of_play(
        db, since=since_24h, company_id=company_id, limit=500, only_ads=True
    )
    ad_plays = sum(int(row.plays) for row in ads)

    media_stmt = select(func.count(models.Media.id))
    if company_id is not None:
        media_stmt = media_stmt.where(models.Media.company_id == company_id)
    media_total = int(db.scalar(media_stmt) or 0)

    lines: list[str] = []
    _gauge(lines, "tvmedia_screens_total", len(screens), "Total de telas cadastradas.")
    _gauge(lines, "tvmedia_screens_online", online, "Telas vistas nos ultimos 120s.")
    _gauge(lines, "tvmedia_players_connected", connected_players, "Players conectados via WebSocket.")
    _gauge(lines, "tvmedia_media_total", media_total, "Total de midias na biblioteca.")
    _gauge(lines, "tvmedia_play_events_24h", summary.total_plays, "Reproducoes nas ultimas 24h.")
    _gauge(lines, "tvmedia_play_seconds_24h", summary.total_seconds, "Segundos exibidos nas ultimas 24h.")
    _gauge(lines, "tvmedia_ad_plays_24h", ad_plays, "Exibicoes de anuncio (ad-break) nas ultimas 24h.")
    return PlainTextResponse("\n".join(lines) + "\n")
