"""Modelos ORM (SQLAlchemy) do AdSignage — versão com zonas e agendamento.

Domínio:

* :class:`Media` — um recurso exibível (imagem, vídeo, texto, HTML ou URL).
* :class:`Playlist` — uma sequência ordenada de itens.
* :class:`PlaylistItem` — a associação entre uma playlist e uma mídia, com
  ordem, tempo de exibição, modo de ajuste (``fit``) e transição.
* :class:`Screen` — uma TV/tela física identificada por um ``slug`` único.
* :class:`Zone` — uma região retangular dentro de uma tela (em %), com sua
  própria playlist padrão. Permite múltiplas zonas simultâneas por tela.
* :class:`Schedule` — regra de agendamento que troca a playlist de uma zona
  conforme dia da semana e faixa de horário.
"""

from __future__ import annotations

import enum
import secrets
from datetime import datetime

from sqlalchemy import (
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


class FitMode(str, enum.Enum):
    """Modo de ajuste do conteúdo à área da zona (mapeia para object-fit)."""

    contain = "contain"  # cabe inteiro, pode deixar bordas
    cover = "cover"      # preenche a zona, pode cortar
    fill = "fill"        # estica para preencher exatamente


class Transition(str, enum.Enum):
    """Efeito de transição entre itens consecutivos."""

    none = "none"
    fade = "fade"
    slide = "slide"


def _generate_slug() -> str:
    """Gera um identificador curto e seguro para URLs de telas.

    Returns:
        str: token aleatório seguro para uso em URLs (~11 caracteres).
    """
    return secrets.token_urlsafe(8)


class Media(Base):
    """Representa um conteúdo exibível na tela.

    Para tipos baseados em arquivo (``image``/``video``) o campo ``path``
    guarda o caminho relativo dentro do diretório de mídia. Para ``text`` e
    ``html`` o conteúdo textual fica em ``content``. Para ``url`` o destino
    fica em ``source_url``.
    """

    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

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
    # Posição (0-based) usada para ordenar os itens dentro da playlist.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Tempo de exibição em segundos (ignorado por vídeos que tocam até o fim).
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    # Como o conteúdo se ajusta à zona.
    fit: Mapped[FitMode] = mapped_column(
        Enum(FitMode), nullable=False, default=FitMode.contain
    )
    # Efeito de entrada do item.
    transition: Mapped[Transition] = mapped_column(
        Enum(Transition), nullable=False, default=Transition.fade
    )

    playlist: Mapped["Playlist"] = relationship(back_populates="items")
    media: Mapped["Media"] = relationship(back_populates="items")


class Screen(Base):
    """Uma TV/tela física que reproduz uma ou mais zonas.

    O campo ``slug`` é o identificador público usado na URL do player
    (ex.: ``/player/?screen=<slug>``) e no canal WebSocket. ``last_seen``
    registra o último "heartbeat". ``timezone`` define o fuso usado para
    resolver agendamentos das zonas desta tela.
    """

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
    """Região retangular de uma tela, com playlist e agendamentos próprios.

    A posição e o tamanho são expressos em porcentagem (0–100) relativa à
    tela, permitindo layouts como "conteúdo principal + faixa de notícias".
    Uma tela simples tem uma única zona cobrindo 100%.
    """

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screen_id: Mapped[int] = mapped_column(
        ForeignKey("screens.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Zona")
    # Geometria em porcentagem da tela.
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    z_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Playlist exibida quando nenhum agendamento estiver ativo.
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

    A regra vale nos dias da semana indicados em ``days_of_week`` (CSV de
    inteiros, 0=segunda … 6=domingo) e na faixa de horário entre
    ``start_minute`` e ``end_minute`` (minutos desde a meia-noite, no fuso da
    tela). Em caso de sobreposição, vence a regra de maior ``priority``.
    """

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), nullable=False
    )
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    # Ex.: "0,1,2,3,4" = dias úteis.
    days_of_week: Mapped[str] = mapped_column(
        String(32), nullable=False, default="0,1,2,3,4,5,6"
    )
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    zone: Mapped["Zone"] = relationship(back_populates="schedules")
    playlist: Mapped["Playlist"] = relationship()
