"""Modelos ORM (SQLAlchemy) do tvMedia.

Dominio multi-empresa (multi-tenant):

* :class:`Company` — empresa/cliente (tenant). Cada empresa tem marca propria
  (nome, logo, cor) e isola seus usuarios, midias, playlists e telas.
* :class:`User` — operador do painel, vinculado a uma empresa, com papel (role),
  flag de super admin (controle global) e versionamento de token para revogacao.
* :class:`MediaFolder` / :class:`Media` — biblioteca de conteudo da empresa.
* :class:`Playlist` / :class:`PlaylistItem` — sequencia ordenada de itens.
* :class:`Screen` — uma TV identificada por ``slug`` unico, com codigo de
  emparelhamento e grupo de sincronia opcional.
* :class:`Zone` — regiao retangular (em %) de uma tela, com playlist padrao.
* :class:`Schedule` — regra de agendamento por dia/hora e faixa de datas.
* :class:`AuditLog` — trilha de auditoria das alteracoes administrativas.
* :class:`PlayEvent` — registro de reproducao (proof-of-play).
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
    """Tipos de midia suportados pelo player."""

    image = "image"
    video = "video"
    text = "text"
    html = "html"
    url = "url"
    youtube = "youtube"
    embed = "embed"
    audio = "audio"
    clock = "clock"
    weather = "weather"
    news = "news"
    promo = "promo"


class FitMode(str, enum.Enum):
    """Modo de ajuste do conteudo a area da zona (mapeia para object-fit)."""

    contain = "contain"
    cover = "cover"
    fill = "fill"


class Transition(str, enum.Enum):
    """Efeito de transicao entre itens consecutivos."""

    none = "none"
    fade = "fade"
    slide = "slide"


class UserRole(str, enum.Enum):
    """Papeis de acesso do painel.

    * ``admin`` — acesso total dentro da empresa, incluindo gestao de usuarios.
    * ``editor`` — gerencia midia/playlists/telas, sem gestao de usuarios.
    * ``viewer`` — somente leitura.
    """

    admin = "admin"
    editor = "editor"
    viewer = "viewer"


def _generate_slug() -> str:
    """Gera um identificador curto e seguro para URLs de telas."""
    return secrets.token_urlsafe(8)


def _generate_company_slug() -> str:
    """Gera um identificador curto para empresas."""
    return secrets.token_urlsafe(6)


def _generate_pair_code() -> str:
    """Gera um codigo numerico de 6 digitos para emparelhar uma TV."""
    return f"{secrets.randbelow(1000000):06d}"


class Company(Base):
    """Empresa/cliente (tenant) com marca propria e dados isolados."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=_generate_company_slug
    )
    # Caminho relativo (em media_dir) do logo enviado, se houver.
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Cor de destaque da marca (hex, ex.: '#7aa2f7').
    primary_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Mensagem de emergencia/override exibida em tela cheia em todas as telas
    # da empresa quando ``emergency_active`` esta ligado.
    emergency_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class User(Base):
    """Operador do painel administrativo, vinculado a uma empresa.

    ``token_version`` e incluido no token de sessao; incrementar o valor
    invalida imediatamente todos os tokens emitidos (logout global/revogacao).
    ``is_super_admin`` concede controle global (gestao de empresas e acesso ao
    conteudo de qualquer empresa), independentemente da empresa de origem.
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
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company: Mapped["Company | None"] = relationship()


class MediaFolder(Base):
    """Pasta para organizar midias, com hierarquia opcional."""

    __tablename__ = "media_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Media(Base):
    """Representa um conteudo exibivel na tela."""

    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Dimensoes originais (px) detectadas no upload (imagens/videos).
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Versao otimizada (reescala/transcodificacao) servida no lugar do
    # original quando presente; o original permanece como backup.
    optimized_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Poster/miniatura do video (primeiro quadro), usada como cartaz.
    poster_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Estado do processamento server-side:
    # pending|processing|done|skipped|failed.
    processing_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    # Observacao do processamento (motivo de skip/falha), p/ diagnostico.
    processing_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Tags livres separadas por virgula (ex.: "promo,verao").
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    folder: Mapped["MediaFolder | None"] = relationship()
    items: Mapped[list["PlaylistItem"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class Playlist(Base):
    """Sequencia ordenada de itens de midia exibidos em loop."""

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
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
    """Associa uma midia a uma playlist com ordem, duracao, ajuste e transicao."""

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
    # Ponto focal do recorte quando o ajuste e "cover".
    focal: Mapped[str] = mapped_column(String(16), nullable=False, default="center")
    transition: Mapped[Transition] = mapped_column(
        Enum(Transition), nullable=False, default=Transition.fade
    )
    muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Tocar a midia inteira (video/audio/YouTube) em vez de cortar na duracao.
    play_full: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    playlist: Mapped["Playlist"] = relationship(back_populates="items")
    media: Mapped["Media"] = relationship(back_populates="items")


class Screen(Base):
    """Uma TV/tela fisica que reproduz uma ou mais zonas."""

    __tablename__ = "screens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=_generate_slug
    )
    # Codigo curto (6 digitos) para emparelhar uma TV nova sem digitar o slug.
    pair_code: Mapped[str | None] = mapped_column(
        String(12), unique=True, index=True, default=_generate_pair_code
    )
    # Grupo de sincronia: telas no mesmo grupo recarregam juntas (parque de TVs).
    sync_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Resolucao nativa do painel (ex.: "1920x1080"), orientacao e tamanho em polegadas.
    resolution: Mapped[str | None] = mapped_column(String(16), nullable=True)
    orientation: Mapped[str] = mapped_column(String(16), nullable=False, default="landscape")
    size_inches: Mapped[str | None] = mapped_column(String(8), nullable=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
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
    # Musica de fundo (midia tipo 'audio') tocada em loop no nivel da tela.
    background_audio_id: Mapped[int | None] = mapped_column(
        ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )

    zones: Mapped[list["Zone"]] = relationship(
        back_populates="screen",
        cascade="all, delete-orphan",
        order_by="Zone.z_index",
    )


class Zone(Base):
    """Regiao retangular de uma tela, com playlist e agendamentos proprios."""

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

    Vale nos dias da semana em ``days_of_week`` (CSV de inteiros, 0=segunda ...
    6=domingo) e na faixa de horario ``start_minute``-``end_minute`` (minutos
    desde a meia-noite). Opcionalmente limita-se a uma faixa de datas
    (``start_date``/``end_date``) para campanhas. Em sobreposicao, vence a
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
    """Trilha de auditoria de acoes administrativas."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="sistema")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class PlayEvent(Base):
    """Registro de reproducao de uma midia em uma tela (proof-of-play)."""

    __tablename__ = "play_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screen_slug: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    zone_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    media_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
