"""Endpoints de agendamento de playlists por zona.

Cada agendamento define qual playlist uma zona exibe em determinados dias da
semana e faixa de horário (resolução em :func:`crud.resolve_active_playlist_id`).
As rotas ficam sob ``/api/zones/{zone_id}/schedules`` e exigem autenticação.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import require_auth
from ..database import get_db
from ..realtime import notify_screen

router = APIRouter(
    prefix="/api/zones", tags=["schedules"], dependencies=[Depends(require_auth)]
)


async def _notify_zone_screen(db: Session, zone: models.Zone, reason: str) -> None:
    """Notifica o player da tela dona da zona, se houver."""
    screen = crud.get_screen(db, zone.screen_id)
    if screen is not None:
        await notify_screen(screen.slug, reason=reason)


@router.post(
    "/{zone_id}/schedules",
    response_model=schemas.ScheduleRead,
    status_code=201,
)
async def create_schedule(
    zone_id: int, data: schemas.ScheduleCreate, db: Session = Depends(get_db)
) -> models.Schedule:
    """Cria uma regra de agendamento para a zona informada."""
    zone = crud.get_zone(db, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zona não encontrada.")
    if crud.get_playlist(db, data.playlist_id) is None:
        raise HTTPException(status_code=400, detail="Playlist inexistente.")
    schedule = crud.create_schedule(db, zone, data)
    await _notify_zone_screen(db, zone, "schedule-created")
    return schedule


@router.patch(
    "/{zone_id}/schedules/{schedule_id}",
    response_model=schemas.ScheduleRead,
)
async def update_schedule(
    zone_id: int,
    schedule_id: int,
    data: schemas.ScheduleUpdate,
    db: Session = Depends(get_db),
) -> models.Schedule:
    """Atualiza parcialmente uma regra de agendamento."""
    schedule = crud.get_schedule(db, schedule_id)
    if schedule is None or schedule.zone_id != zone_id:
        raise HTTPException(
            status_code=404, detail="Agendamento não encontrado."
        )
    if (
        data.playlist_id is not None
        and crud.get_playlist(db, data.playlist_id) is None
    ):
        raise HTTPException(status_code=400, detail="Playlist inexistente.")
    schedule = crud.update_schedule(db, schedule, data)
    zone = crud.get_zone(db, zone_id)
    if zone is not None:
        await _notify_zone_screen(db, zone, "schedule-updated")
    return schedule


@router.delete(
    "/{zone_id}/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_schedule(
    zone_id: int, schedule_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove uma regra de agendamento da zona."""
    schedule = crud.get_schedule(db, schedule_id)
    if schedule is None or schedule.zone_id != zone_id:
        raise HTTPException(
            status_code=404, detail="Agendamento não encontrado."
        )
    zone = crud.get_zone(db, zone_id)
    crud.delete_schedule(db, schedule)
    if zone is not None:
        await _notify_zone_screen(db, zone, "schedule-deleted")
