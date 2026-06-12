"""Endpoints de gerenciamento de playlists e seus itens.

Qualquer alteração em uma playlist dispara uma notificação em tempo real para
todas as telas vinculadas a ela, garantindo que a TV atualize imediatamente.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..realtime import notify_playlist_screens

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


def _get_playlist_or_404(db: Session, playlist_id: int) -> models.Playlist:
    """Recupera uma playlist ou lança 404 se não existir."""
    playlist = crud.get_playlist(db, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return playlist


@router.get("", response_model=list[schemas.PlaylistRead])
def list_playlists(db: Session = Depends(get_db)) -> list[models.Playlist]:
    """Lista todas as playlists com seus itens."""
    return crud.list_playlists(db)


@router.get("/{playlist_id}", response_model=schemas.PlaylistRead)
def get_playlist(playlist_id: int, db: Session = Depends(get_db)) -> models.Playlist:
    """Recupera uma playlist específica."""
    return _get_playlist_or_404(db, playlist_id)


@router.post("", response_model=schemas.PlaylistRead, status_code=201)
def create_playlist(
    data: schemas.PlaylistCreate, db: Session = Depends(get_db)
) -> models.Playlist:
    """Cria uma playlist vazia."""
    return crud.create_playlist(db, data)


@router.patch("/{playlist_id}", response_model=schemas.PlaylistRead)
async def update_playlist(
    playlist_id: int, data: schemas.PlaylistUpdate, db: Session = Depends(get_db)
) -> models.Playlist:
    """Renomeia uma playlist e notifica as telas vinculadas."""
    playlist = _get_playlist_or_404(db, playlist_id)
    playlist = crud.update_playlist(db, playlist, data)
    await notify_playlist_screens(db, playlist.id, reason="playlist-updated")
    return playlist


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(playlist_id: int, db: Session = Depends(get_db)) -> None:
    """Remove uma playlist e notifica as telas que a usavam."""
    playlist = _get_playlist_or_404(db, playlist_id)
    playlist_id_value = playlist.id
    crud.delete_playlist(db, playlist)
    await notify_playlist_screens(db, playlist_id_value, reason="playlist-deleted")


@router.post("/{playlist_id}/items", response_model=schemas.PlaylistRead, status_code=201)
async def add_item(
    playlist_id: int,
    data: schemas.PlaylistItemCreate,
    db: Session = Depends(get_db),
) -> models.Playlist:
    """Adiciona um item à playlist e retorna a playlist atualizada."""
    playlist = _get_playlist_or_404(db, playlist_id)
    if crud.get_media(db, data.media_id) is None:
        raise HTTPException(status_code=400, detail="Mídia inexistente.")
    crud.add_item(db, playlist, data)
    await notify_playlist_screens(db, playlist.id, reason="item-added")
    return _get_playlist_or_404(db, playlist_id)


@router.patch(
    "/{playlist_id}/items/{item_id}", response_model=schemas.PlaylistRead
)
async def update_item(
    playlist_id: int,
    item_id: int,
    data: schemas.PlaylistItemUpdate,
    db: Session = Depends(get_db),
) -> models.Playlist:
    """Atualiza duração/posição de um item da playlist."""
    playlist = _get_playlist_or_404(db, playlist_id)
    item = db.get(models.PlaylistItem, item_id)
    if item is None or item.playlist_id != playlist.id:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    crud.update_item(db, item, data)
    await notify_playlist_screens(db, playlist.id, reason="item-updated")
    return _get_playlist_or_404(db, playlist_id)


@router.delete(
    "/{playlist_id}/items/{item_id}", response_model=schemas.PlaylistRead
)
async def delete_item(
    playlist_id: int, item_id: int, db: Session = Depends(get_db)
) -> models.Playlist:
    """Remove um item da playlist."""
    playlist = _get_playlist_or_404(db, playlist_id)
    item = db.get(models.PlaylistItem, item_id)
    if item is None or item.playlist_id != playlist.id:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    crud.remove_item(db, item)
    await notify_playlist_screens(db, playlist.id, reason="item-removed")
    return _get_playlist_or_404(db, playlist_id)


@router.post("/{playlist_id}/reorder", response_model=schemas.PlaylistRead)
async def reorder_items(
    playlist_id: int,
    data: schemas.ReorderRequest,
    db: Session = Depends(get_db),
) -> models.Playlist:
    """Reordena os itens de uma playlist conforme a sequência informada."""
    playlist = _get_playlist_or_404(db, playlist_id)
    crud.reorder_items(db, playlist, data.item_ids)
    await notify_playlist_screens(db, playlist.id, reason="reordered")
    return _get_playlist_or_404(db, playlist_id)
