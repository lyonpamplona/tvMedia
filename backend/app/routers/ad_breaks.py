"""CRUD de ad-breaks recorrentes/agendados (L6).

Um ad-break agendado exibe uma midia de anuncio em tela cheia em intervalos de
relogio de parede (``every_minutes``), respeitando uma janela diaria
(``start_time``/``end_time``) e dias da semana (``days``). O disparo em si e
feito pelo ``player.js``; estes endpoints apenas gerenciam a configuracao. O
escopo multiempresa segue o restante da API (``Scope``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import notify_all_screens

router = APIRouter(
    prefix="/api/ad-breaks", tags=["ad-breaks"], dependencies=[Depends(require_auth)]
)


def _resolve_for_scope(
    db: Session, sched_id: int, scope: Scope
) -> models.AdBreakSchedule:
    """Carrega um ad-break garantindo que o solicitante pode acessa-lo."""
    sched = crud.get_ad_break_schedule(db, sched_id)
    if sched is None or not scope_can_access(scope, sched.company_id):
        raise HTTPException(status_code=404, detail="Ad-break nao encontrado.")
    return sched


def _validate_screen(db: Session, screen_id: int | None, scope: Scope) -> None:
    """Valida que a tela alvo (se houver) existe e e acessivel no escopo."""
    if screen_id is None:
        return
    screen = crud.get_screen(db, screen_id)
    if screen is None or not scope_can_access(scope, screen.company_id):
        raise HTTPException(status_code=400, detail="Tela alvo invalida.")


def _validate_media(db: Session, media_id: int | None, scope: Scope) -> None:
    """Valida que a midia do anuncio (se houver) existe e e acessivel."""
    if media_id is None:
        return
    media = crud.get_media(db, media_id)
    if media is None or not scope_can_access(scope, media.company_id):
        raise HTTPException(status_code=400, detail="Midia do anuncio invalida.")
    if media.type not in (models.MediaType.image, models.MediaType.video):
        raise HTTPException(
            status_code=400, detail="O anuncio deve ser uma imagem ou video."
        )


@router.get("", response_model=list[schemas.AdBreakScheduleRead])
def list_schedules(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[models.AdBreakSchedule]:
    """Lista os ad-breaks agendados da empresa em foco."""
    return crud.list_ad_break_schedules(db, company_id=scope.company_id)


@router.post(
    "", response_model=schemas.AdBreakScheduleRead, status_code=status.HTTP_201_CREATED
)
async def create_schedule(
    data: schemas.AdBreakScheduleCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.AdBreakSchedule:
    """Cria um ad-break recorrente/agendado."""
    _validate_screen(db, data.screen_id, scope)
    _validate_media(db, data.media_id, scope)
    sched = crud.create_ad_break_schedule(
        db, company_id=scope.write_company_id, data=data
    )
    await notify_all_screens(db, reason="ad-break-created")
    return sched


@router.patch("/{sched_id}", response_model=schemas.AdBreakScheduleRead)
async def update_schedule(
    sched_id: int,
    data: schemas.AdBreakScheduleUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.AdBreakSchedule:
    """Atualiza um ad-break agendado."""
    sched = _resolve_for_scope(db, sched_id, scope)
    fields = data.model_dump(exclude_unset=True)
    if "screen_id" in fields:
        _validate_screen(db, fields["screen_id"], scope)
    if "media_id" in fields:
        _validate_media(db, fields["media_id"], scope)
    sched = crud.update_ad_break_schedule(db, sched, data)
    await notify_all_screens(db, reason="ad-break-updated")
    return sched


@router.delete(
    "/{sched_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_schedule(
    sched_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove um ad-break agendado."""
    sched = _resolve_for_scope(db, sched_id, scope)
    crud.delete_ad_break_schedule(db, sched)
    await notify_all_screens(db, reason="ad-break-deleted")
