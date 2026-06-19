"""Endpoints de gerenciamento de playlists e seus itens.

Alterações em uma playlist notificam, em tempo real, apenas as telas que a
usam (zona padrão ou agendamento), via :func:`notify_playlist_screens`.
A remoção notifica todas as telas por segurança. Todas as rotas exigem
autenticação.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import notify_all_screens, notify_playlist_screens

router = APIRouter(
    prefix="/api/playlists", tags=["playlists"], dependencies=[Depends(require_auth)]
)


def _get_playlist_or_404(
    db: Session, playlist_id: int, scope: Scope
) -> models.Playlist:
    """Recupera uma playlist da empresa em foco ou lança 404."""
    playlist = crud.get_playlist(db, playlist_id)
    if playlist is None or not scope_can_access(scope, playlist.company_id):
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return playlist


def _get_item_or_404(
    db: Session, playlist_id: int, item_id: int, scope: Scope
) -> models.PlaylistItem:
    """Recupera um item garantindo que pertence à playlist informada."""
    _get_playlist_or_404(db, playlist_id, scope)
    item = crud.get_playlist_item(db, item_id)
    if item is None or item.playlist_id != playlist_id:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return item


@router.get("", response_model=list[schemas.PlaylistRead])
def list_playlists(
    folder_id: int | None = Query(None, description="Filtra por pasta (0 = sem pasta)."),
    tag: str | None = Query(None, description="Filtra por tag."),
    q: str | None = Query(None, description="Busca por nome."),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[models.Playlist]:
    """Lista as playlists da empresa em foco com filtros P3."""
    return crud.list_playlists(
        db,
        company_id=scope.company_id,
        folder_id=folder_id,
        tag=tag,
        search=q,
    )


def _validate_playlist_folder(
    db: Session, folder_id: int | None, scope: Scope
) -> None:
    """Garante que a pasta de playlist existe no escopo atual."""
    if folder_id is None:
        return
    folder = crud.get_playlist_folder(db, folder_id)
    if folder is None or not scope_can_access(scope, folder.company_id):
        raise HTTPException(status_code=400, detail="Pasta de playlist inexistente.")


@router.get("/folders", response_model=list[schemas.FolderRead])
def list_playlist_folders(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[models.PlaylistFolder]:
    """Lista pastas de playlists da empresa em foco."""
    return crud.list_playlist_folders(db, company_id=scope.company_id)


@router.post("/folders", response_model=schemas.FolderRead, status_code=201)
def create_playlist_folder(
    data: schemas.FolderCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.PlaylistFolder:
    """Cria uma pasta de playlist."""
    if data.parent_id is not None:
        parent = crud.get_playlist_folder(db, data.parent_id)
        if parent is None or not scope_can_access(scope, parent.company_id):
            raise HTTPException(status_code=400, detail="Pasta pai inexistente.")
    return crud.create_playlist_folder(db, data, company_id=scope.write_company_id)


@router.patch("/folders/{folder_id}", response_model=schemas.FolderRead)
def update_playlist_folder(
    folder_id: int,
    data: schemas.FolderUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.PlaylistFolder:
    """Atualiza uma pasta de playlist."""
    folder = crud.get_playlist_folder(db, folder_id)
    if folder is None or not scope_can_access(scope, folder.company_id):
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    if data.parent_id == folder_id:
        raise HTTPException(status_code=400, detail="Uma pasta não pode ser pai de si mesma.")
    if data.parent_id is not None:
        parent = crud.get_playlist_folder(db, data.parent_id)
        if parent is None or not scope_can_access(scope, parent.company_id):
            raise HTTPException(status_code=400, detail="Pasta pai inexistente.")
    return crud.update_playlist_folder(db, folder, data)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_playlist_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove uma pasta de playlist."""
    folder = crud.get_playlist_folder(db, folder_id)
    if folder is None or not scope_can_access(scope, folder.company_id):
        raise HTTPException(status_code=404, detail="Pasta não encontrada.")
    crud.delete_playlist_folder(db, folder)


@router.post("/bulk-tags", response_model=schemas.BulkActionResult)
async def bulk_tag_playlists(
    data: schemas.BulkTagRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.BulkActionResult:
    """Adiciona tags a varias playlists da empresa em foco."""
    rows: list[models.Playlist] = []
    for playlist_id in data.ids:
        playlist = crud.get_playlist(db, playlist_id)
        if playlist is not None and scope_can_access(scope, playlist.company_id):
            rows.append(playlist)
    updated = crud.bulk_tag_playlists(db, rows, data.tags)
    for playlist in rows:
        await notify_playlist_screens(db, playlist.id, reason="playlist-bulk-tagged")
    return schemas.BulkActionResult(updated=updated, ids=[p.id for p in rows])


@router.post("/import", response_model=schemas.PlaylistRead, status_code=201)
async def import_playlist(
    data: schemas.PlaylistImport,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Importa uma playlist a partir do JSON exportado."""
    _validate_playlist_folder(db, data.folder_id, scope)
    file_types = (
        models.MediaType.image,
        models.MediaType.video,
        models.MediaType.audio,
    )
    playlist = crud.create_playlist(
        db,
        schemas.PlaylistCreate(
            name=data.name, tags=data.tags, folder_id=data.folder_id
        ),
        company_id=scope.write_company_id,
    )
    for entry in data.items:
        media = crud.find_media_by_name_type(
            db, name=entry.media_name, media_type=entry.media_type,
            company_id=scope.company_id,
        )
        if media is None:
            if entry.media_type in file_types:
                continue
            media = crud.create_media(
                db,
                name=entry.media_name,
                media_type=entry.media_type,
                source_url=entry.source_url,
                content=entry.content,
                tags=entry.tags,
                company_id=scope.write_company_id,
            )
        crud.add_playlist_item(
            db,
            playlist,
            schemas.PlaylistItemCreate(
                media_id=media.id,
                duration=entry.duration,
                fit=entry.fit,
                focal=entry.focal,
                transition=entry.transition,
                muted=entry.muted,
                play_full=entry.play_full,
                start_at=entry.start_at,
                end_at=entry.end_at,
            ),
        )
    return crud.get_playlist(db, playlist.id)


@router.get("/{playlist_id}", response_model=schemas.PlaylistRead)
def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Recupera uma playlist específica."""
    return _get_playlist_or_404(db, playlist_id, scope)


@router.post("", response_model=schemas.PlaylistRead, status_code=201)
def create_playlist(
    data: schemas.PlaylistCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Cria uma playlist vazia na empresa em foco."""
    _validate_playlist_folder(db, data.folder_id, scope)
    return crud.create_playlist(db, data, company_id=scope.write_company_id)


@router.patch("/{playlist_id}", response_model=schemas.PlaylistRead)
async def update_playlist(
    playlist_id: int,
    data: schemas.PlaylistUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Renomeia uma playlist e notifica as telas que a utilizam."""
    playlist = _get_playlist_or_404(db, playlist_id, scope)
    if "folder_id" in data.model_fields_set:
        _validate_playlist_folder(db, data.folder_id, scope)
    playlist = crud.update_playlist(db, playlist, data)
    await notify_playlist_screens(db, playlist_id, reason="playlist-updated")
    return playlist


@router.delete(
    "/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove uma playlist e seus itens; notifica todas as telas."""
    playlist = _get_playlist_or_404(db, playlist_id, scope)
    crud.delete_playlist(db, playlist)
    await notify_all_screens(db, reason="playlist-deleted")


@router.post("/{playlist_id}/items", response_model=schemas.PlaylistRead, status_code=201)
async def add_item(
    playlist_id: int,
    data: schemas.PlaylistItemCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Adiciona um item de mídia a uma playlist."""
    playlist = _get_playlist_or_404(db, playlist_id, scope)
    media = crud.get_media(db, data.media_id)
    if media is None or not scope_can_access(scope, media.company_id):
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
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Atualiza um item da playlist (duração, ajuste, transição, etc.)."""
    item = _get_item_or_404(db, playlist_id, item_id, scope)
    playlist = crud.update_playlist_item(db, item, data)
    await notify_playlist_screens(db, playlist_id, reason="playlist-item-updated")
    return playlist


@router.delete(
    "/{playlist_id}/items/{item_id}", response_model=schemas.PlaylistRead
)
async def remove_item(
    playlist_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Remove um item de uma playlist."""
    item = _get_item_or_404(db, playlist_id, item_id, scope)
    playlist = crud.remove_playlist_item(db, item)
    await notify_playlist_screens(db, playlist_id, reason="playlist-item-removed")
    return playlist


@router.post("/{playlist_id}/reorder", response_model=schemas.PlaylistRead)
async def reorder(
    playlist_id: int,
    data: schemas.ReorderRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Playlist:
    """Reordena os itens de uma playlist conforme a sequência de IDs."""
    playlist = _get_playlist_or_404(db, playlist_id, scope)
    playlist = crud.reorder_items(db, playlist, data.item_ids)
    await notify_playlist_screens(db, playlist_id, reason="playlist-reordered")
    return playlist


def _media_tags_list(media: models.Media) -> list[str]:
    """Converte as tags CSV de uma midia em lista limpa."""
    if not media.tags:
        return []
    return [t.strip() for t in media.tags.split(",") if t.strip()]


@router.get("/{playlist_id}/export")
def export_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> dict:
    """Exporta uma playlist como JSON (estrutura + metadados das midias).

    Arquivos binarios nao sao incluidos; midias de arquivo sao referenciadas
    por nome/tipo e reaproveitadas no import quando ja existirem.
    """
    playlist = _get_playlist_or_404(db, playlist_id, scope)
    items = []
    for it in sorted(playlist.items, key=lambda i: i.position):
        media = it.media
        items.append(
            {
                "duration": it.duration,
                "fit": it.fit.value,
                "focal": it.focal,
                "transition": it.transition.value,
                "muted": it.muted,
                "play_full": it.play_full,
                "start_at": it.start_at.isoformat() if it.start_at else None,
                "end_at": it.end_at.isoformat() if it.end_at else None,
                "media_name": media.name,
                "media_type": media.type.value,
                "source_url": media.source_url,
                "content": media.content,
                "tags": _media_tags_list(media),
            }
        )
    return {
        "version": 1,
        "name": playlist.name,
        "tags": _media_tags_list(playlist),
        "folder_id": playlist.folder_id,
        "items": items,
    }
