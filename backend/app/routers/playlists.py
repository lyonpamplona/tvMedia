"""Endpoints de gerenciamento de playlists e seus itens.

Alterações em uma playlist notificam, em tempo real, apenas as telas que a
usam (zona padrão ou agendamento), via :func:`notify_playlist_screens`.
A remoção notifica todas as telas por segurança. Todas as rotas exigem
autenticação.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth
from ..database import get_db
from ..realtime import notify_all_screens, notify_playlist_screens

router = APIRouter(
    prefix="/api/playlists", tags=["playlists"], dependencies=[Depends(require_auth)]
)


def _get_playlist_or_404(db: Session, playlist_id: int) -> models.Playlist:
    """Recupera uma playlist ou lança 404 se não existir."""
    playlist = crud.get_playlist(db, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return playlist


def _get_item_or_404(
    db: Session, playlist_id: int, item_id: int
) -> models.PlaylistItem:
    """Recupera um item garantindo que pertence à playlist informada."""
    item = crud.get_playlist_item(db, item_id)
    if item is None or item.playlist_id != playlist_id:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return item


@router.get("", response_model=list[schemas.PlaylistRead])
def list_playlists(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[models.Playlist]:
    """Lista as playlists da empresa em foco com seus itens."""
    return crud.list_playlists(db, company_id=scope.company_id)


@router.get("/{playlist_id}", response_model=schemas.PlaylistRead)
def get_playlist(playlist_id: int, db: Session = Depends(get_db)) -> models.Playlist:
    """Recupera uma playlist específica."""
    return _get_playlist_or_404(db, playlist_id)


@router.post("", response_model=schemas.PlaylistRead, status_code=201)
def create_playlist(
    data: schemas.PlaylistCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Cria uma playlist vazia na empresa em foco."""
    return crud.create_playlist(db, data, company_id=scope.write_company_id)


@router.patch("/{playlist_id}", response_model=schemas.PlaylistRead)
async def update_playlist(
    playlist_id: int, data: schemas.PlaylistUpdate, db: Session = Depends(get_db)
) -> models.Playlist:
    """Renomeia uma playlist e notifica as telas que a utilizam."""
    playlist = _get_playlist_or_404(db, playlist_id)
    playlist = crud.update_playlist(db, playlist, data)
    await notify_playlist_screens(db, playlist_id, reason="playlist-updated")
    return playlist


@router.delete(
    "/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_playlist(playlist_id: int, db: Session = Depends(get_db)) -> None:
    """Remove uma playlist e seus itens; notifica todas as telas."""
    playlist = _get_playlist_or_404(db, playlist_id)
    crud.delete_playlist(db, playlist)
    await notify_all_screens(db, reason="playlist-deleted")


@router.post("/{playlist_id}/items", response_model=schemas.PlaylistRead, status_code=201)
async def add_item(
    playlist_id: int, data: schemas.PlaylistItemCreate, db: Session = Depends(get_db)
) -> models.Playlist:
    """Adiciona um item de mídia a uma playlist."""
    playlist = _get_playlist_or_404(db, playlist_id)
    if crud.get_media(db, data.media_id) is None:
        raise HTTPException(status_code=400, detail="Mídia inexistente.")
    playlist = crud.add_playlist_item(db, playlist, data)
    await notify_playlist_screens(db, playlist_id, reason="playlist-item-added")
    return playlist


@router.patch(
    "/{playlist_id}/items/{item_id}", response_model=schemas.PlaylistRead
)
async def update_item(
    playlist_id: int,
    item_id: int,
    data: schemas.PlaylistItemUpdate,
    db: Session = Depends(get_db),
) -> models.Playlist:
    """Atualiza um item da playlist (duração, ajuste, transição, etc.)."""
    item = _get_item_or_404(db, playlist_id, item_id)
    playlist = crud.update_playlist_item(db, item, data)
    await notify_playlist_screens(db, playlist_id, reason="playlist-item-updated")
    return playlist


@router.delete(
    "/{playlist_id}/items/{item_id}", response_model=schemas.PlaylistRead
)
async def remove_item(
    playlist_id: int, item_id: int, db: Session = Depends(get_db)
) -> models.Playlist:
    """Remove um item de uma playlist."""
    item = _get_item_or_404(db, playlist_id, item_id)
    playlist = crud.remove_playlist_item(db, item)
    await notify_playlist_screens(db, playlist_id, reason="playlist-item-removed")
    return playlist


@router.post("/{playlist_id}/reorder", response_model=schemas.PlaylistRead)
async def reorder(
    playlist_id: int, data: schemas.ReorderRequest, db: Session = Depends(get_db)
) -> models.Playlist:
    """Reordena os itens de uma playlist conforme a sequência de IDs."""
    playlist = _get_playlist_or_404(db, playlist_id)
    playlist = crud.reorder_items(db, playlist, data.item_ids)
    await notify_playlist_screens(db, playlist_id, reason="playlist-reordered")
    return playlist
