"""Modelos ORM (SQLAlchemy) do AdSignage.

Domínio:

* :class:`User` — operador do painel, com papel (role) e versionamento de token
  para permitir revogação de sessões.
* :class:`MediaFolder` — pasta para organizar mídias (hierarquia opcional).
* :class:`Media` — recurso exibível (imagem, vídeo, texto, HTML, URL, embed),
  com pasta e tags opcionais.
* :class:`Playlist` / :class:`PlaylistItem` — sequência ordenada de itens.
* :class:`Screen` — uma TV identificada por ``slug`` único.
* :class:`Zone` — região retangular (em %) de uma tela, com playlist padrão.
* :class:`Schedule` — regra de agendamento por dia/hora e, opcionalmente, por
  faixa de datas (campanhas).
* :class:`AuditLog` — trilha de auditoria das alterações administrativas.
* :class:`PlayEvent` — registro de reprodução (proof-of-play).
"""

from __future__ import annotations

import enum
import secrets
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class MediaType(str, enum.Enum):
    """Tipos de mídia suportados pelo player."""

    image = "image"
    video = "video"
    text = "text"
    html = "html"
    url = "url"
    youtube = "youtube"
    embed = "embed"


class FitMode(str, enum.Enum):
    """Modo de ajuste do conteúdo à área da zona (mapeia para object-fit)."""

    contain = "contain"
    cover = "cover"
    fill = "fill"


class Transition(str, enum.Enum):
    """Efeito de transição entre itens consecutivos."""

    none = "none"
    fade = "fade"
    slide = "slide"


class UserRole(str, enum.Enum):
    """Papéis de acesso do painel.

    * ``admin`` — acesso total, incluindo gestão de usuários.
    * ``editor`` — gerencia mídia/playlists/telas, sem gestão de usuários.
    * ``viewer`` — somente leitura.
    """

    admin = "admin"
    editor = "editor"
    viewer = "viewer"


def _generate_slug() -> str:
    """Gera um identificador curto e seguro para URLs de telas."""
    return secrets.token_urlsafe(8)


class User(Base):
    """Operador do painel administrativo.

    ``token_version`` é incluído no token de sessão; incrementar o valor
    invalida imediatamente todos os tokens emitidos (logout global/revogação).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.editor
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class MediaFolder(Base):
    """Pasta para organizar mídias, com hierarquia opcional."""

    __tablename__ = "media_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Media(Base):
    """Representa um conteúdo exibível na tela."""

    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Tags livres separadas por vírgula (ex.: "promo,verao").
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    folder: Mapped["MediaFolder | None"] = relationship()
    items: Mapped[list["PlaylistItem"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class Playlist(Base):
    """Sequência ordenada de itens de mídia exibidos em loop."""

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["PlaylistItem"]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistItem.position",
    )


class PlaylistItem(Base):
    """Associa uma mídia a uma playlist com ordem, duração, ajuste e transição."""

    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    fit: Mapped[FitMode] = mapped_column(
        Enum(FitMode), nullable=False, default=FitMode.contain
    )
    transition: Mapped[Transition] = mapped_column(
        Enum(Transition), nullable=False, default=Transition.fade
    )
    muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    playlist: Mapped["Playlist"] = relationship(back_populates="items")
    media: Mapped["Media"] = relationship(back_populates="items")


class Screen(Base):
    """Uma TV/tela física que reproduz uma ou mais zonas."""

    __tablename__ = "screens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=_generate_slug
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="America/Sao_Paulo"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    zones: Mapped[list["Zone"]] = relationship(
        back_populates="screen",
        cascade="all, delete-orphan",
        order_by="Zone.z_index",
    )


class Zone(Base):
    """Região retangular de uma tela, com playlist e agendamentos próprios."""

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screen_id: Mapped[int] = mapped_column(
        ForeignKey("screens.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Zona")
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    z_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_playlist_id: Mapped[int | None] = mapped_column(
        ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True
    )

    screen: Mapped["Screen"] = relationship(back_populates="zones")
    default_playlist: Mapped["Playlist | None"] = relationship()
    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="zone",
        cascade="all, delete-orphan",
        order_by="Schedule.priority.desc()",
    )


class Schedule(Base):
    """Regra de agendamento de playlist para uma zona.

    Vale nos dias da semana em ``days_of_week`` (CSV de inteiros, 0=segunda …
    6=domingo) e na faixa de horário ``start_minute``–``end_minute`` (minutos
    desde a meia-noite). Opcionalmente limita-se a uma faixa de datas
    (``start_date``/``end_date``) para campanhas. Em sobreposição, vence a
    maior ``priority``.
    """

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), nullable=False
    )
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    days_of_week: Mapped[str] = mapped_column(
        String(32), nullable=False, default="0,1,2,3,4,5,6"
    )
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Faixa de datas opcional (campanhas). Nulo = sem limite.
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    zone: Mapped["Zone"] = relationship(back_populates="schedules")
    playlist: Mapped["Playlist"] = relationship()


class AuditLog(Base):
    """Trilha de auditoria de ações administrativas."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="sistema")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class PlayEvent(Base):
    """Registro de reprodução de uma mídia em uma tela (proof-of-play)."""

    __tablename__ = "play_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screen_slug: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    zone_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    media_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
