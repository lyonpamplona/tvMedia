"""Operações de acesso a dados (CRUD) reutilizáveis pelos roteadores.

Concentrar a lógica de persistência aqui mantém os endpoints enxutos e
facilita testes. Todas as funções recebem uma ``Session`` ativa e não fazem
``commit`` implícito quando isso poderia surpreender o chamador — a regra de
commit é explicitada na docstring de cada função.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import models, schemas


# --------------------------------------------------------------------------- #
# Media
# --------------------------------------------------------------------------- #
def list_media(db: Session) -> list[models.Media]:
    """Retorna todas as mídias ordenadas da mais recente para a mais antiga."""
    return list(db.scalars(select(models.Media).order_by(models.Media.id.desc())))


def get_media(db: Session, media_id: int) -> models.Media | None:
    """Busca uma mídia pelo ID (ou ``None`` se inexistente)."""
    return db.get(models.Media, media_id)


def create_media(db: Session, data: schemas.MediaCreate) -> models.Media:
    """Cria uma mídia baseada em texto/HTML/URL e persiste no banco.

    Args:
        db: sessão ativa.
        data: dados validados de criação.

    Returns:
        models.Media: instância persistida (com ID atribuído).
    """
    media = models.Media(
        name=data.name,
        type=data.type,
        source_url=data.source_url,
        content=data.content,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def create_uploaded_media(
    db: Session, name: str, media_type: models.MediaType, relative_path: str
) -> models.Media:
    """Registra uma mídia cujo arquivo já foi salvo em disco.

    Args:
        db: sessão ativa.
        name: nome amigável da mídia.
        media_type: ``image`` ou ``video``.
        relative_path: caminho relativo do arquivo dentro do diretório de mídia.

    Returns:
        models.Media: instância persistida.
    """
    media = models.Media(name=name, type=media_type, path=relative_path)
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def update_media(
    db: Session, media: models.Media, data: schemas.MediaUpdate
) -> models.Media:
    """Aplica atualização parcial a uma mídia existente."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(media, field, value)
    db.commit()
    db.refresh(media)
    return media


def delete_media(db: Session, media: models.Media) -> None:
    """Remove uma mídia (e, em cascata, seus itens de playlist)."""
    db.delete(media)
    db.commit()


# --------------------------------------------------------------------------- #
# Playlist
# --------------------------------------------------------------------------- #
def _playlist_query():
    """Monta a query base de playlist com itens e mídias pré-carregados."""
    return select(models.Playlist).options(
        selectinload(models.Playlist.items).selectinload(models.PlaylistItem.media)
    )


def list_playlists(db: Session) -> list[models.Playlist]:
    """Retorna todas as playlists com seus itens carregados."""
    return list(db.scalars(_playlist_query().order_by(models.Playlist.id.desc())))


def get_playlist(db: Session, playlist_id: int) -> models.Playlist | None:
    """Busca uma playlist pelo ID com itens e mídias carregados."""
    return db.scalar(
        _playlist_query().where(models.Playlist.id == playlist_id)
    )


def create_playlist(db: Session, data: schemas.PlaylistCreate) -> models.Playlist:
    """Cria uma playlist vazia."""
    playlist = models.Playlist(name=data.name)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


def update_playlist(
    db: Session, playlist: models.Playlist, data: schemas.PlaylistUpdate
) -> models.Playlist:
    """Atualiza os dados básicos de uma playlist (ex.: nome)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(playlist, field, value)
    db.commit()
    db.refresh(playlist)
    return playlist


def delete_playlist(db: Session, playlist: models.Playlist) -> None:
    """Remove uma playlist e seus itens."""
    db.delete(playlist)
    db.commit()


def add_item(
    db: Session, playlist: models.Playlist, data: schemas.PlaylistItemCreate
) -> models.PlaylistItem:
    """Adiciona um item à playlist na posição indicada (ou ao final).

    Args:
        db: sessão ativa.
        playlist: playlist alvo.
        data: dados do item (mídia, duração e posição opcional).

    Returns:
        models.PlaylistItem: item criado.
    """
    next_position = (
        data.position
        if data.position is not None
        else len(playlist.items)
    )
    item = models.PlaylistItem(
        playlist_id=playlist.id,
        media_id=data.media_id,
        duration=data.duration,
        position=next_position,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session, item: models.PlaylistItem, data: schemas.PlaylistItemUpdate
) -> models.PlaylistItem:
    """Atualiza duração e/ou posição de um item de playlist."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, item: models.PlaylistItem) -> None:
    """Remove um item da playlist."""
    db.delete(item)
    db.commit()


def reorder_items(
    db: Session, playlist: models.Playlist, item_ids: list[int]
) -> None:
    """Reordena os itens da playlist conforme a sequência de IDs informada.

    Itens não citados em ``item_ids`` mantêm suas posições relativas ao final.

    Args:
        db: sessão ativa.
        playlist: playlist alvo.
        item_ids: IDs dos itens na nova ordem.
    """
    order = {item_id: index for index, item_id in enumerate(item_ids)}
    for item in playlist.items:
        item.position = order.get(item.id, len(item_ids) + item.position)
    db.commit()


# --------------------------------------------------------------------------- #
# Screen
# --------------------------------------------------------------------------- #
def list_screens(db: Session) -> list[models.Screen]:
    """Retorna todas as telas cadastradas."""
    return list(db.scalars(select(models.Screen).order_by(models.Screen.id.desc())))


def get_screen(db: Session, screen_id: int) -> models.Screen | None:
    """Busca uma tela pelo ID."""
    return db.get(models.Screen, screen_id)


def get_screen_by_slug(db: Session, slug: str) -> models.Screen | None:
    """Busca uma tela pelo ``slug`` público."""
    return db.scalar(select(models.Screen).where(models.Screen.slug == slug))


def create_screen(db: Session, data: schemas.ScreenCreate) -> models.Screen:
    """Cria uma nova tela com ``slug`` gerado automaticamente."""
    screen = models.Screen(name=data.name, playlist_id=data.playlist_id)
    db.add(screen)
    db.commit()
    db.refresh(screen)
    return screen


def update_screen(
    db: Session, screen: models.Screen, data: schemas.ScreenUpdate
) -> models.Screen:
    """Atualiza nome e/ou playlist vinculada de uma tela."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(screen, field, value)
    db.commit()
    db.refresh(screen)
    return screen


def delete_screen(db: Session, screen: models.Screen) -> None:
    """Remove uma tela."""
    db.delete(screen)
    db.commit()
