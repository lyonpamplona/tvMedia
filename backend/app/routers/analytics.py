"""Endpoints de analytics: proof-of-play e saúde das telas.

* ``GET /api/analytics/proof-of-play`` — agrega reproduções por mídia em uma
  janela de tempo (contagem e tempo total exibido).
* ``GET /api/analytics/screens/health`` — estado de cada tela (online/offline
  por último contato e número de players conectados via WebSocket).

Todas as rotas exigem autenticação.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import crud, models, reports, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..websocket_manager import manager

router = APIRouter(
    prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(require_auth)]
)

# Tela é considerada online se vista nos últimos N segundos (heartbeat ~60s).
_ONLINE_WINDOW_SECONDS = 120


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _validate_screen_slug(db: Session, screen_slug: str | None, scope: Scope) -> None:
    if not screen_slug:
        return
    screen = crud.get_screen_by_slug(db, screen_slug)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=404, detail="Tela não encontrada.")


@router.get("/proof-of-play", response_model=list[schemas.ProofOfPlayRow])
def proof_of_play(
    days: int = Query(7, ge=1, le=365),
    screen: str | None = Query(None, description="Filtra por slug de tela."),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[schemas.ProofOfPlayRow]:
    """Agrega os eventos de reprodução dos últimos ``days`` dias (por empresa)."""
    _validate_screen_slug(db, screen, scope)
    since = _since(days)
    return crud.proof_of_play(
        db,
        since=since,
        screen_slug=screen,
        company_id=scope.company_id,
        limit=limit,
    )


@router.get("/proof-of-play/summary", response_model=schemas.ProofOfPlaySummary)
def proof_of_play_summary(
    days: int = Query(7, ge=1, le=365),
    screen: str | None = Query(None),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.ProofOfPlaySummary:
    """Resumo executivo para dashboards BI."""
    _validate_screen_slug(db, screen, scope)
    return crud.proof_of_play_summary(
        db, since=_since(days), screen_slug=screen, company_id=scope.company_id
    )


@router.get("/proof-of-play/details", response_model=list[schemas.ProofOfPlayDetailRow])
def proof_of_play_details(
    days: int = Query(7, ge=1, le=365),
    screen: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[schemas.ProofOfPlayDetailRow]:
    """Eventos detalhados para BI/auditoria."""
    _validate_screen_slug(db, screen, scope)
    return crud.proof_of_play_details(
        db, since=_since(days), screen_slug=screen, company_id=scope.company_id, limit=limit
    )


@router.get("/proof-of-play/export.csv", response_class=Response)
def proof_of_play_csv(
    days: int = Query(7, ge=1, le=365),
    screen: str | None = Query(None),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> Response:
    """Exporta eventos detalhados em CSV."""
    _validate_screen_slug(db, screen, scope)
    rows = crud.proof_of_play_details(
        db, since=_since(days), screen_slug=screen, company_id=scope.company_id, limit=10000
    )
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["played_at", "screen_slug", "zone_id", "media_id", "media_name", "media_type", "duration_seconds"])
    for row in rows:
        writer.writerow([row.played_at.isoformat(), row.screen_slug, row.zone_id or "", row.media_id or "", row.media_name, row.media_type, row.duration_seconds])
    filename = "proof-of-play.csv"
    return Response(
        content=out.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports", response_model=list[schemas.ReportScheduleRead])
def list_reports(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[models.ReportSchedule]:
    """Lista relatórios agendados."""
    return crud.list_report_schedules(db, company_id=scope.company_id)


@router.post("/reports", response_model=schemas.ReportScheduleRead, status_code=201)
def create_report(
    data: schemas.ReportScheduleCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.ReportSchedule:
    """Cria relatório agendado por e-mail."""
    _validate_screen_slug(db, data.screen_slug, scope)
    return crud.create_report_schedule(db, data, company_id=scope.write_company_id)


@router.patch("/reports/{report_id}", response_model=schemas.ReportScheduleRead)
def update_report(
    report_id: int,
    data: schemas.ReportScheduleUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.ReportSchedule:
    """Atualiza relatório agendado."""
    row = crud.get_report_schedule(db, report_id)
    if row is None or not scope_can_access(scope, row.company_id):
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    _validate_screen_slug(db, data.screen_slug, scope)
    return crud.update_report_schedule(db, row, data)


@router.post("/reports/{report_id}/send", response_model=dict)
def send_report_now(
    report_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> dict:
    """Envia um relatório imediatamente para testar SMTP/anexos."""
    row = crud.get_report_schedule(db, report_id)
    if row is None or not scope_can_access(scope, row.company_id):
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    sent = reports.send_report_once(db, row)
    return {"sent": sent}


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove relatório agendado."""
    row = crud.get_report_schedule(db, report_id)
    if row is None or not scope_can_access(scope, row.company_id):
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    crud.delete_report_schedule(db, row)


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
                tags=screen.tags or "",
                location_label=screen.location_label,
                latitude=screen.latitude,
                longitude=screen.longitude,
                sync_group=screen.sync_group,
                open_commands=crud.open_command_count(db, screen.id),
            )
        )
    return health
