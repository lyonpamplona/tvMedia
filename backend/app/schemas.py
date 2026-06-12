"""Esquemas Pydantic para validação de entrada e serialização de saída.

Convenção de sufixos: ``*Create`` (criação), ``*Update`` (atualização
parcial) e ``*Read`` (resposta da API). Inclui o contêiner genérico
:class:`Page` para respostas paginadas.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import FitMode, MediaType, Transition, UserRole


def _split_tags(value: object) -> object:
    """Normaliza tags vindas como CSV (do ORM) ou lista (da API) em lista."""
    if value is None:
        return []
    if isinstance(value, str):
        return [tag.strip() for tag in value.split(",") if tag.strip()]
    return value


# --------------------------------------------------------------------------- #
# Paginação
# --------------------------------------------------------------------------- #
T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Contêiner genérico de resposta paginada."""

    total: int = Field(..., description="Total de registros que casam o filtro.")
    limit: int = Field(..., description="Tamanho da página solicitada.")
    offset: int = Field(..., description="Deslocamento aplicado.")
    items: list[T] = Field(default_factory=list, description="Itens da página.")


# --------------------------------------------------------------------------- #
# Autenticação e usuários
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    """Payload de login do painel.

    ``username`` é opcional para compatibilidade com o fluxo antigo de senha
    única; quando omitido, assume o usuário administrador padrão.
    """

    username: str | None = Field(None, description="Usuário do painel.")
    password: str = Field(..., description="Senha do painel.")


class TokenResponse(BaseModel):
    """Resposta de login contendo o token de sessão assinado."""

    token: str
    expires_in: int = Field(..., description="Validade do token em segundos.")
    username: str
    role: UserRole


class ChangePasswordRequest(BaseModel):
    """Troca de senha do usuário autenticado."""

    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class UserCreate(BaseModel):
    """Payload de criação de usuário (somente admin)."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = Field(UserRole.editor)


class UserUpdate(BaseModel):
    """Atualização parcial de usuário (somente admin)."""

    password: str | None = Field(None, min_length=6, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    """Representação pública de um usuário."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


# --------------------------------------------------------------------------- #
# Pastas de mídia
# --------------------------------------------------------------------------- #
class FolderCreate(BaseModel):
    """Payload de criação de pasta de mídia."""

    name: str = Field(..., max_length=255)
    parent_id: int | None = None


class FolderUpdate(BaseModel):
    """Atualização parcial de pasta."""

    name: str | None = Field(None, max_length=255)
    parent_id: int | None = None


class FolderRead(BaseModel):
    """Representação de uma pasta de mídia."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None = None
    created_at: datetime


# --------------------------------------------------------------------------- #
# Media
# --------------------------------------------------------------------------- #
class MediaBase(BaseModel):
    """Campos comuns de mídia compartilhados entre criação e leitura."""

    name: str = Field(..., max_length=255, description="Nome amigável da mídia.")
    type: MediaType = Field(..., description="Tipo da mídia.")
    source_url: str | None = Field(None, description="URL de origem (tipo 'url').")
    content: str | None = Field(
        None, description="Conteúdo textual ou HTML (tipos 'text'/'html')."
    )
    tags: list[str] = Field(default_factory=list, description="Tags livres.")
    folder_id: int | None = Field(None, description="Pasta da mídia.")

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class MediaCreate(MediaBase):
    """Payload para criar mídia sem arquivo (texto, html, url, youtube, embed)."""


class MediaUpdate(BaseModel):
    """Campos opcionais para atualização parcial de mídia."""

    name: str | None = Field(None, max_length=255)
    source_url: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    folder_id: int | None = None

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class MediaRead(MediaBase):
    """Representação de mídia retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str | None = None
    created_at: datetime


class BulkUrlItem(BaseModel):
    """Item de importação em massa de mídia (texto/url/embed/youtube)."""

    name: str = Field(..., max_length=255)
    type: MediaType
    source_url: str | None = None
    content: str | None = None
    tags: list[str] = Field(default_factory=list)
    folder_id: int | None = None

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class BulkUrlRequest(BaseModel):
    """Payload de importação em massa."""

    items: list[BulkUrlItem] = Field(..., max_length=500)


# --------------------------------------------------------------------------- #
# PlaylistItem
# --------------------------------------------------------------------------- #
class PlaylistItemCreate(BaseModel):
    """Payload para adicionar um item a uma playlist."""

    media_id: int = Field(..., description="ID da mídia referenciada.")
    duration: int = Field(10, ge=1, le=86400, description="Tempo de exibição (s).")
    position: int | None = Field(None, description="Posição; ao final se omitido.")
    fit: FitMode = Field(FitMode.contain, description="Modo de ajuste à zona.")
    transition: Transition = Field(Transition.fade, description="Efeito de entrada.")
    muted: bool = Field(True, description="True silencia (recomendado p/ autoplay).")


class PlaylistItemUpdate(BaseModel):
    """Campos opcionais para atualizar um item da playlist."""

    duration: int | None = Field(None, ge=1, le=86400)
    position: int | None = None
    fit: FitMode | None = None
    transition: Transition | None = None
    muted: bool | None = None


class PlaylistItemRead(BaseModel):
    """Item de playlist com a mídia associada embutida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: int
    position: int
    duration: int
    fit: FitMode
    transition: Transition
    muted: bool
    media: MediaRead


# --------------------------------------------------------------------------- #
# Playlist
# --------------------------------------------------------------------------- #
class PlaylistCreate(BaseModel):
    """Payload para criar uma playlist."""

    name: str = Field(..., max_length=255)


class PlaylistUpdate(BaseModel):
    """Payload para renomear uma playlist."""

    name: str | None = Field(None, max_length=255)


class PlaylistRead(BaseModel):
    """Representação completa de uma playlist, com seus itens ordenados."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    items: list[PlaylistItemRead] = []


class ReorderRequest(BaseModel):
    """Payload para reordenar os itens de uma playlist."""

    item_ids: list[int] = Field(..., description="IDs dos itens na nova ordem.")


# --------------------------------------------------------------------------- #
# Schedule (agendamento)
# --------------------------------------------------------------------------- #
class ScheduleBase(BaseModel):
    """Campos de uma regra de agendamento de zona."""

    playlist_id: int = Field(..., description="Playlist exibida quando ativa.")
    days_of_week: str = Field(
        "0,1,2,3,4,5,6", description="Dias da semana (CSV, 0=segunda … 6=domingo)."
    )
    start_minute: int = Field(0, ge=0, le=1440, description="Início (min do dia).")
    end_minute: int = Field(1440, ge=0, le=1440, description="Fim (min do dia).")
    priority: int = Field(0, description="Maior vence em caso de sobreposição.")
    start_date: date | None = Field(None, description="Início da campanha (opcional).")
    end_date: date | None = Field(None, description="Fim da campanha (opcional).")

    @model_validator(mode="after")
    def _check_ranges(self) -> "ScheduleBase":
        """Valida coerência das faixas de horário e de datas."""
        if self.end_minute <= self.start_minute:
            raise ValueError("end_minute deve ser maior que start_minute.")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date não pode ser anterior a start_date.")
        return self


class ScheduleCreate(ScheduleBase):
    """Payload para criar um agendamento."""


class ScheduleUpdate(BaseModel):
    """Campos opcionais para atualizar um agendamento."""

    playlist_id: int | None = None
    days_of_week: str | None = None
    start_minute: int | None = Field(None, ge=0, le=1440)
    end_minute: int | None = Field(None, ge=0, le=1440)
    priority: int | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _check_ranges(self) -> "ScheduleUpdate":
        """Valida faixas quando ambos os limites são informados."""
        if (
            self.start_minute is not None
            and self.end_minute is not None
            and self.end_minute <= self.start_minute
        ):
            raise ValueError("end_minute deve ser maior que start_minute.")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date não pode ser anterior a start_date.")
        return self


class ScheduleRead(ScheduleBase):
    """Representação de um agendamento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_id: int


# --------------------------------------------------------------------------- #
# Zone
# --------------------------------------------------------------------------- #
class ZoneBase(BaseModel):
    """Geometria e playlist padrão de uma zona (valores em % da tela)."""

    name: str = Field("Zona", max_length=255)
    x: float = Field(0.0, ge=0, le=100)
    y: float = Field(0.0, ge=0, le=100)
    width: float = Field(100.0, ge=1, le=100)
    height: float = Field(100.0, ge=1, le=100)
    z_index: int = Field(0)
    default_playlist_id: int | None = Field(
        None, description="Playlist exibida fora de qualquer agendamento."
    )


class ZoneCreate(ZoneBase):
    """Payload para criar uma zona em uma tela."""


class ZoneUpdate(BaseModel):
    """Campos opcionais para atualizar uma zona."""

    name: str | None = Field(None, max_length=255)
    x: float | None = Field(None, ge=0, le=100)
    y: float | None = Field(None, ge=0, le=100)
    width: float | None = Field(None, ge=1, le=100)
    height: float | None = Field(None, ge=1, le=100)
    z_index: int | None = None
    default_playlist_id: int | None = None


class ZoneRead(ZoneBase):
    """Representação de uma zona, com seus agendamentos."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    screen_id: int
    schedules: list[ScheduleRead] = []


# --------------------------------------------------------------------------- #
# Screen
# --------------------------------------------------------------------------- #
class ScreenCreate(BaseModel):
    """Payload para registrar uma nova tela."""

    name: str = Field(..., max_length=255)
    timezone: str = Field("America/Sao_Paulo", description="Fuso IANA da tela.")
    default_playlist_id: int | None = Field(
        None, description="Playlist da zona principal criada automaticamente."
    )


class ScreenUpdate(BaseModel):
    """Campos opcionais para atualizar uma tela."""

    name: str | None = Field(None, max_length=255)
    timezone: str | None = None


class ScreenRead(BaseModel):
    """Representação de uma tela retornada pela API, com suas zonas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    timezone: str
    created_at: datetime
    last_seen: datetime | None = None
    zones: list[ZoneRead] = []


class ScreenHealth(BaseModel):
    """Estado de saúde/disponibilidade de uma tela."""

    id: int
    name: str
    slug: str
    last_seen: datetime | None = None
    online: bool = Field(..., description="True se vista recentemente.")
    connected_players: int = Field(0, description="Players conectados via WebSocket.")
    seconds_since_seen: int | None = None


# --------------------------------------------------------------------------- #
# Display (payload consumido pelo player)
# --------------------------------------------------------------------------- #
class DisplayItem(BaseModel):
    """Item já resolvido para reprodução no player."""

    media_id: int | None = None
    type: MediaType
    duration: int
    name: str
    fit: FitMode
    transition: Transition
    muted: bool = True
    url: str | None = None
    content: str | None = None


class DisplayZone(BaseModel):
    """Zona resolvida (geometria + itens da playlist ativa no momento)."""

    id: int
    name: str
    x: float
    y: float
    width: float
    height: float
    z_index: int
    playlist_name: str | None = None
    items: list[DisplayItem] = []


class DisplayPayload(BaseModel):
    """Conteúdo completo que o player precisa para reproduzir uma tela."""

    screen: str
    revision: str
    zones: list[DisplayZone] = []


# --------------------------------------------------------------------------- #
# Proof-of-play e auditoria
# --------------------------------------------------------------------------- #
class PlayEventCreate(BaseModel):
    """Evento de reprodução reportado pelo player."""

    media_id: int | None = None
    zone_id: int | None = None
    media_name: str = Field("", max_length=255)
    media_type: str = Field("", max_length=32)
    duration_seconds: int = Field(0, ge=0, le=86400)


class PlayEventBatch(BaseModel):
    """Lote de eventos de reprodução (o player agrega antes de enviar)."""

    events: list[PlayEventCreate] = Field(..., max_length=500)


class ProofOfPlayRow(BaseModel):
    """Linha agregada de proof-of-play."""

    media_id: int | None = None
    media_name: str
    plays: int
    total_seconds: int


class AuditLogRead(BaseModel):
    """Representação de um registro de auditoria."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str | None = None
    detail: str | None = None
    created_at: datetime
