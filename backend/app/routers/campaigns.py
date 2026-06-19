"""Endpoints de campanhas e interrupcoes de layout (P6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import notify_all_screens

router = APIRouter(
    prefix="/api/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(require_auth)],
)


def _validate_playlist(db: Session, playlist_id: int, scope: Scope) -> None:
    playlist = crud.get_playlist(db, playlist_id)
    if playlist is None or not scope_can_access(scope, playlist.company_id):
        raise HTTPException(status_code=400, detail="Playlist inexistente.")


def _validate_targets(
    db: Session,
    *,
    screen_ids: list[int] | None,
    screen_group_ids: list[int] | None,
    zone_ids: list[int] | None,
    scope: Scope,
) -> None:
    """Garante que todos os alvos pertencem ao escopo atual."""
    for screen_id in screen_ids or []:
        screen = crud.get_screen(db, screen_id)
        if screen is None or not scope_can_access(scope, screen.company_id):
            raise HTTPException(status_code=400, detail="Tela alvo inexistente.")
    for group_id in screen_group_ids or []:
        group = crud.get_screen_group(db, group_id)
        if group is None or not scope_can_access(scope, group.company_id):
            raise HTTPException(status_code=400, detail="Grupo alvo inexistente.")
    for zone_id in zone_ids or []:
        zone = crud.get_zone(db, zone_id)
        screen = crud.get_screen(db, zone.screen_id) if zone is not None else None
        if zone is None or screen is None or not scope_can_access(scope, screen.company_id):
            raise HTTPException(status_code=400, detail="Zona alvo inexistente.")


@router.get("", response_model=list[schemas.CampaignRead])
def list_campaigns(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[models.Campaign]:
    """Lista campanhas do escopo atual."""
    return crud.list_campaigns(db, company_id=scope.company_id)


@router.post("", response_model=schemas.CampaignRead, status_code=201)
async def create_campaign(
    data: schemas.CampaignCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Campaign:
    """Cria campanha agendada ou interrupcao."""
    _validate_playlist(db, data.playlist_id, scope)
    _validate_targets(
        db,
        screen_ids=data.screen_ids,
        screen_group_ids=data.screen_group_ids,
        zone_ids=data.zone_ids,
        scope=scope,
    )
    campaign = crud.create_campaign(db, data, company_id=scope.write_company_id)
    await notify_all_screens(db, reason="campaign-created")
    return campaign


@router.patch("/{campaign_id}", response_model=schemas.CampaignRead)
async def update_campaign(
    campaign_id: int,
    data: schemas.CampaignUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Campaign:
    """Atualiza campanha."""
    campaign = crud.get_campaign(db, campaign_id)
    if campaign is None or not scope_can_access(scope, campaign.company_id):
        raise HTTPException(status_code=404, detail="Campanha nao encontrada.")
    if data.playlist_id is not None:
        _validate_playlist(db, data.playlist_id, scope)
    _validate_targets(
        db,
        screen_ids=data.screen_ids,
        screen_group_ids=data.screen_group_ids,
        zone_ids=data.zone_ids,
        scope=scope,
    )
    campaign = crud.update_campaign(db, campaign, data)
    await notify_all_screens(db, reason="campaign-updated")
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove campanha."""
    campaign = crud.get_campaign(db, campaign_id)
    if campaign is None or not scope_can_access(scope, campaign.company_id):
        raise HTTPException(status_code=404, detail="Campanha nao encontrada.")
    crud.delete_campaign(db, campaign)
    await notify_all_screens(db, reason="campaign-deleted")
