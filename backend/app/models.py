"""Modelos ORM (SQLAlchemy) do AdSignage.

O domínio é composto por quatro entidades principais:

* :class:`Media` — um recurso exibível (imagem, vídeo, texto, HTML ou URL).
* :class:`Playlist` — uma sequência ordenada de itens.
* :class:`PlaylistItem` — a associação entre uma playlist e uma mídia, com
  ordem e tempo de exibição.
* :class:`Screen` — uma TV/tela física identificada por um ``slug`` único,
  vinculada (opcionalmente) a uma playlist.
"""

from __future__ import annotations

import enum
import secrets
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
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
    screens: Mapped[list["Screen"]] = relationship(back_populates="playlist")


class PlaylistItem(Base):
    """Associa uma mídia a uma playlist com ordem e duração de exibição."""

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

    playlist: Mapped["Playlist"] = relationship(back_populates="items")
    media: Mapped["Media"] = relationship(back_populates="items")


class Screen(Base):
    """Uma TV/tela física que reproduz uma playlist.

    O campo ``slug`` é o identificador público usado na URL do player
    (ex.: ``/player/?screen=<slug>``) e no canal WebSocket. ``last_seen``
    registra o último "heartbeat" recebido do player.
    """

    __tablename__ = "screens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=_generate_slug
    )
    playlist_id: Mapped[int | None] = mapped_column(
        ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    playlist: Mapped["Playlist | None"] = relationship(back_populates="screens")
