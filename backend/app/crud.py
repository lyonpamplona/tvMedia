"""Operações de acesso a dados (CRUD) reutilizáveis pelos roteadores.

Inclui também a lógica de resolução de agendamento (qual playlist uma zona
deve exibir em um dado instante). Concentrar essa lógica aqui mantém os
endpoints enxutos e facilita testes.
"""

from __future__ import annotations

from datetime import datetime

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
    """Cria uma mídia baseada em texto/HTML/URL e persiste no banco."""
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
    """Registra uma mídia cujo arquivo já foi salvo em disco."""
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
    return db.scalar(_playlist_query().where(models.Playlist.id == playlist_id))


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
    """Adiciona um item à playlist na posição indicada (ou ao final)."""
    next_position = (
        data.position if data.position is not None else len(playlist.items)
    )
    item = models.PlaylistItem(
        playlist_id=playlist.id,
        media_id=data.media_id,
        duration=data.duration,
        position=next_position,
        fit=data.fit,
        transition=data.transition,
        muted=data.muted,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session, item: models.PlaylistItem, data: schemas.PlaylistItemUpdate
) -> models.PlaylistItem:
    """Atualiza duração, posição, ajuste e/ou transição de um item."""
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
    """Reordena os itens da playlist conforme a sequência de IDs informada."""
    order = {item_id: index for index, item_id in enumerate(item_ids)}
    for item in playlist.items:
        item.position = order.get(item.id, len(item_ids) + item.position)
    db.commit()


# --------------------------------------------------------------------------- #
# Screen
# --------------------------------------------------------------------------- #
def _screen_query():
    """Query base de tela com zonas e agendamentos pré-carregados."""
    return select(models.Screen).options(
        selectinload(models.Screen.zones).selectinload(models.Zone.schedules)
    )


def list_screens(db: Session) -> list[models.Screen]:
    """Retorna todas as telas cadastradas com suas zonas."""
    return list(db.scalars(_screen_query().order_by(models.Screen.id.desc())))


def get_screen(db: Session, screen_id: int) -> models.Screen | None:
    """Busca uma tela pelo ID com zonas e agendamentos."""
    return db.scalar(_screen_query().where(models.Screen.id == screen_id))


def get_screen_by_slug(db: Session, slug: str) -> models.Screen | None:
    """Busca uma tela pelo ``slug`` público com zonas e agendamentos."""
    return db.scalar(_screen_query().where(models.Screen.slug == slug))


def create_screen(db: Session, data: schemas.ScreenCreate) -> models.Screen:
    """Cria uma nova tela já com uma zona principal cobrindo 100%.

    A zona principal recebe ``default_playlist_id`` informado no payload,
    oferecendo o comportamento "tela simples" sem exigir criação manual de zona.
    """
    screen = models.Screen(name=data.name, timezone=data.timezone)
    screen.zones.append(
        models.Zone(
            name="Principal",
            x=0.0,
            y=0.0,
            width=100.0,
            height=100.0,
            z_index=0,
            default_playlist_id=data.default_playlist_id,
        )
    )
    db.add(screen)
    db.commit()
    db.refresh(screen)
    return screen


def update_screen(
    db: Session, screen: models.Screen, data: schemas.ScreenUpdate
) -> models.Screen:
    """Atualiza nome e/ou fuso horário de uma tela."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(screen, field, value)
    db.commit()
    db.refresh(screen)
    return screen


def delete_screen(db: Session, screen: models.Screen) -> None:
    """Remove uma tela (e suas zonas/agendamentos em cascata)."""
    db.delete(screen)
    db.commit()


# --------------------------------------------------------------------------- #
# Zone
# --------------------------------------------------------------------------- #
def get_zone(db: Session, zone_id: int) -> models.Zone | None:
    """Busca uma zona pelo ID com seus agendamentos."""
    return db.scalar(
        select(models.Zone)
        .options(selectinload(models.Zone.schedules))
        .where(models.Zone.id == zone_id)
    )


def create_zone(
    db: Session, screen: models.Screen, data: schemas.ZoneCreate
) -> models.Zone:
    """Cria uma nova zona em uma tela."""
    zone = models.Zone(screen_id=screen.id, **data.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def update_zone(
    db: Session, zone: models.Zone, data: schemas.ZoneUpdate
) -> models.Zone:
    """Atualiza geometria/nome/playlist padrão de uma zona."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    db.commit()
    db.refresh(zone)
    return zone


def delete_zone(db: Session, zone: models.Zone) -> None:
    """Remove uma zona (e seus agendamentos em cascata)."""
    db.delete(zone)
    db.commit()


# --------------------------------------------------------------------------- #
# Schedule
# --------------------------------------------------------------------------- #
def get_schedule(db: Session, schedule_id: int) -> models.Schedule | None:
    """Busca um agendamento pelo ID."""
    return db.get(models.Schedule, schedule_id)


def create_schedule(
    db: Session, zone: models.Zone, data: schemas.ScheduleCreate
) -> models.Schedule:
    """Cria um agendamento para uma zona."""
    schedule = models.Schedule(zone_id=zone.id, **data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule(
    db: Session, schedule: models.Schedule, data: schemas.ScheduleUpdate
) -> models.Schedule:
    """Atualiza parcialmente um agendamento."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule: models.Schedule) -> None:
    """Remove um agendamento."""
    db.delete(schedule)
    db.commit()


# --------------------------------------------------------------------------- #
# Resolução de agendamento
# --------------------------------------------------------------------------- #
def resolve_active_playlist_id(
    zone: models.Zone, now: datetime
) -> int | None:
    """Determina qual playlist uma zona deve exibir em um dado instante.

    Avalia os agendamentos da zona: dentre os que casam com o dia da semana e
    a faixa de horário de ``now``, vence o de maior ``priority``. Se nenhum
    casar, usa ``default_playlist_id`` da zona.

    Args:
        zone: zona com agendamentos carregados.
        now: datetime já convertido para o fuso da tela.

    Returns:
        int | None: ID da playlist ativa, ou None se a zona não tiver conteúdo.
    """
    minute_of_day = now.hour * 60 + now.minute
    weekday = now.weekday()  # 0=segunda … 6=domingo

    best: models.Schedule | None = None
    for schedule in zone.schedules:
        days = {
            int(d)
            for d in schedule.days_of_week.split(",")
            if d.strip().isdigit()
        }
        if weekday not in days:
            continue
        if not (schedule.start_minute <= minute_of_day < schedule.end_minute):
            continue
        if best is None or schedule.priority > best.priority:
            best = schedule

    if best is not None:
        return best.playlist_id
    return zone.default_playlist_id
