"""Esquemas Pydantic para validacao de entrada e serializacao de saida.

Convencao de sufixos: ``*Create`` (criacao), ``*Update`` (atualizacao
parcial) e ``*Read`` (resposta da API). Inclui o conteiner generico
:class:`Page` para respostas paginadas e os esquemas multi-empresa.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import FitMode, MediaType, Transition, UserRole

# Animacoes de entrada/saida de overlays (L1 - Live Graphics).
AnimKind = Literal["none", "fade", "slide", "wipe"]


def _split_tags(value: object) -> object:
    """Normaliza tags vindas como CSV (do ORM) ou lista (da API) em lista."""
    if value is None:
        return []
    if isinstance(value, str):
        return [tag.strip() for tag in value.split(",") if tag.strip()]
    return value


def _split_ints(value: object) -> object:
    """Normaliza uma lista de IDs vinda como CSV/JSON/lista."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return [int(part) for part in value.split(",") if part.strip().isdigit()]
    return value


def _parse_json_dict(value: object) -> object:
    """Normaliza dicionarios armazenados como JSON textual."""
    if value is None or isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return value


def _parse_json_list(value: object) -> object:
    """Normaliza listas armazenadas como JSON textual."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return value


# --------------------------------------------------------------------------- #
# Paginacao
# --------------------------------------------------------------------------- #
T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Conteiner generico de resposta paginada."""

    total: int = Field(..., description="Total de registros que casam o filtro.")
    limit: int = Field(..., description="Tamanho da pagina solicitada.")
    offset: int = Field(..., description="Deslocamento aplicado.")
    items: list[T] = Field(default_factory=list, description="Itens da pagina.")


# --------------------------------------------------------------------------- #
# Empresas (multi-tenant)
# --------------------------------------------------------------------------- #
class CompanyCreate(BaseModel):
    """Payload de criacao de empresa (somente super admin).

    Opcionalmente cria o usuario administrador inicial da empresa.
    """

    name: str = Field(..., min_length=2, max_length=255)
    primary_color: str | None = Field(None, max_length=16)
    admin_username: str | None = Field(None, min_length=3, max_length=64)
    admin_password: str | None = Field(None, min_length=6, max_length=128)


class CompanyUpdate(BaseModel):
    """Atualizacao parcial de empresa."""

    name: str | None = Field(None, min_length=2, max_length=255)
    primary_color: str | None = Field(None, max_length=16)
    emergency_message: str | None = Field(None, max_length=2000)
    emergency_active: bool | None = None
    is_active: bool | None = None


class CompanyRead(BaseModel):
    """Representacao de uma empresa."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    logo_path: str | None = None
    primary_color: str | None = None
    emergency_message: str | None = None
    emergency_active: bool = False
    is_active: bool
    created_at: datetime


class CompanyStats(CompanyRead):
    """Empresa com contadores agregados (painel de super admin)."""

    users: int = 0
    screens: int = 0
    media: int = 0
    playlists: int = 0


class BrandingRead(BaseModel):
    """Marca exibida no painel apos o login (nome/logo/cor da empresa)."""

    company_id: int | None = None
    company_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None


# --------------------------------------------------------------------------- #
# Autenticacao e usuarios
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    """Payload de login do painel.

    ``username`` e opcional para compatibilidade com o fluxo antigo de senha
    unica; quando omitido, assume o usuario administrador padrao. A empresa e
    resolvida automaticamente a partir do usuario.
    """

    username: str | None = Field(None, description="Usuario do painel.")
    password: str = Field(..., description="Senha do painel.")
    totp_code: str | None = Field(None, min_length=6, max_length=8, description="Codigo 2FA quando habilitado.")


class TokenResponse(BaseModel):
    """Resposta de login contendo o token de sessao assinado."""

    token: str
    expires_in: int = Field(..., description="Validade do token em segundos.")
    username: str
    role: UserRole
    is_super_admin: bool = False
    company_id: int | None = None
    company_name: str | None = None
    two_factor_required: bool = False


class ChangePasswordRequest(BaseModel):
    """Troca de senha do usuario autenticado."""

    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class UserCreate(BaseModel):
    """Payload de criacao de usuario (somente admin)."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = Field(UserRole.editor)


class UserUpdate(BaseModel):
    """Atualizacao parcial de usuario (somente admin)."""

    password: str | None = Field(None, min_length=6, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    """Representacao publica de um usuario."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    is_active: bool
    is_super_admin: bool = False
    company_id: int | None = None
    created_at: datetime
    last_login: datetime | None = None
    totp_enabled: bool = False


class TotpSetupRead(BaseModel):
    """Segredo TOTP para configurar app autenticador."""

    secret: str
    otpauth_url: str


class TotpVerifyRequest(BaseModel):
    """Codigo TOTP digitado pelo usuario."""

    code: str = Field(..., min_length=6, max_length=8)


class TotpDisableRequest(BaseModel):
    """Desativa 2FA confirmando senha atual."""

    current_password: str


class ApiTokenCreate(BaseModel):
    """Cria token de API pessoal."""

    name: str = Field(..., min_length=2, max_length=255)
    scopes: list[str] = Field(default_factory=lambda: ["read"], max_length=10)
    expires_at: datetime | None = None


class ApiTokenRead(BaseModel):
    """Metadados de token de API sem revelar o segredo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    prefix: str
    scopes: str
    is_active: bool
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime


class ApiTokenCreated(ApiTokenRead):
    """Resposta de criacao com o token uma unica vez."""

    token: str


# --------------------------------------------------------------------------- #
# Pastas de midia
# --------------------------------------------------------------------------- #
class FolderCreate(BaseModel):
    """Payload de criacao de pasta de midia."""

    name: str = Field(..., max_length=255)
    parent_id: int | None = None


class FolderUpdate(BaseModel):
    """Atualizacao parcial de pasta."""

    name: str | None = Field(None, max_length=255)
    parent_id: int | None = None


class FolderRead(BaseModel):
    """Representacao de uma pasta de midia."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None = None
    created_at: datetime


# --------------------------------------------------------------------------- #
# Media
# --------------------------------------------------------------------------- #
class MediaBase(BaseModel):
    """Campos comuns de midia compartilhados entre criacao e leitura."""

    name: str = Field(..., max_length=255, description="Nome amigavel da midia.")
    type: MediaType = Field(..., description="Tipo da midia.")
    source_url: str | None = Field(None, description="URL de origem (tipo 'url').")
    content: str | None = Field(
        None, description="Conteudo textual/HTML ou config JSON de widget."
    )
    tags: list[str] = Field(default_factory=list, description="Tags livres.")
    folder_id: int | None = Field(None, description="Pasta da midia.")
    expires_at: datetime | None = Field(None, description="Expira em; apos isso nao e exibida (P3).")
    collect_stats: bool = Field(True, description="Coletar proof-of-play desta midia (P7).")

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class MediaCreate(MediaBase):
    """Payload para criar midia sem arquivo (texto, html, url, youtube, widgets)."""


class MediaUpdate(BaseModel):
    """Campos opcionais para atualizacao parcial de midia."""

    name: str | None = Field(None, max_length=255)
    source_url: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    folder_id: int | None = None
    expires_at: datetime | None = None
    collect_stats: bool | None = None

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class MediaRead(MediaBase):
    """Representacao de midia retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str | None = None
    width: int | None = None
    height: int | None = None
    optimized_path: str | None = None
    poster_path: str | None = None
    processing_status: str = "skipped"
    processing_note: str | None = None
    created_at: datetime


class BulkUrlItem(BaseModel):
    """Item de importacao em massa de midia (texto/url/embed/youtube)."""

    name: str = Field(..., max_length=255)
    type: MediaType
    source_url: str | None = None
    content: str | None = None
    tags: list[str] = Field(default_factory=list)
    folder_id: int | None = None
    expires_at: datetime | None = None

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class BulkUrlRequest(BaseModel):
    """Payload de importacao em massa."""

    items: list[BulkUrlItem] = Field(..., max_length=500)


# --------------------------------------------------------------------------- #
# PlaylistItem
# --------------------------------------------------------------------------- #
class PlaylistItemCreate(BaseModel):
    """Payload para adicionar um item a uma playlist."""

    media_id: int = Field(..., description="ID da midia referenciada.")
    duration: int = Field(10, ge=1, le=86400, description="Tempo de exibicao (s).")
    position: int | None = Field(None, description="Posicao; ao final se omitido.")
    fit: FitMode = Field(FitMode.contain, description="Modo de ajuste a zona.")
    focal: str = Field("center", max_length=16, description="Ponto focal do recorte (cover).")
    transition: Transition = Field(Transition.fade, description="Efeito de entrada.")
    muted: bool = Field(True, description="True silencia (recomendado p/ autoplay).")
    play_full: bool = Field(False, description="Tocar a midia inteira (video/audio/YouTube).")
    start_at: datetime | None = Field(None, description="Inicio da validade do item (P3).")
    end_at: datetime | None = Field(None, description="Fim da validade do item (P3).")
    max_plays_per_hour: int | None = Field(None, ge=1, le=10000, description="Limite de exibicoes por hora (P6).")


class PlaylistItemUpdate(BaseModel):
    """Campos opcionais para atualizar um item da playlist."""

    duration: int | None = Field(None, ge=1, le=86400)
    position: int | None = None
    fit: FitMode | None = None
    focal: str | None = Field(None, max_length=16)
    transition: Transition | None = None
    muted: bool | None = None
    play_full: bool | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    max_plays_per_hour: int | None = Field(None, ge=1, le=10000)


class PlaylistItemRead(BaseModel):
    """Item de playlist com a midia associada embutida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: int
    position: int
    duration: int
    fit: FitMode
    focal: str = "center"
    transition: Transition
    muted: bool
    play_full: bool = False
    start_at: datetime | None = None
    end_at: datetime | None = None
    max_plays_per_hour: int | None = None
    media: MediaRead


# --------------------------------------------------------------------------- #
# Playlist
# --------------------------------------------------------------------------- #
class PlaylistCreate(BaseModel):
    """Payload para criar uma playlist."""

    name: str = Field(..., max_length=255)
    tags: list[str] = Field(default_factory=list, description="Tags livres.")
    folder_id: int | None = Field(None, description="Pasta da playlist.")

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class PlaylistUpdate(BaseModel):
    """Payload para atualizar uma playlist."""

    name: str | None = Field(None, max_length=255)
    tags: list[str] | None = None
    folder_id: int | None = None

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class PlaylistRead(BaseModel):
    """Representacao completa de uma playlist, com seus itens ordenados."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tags: list[str] = []
    folder_id: int | None = None
    created_at: datetime
    updated_at: datetime
    items: list[PlaylistItemRead] = []

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


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
        "0,1,2,3,4,5,6", description="Dias da semana (CSV, 0=segunda ... 6=domingo)."
    )
    start_minute: int = Field(0, ge=0, le=1440, description="Inicio (min do dia).")
    end_minute: int = Field(1440, ge=0, le=1440, description="Fim (min do dia).")
    priority: int = Field(0, description="Maior vence em caso de sobreposicao.")
    start_date: date | None = Field(None, description="Inicio da campanha (opcional).")
    end_date: date | None = Field(None, description="Fim da campanha (opcional).")

    @model_validator(mode="after")
    def _check_ranges(self) -> "ScheduleBase":
        """Valida coerencia das faixas de horario e de datas."""
        if self.end_minute <= self.start_minute:
            raise ValueError("end_minute deve ser maior que start_minute.")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date nao pode ser anterior a start_date.")
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
        """Valida faixas quando ambos os limites sao informados."""
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
            raise ValueError("end_date nao pode ser anterior a start_date.")
        return self


class ScheduleRead(ScheduleBase):
    """Representacao de um agendamento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_id: int


# --------------------------------------------------------------------------- #
# Zone
# --------------------------------------------------------------------------- #
class ZoneBase(BaseModel):
    """Geometria e playlist padrao de uma zona (valores em % da tela)."""

    name: str = Field("Zona", max_length=255)
    x: float = Field(0.0, ge=0, le=100)
    y: float = Field(0.0, ge=0, le=100)
    width: float = Field(100.0, ge=1, le=100)
    height: float = Field(100.0, ge=1, le=100)
    z_index: int = Field(0)
    default_playlist_id: int | None = Field(
        None, description="Playlist exibida fora de qualquer agendamento."
    )
    bg_color: str | None = Field(None, max_length=32, description="Cor de fundo da zona; 'transparent' mostra o fundo da tela. Nulo = preto.")
    opacity: float = Field(1.0, ge=0.1, le=1.0)
    radius: float = Field(0.0, ge=0, le=50, description="Cantos arredondados (% do menor lado).")
    padding: float = Field(0.0, ge=0, le=40, description="Espacamento interno (% do menor lado).")
    border_width: float = Field(0.0, ge=0, le=20, description="Espessura da borda em px.")
    border_color: str | None = Field(None, max_length=32)
    font_family: str | None = Field(None, max_length=120, description="Fonte CSS do conteudo de texto da zona.")


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
    bg_color: str | None = Field(None, max_length=32)
    opacity: float | None = Field(None, ge=0.1, le=1.0)
    radius: float | None = Field(None, ge=0, le=50)
    padding: float | None = Field(None, ge=0, le=40)
    border_width: float | None = Field(None, ge=0, le=20)
    border_color: str | None = Field(None, max_length=32)
    font_family: str | None = Field(None, max_length=120)


class ZoneRead(ZoneBase):
    """Representacao de uma zona, com seus agendamentos."""

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
    template: str | None = Field(
        None, description="Template de layout (ex.: restaurante, recepcao, varejo)."
    )
    sync_group: str | None = Field(None, max_length=64, description="Grupo de sincronia.")
    tags: list[str] = Field(default_factory=list, description="Tags livres para grupos dinamicos.")
    location_label: str | None = Field(None, max_length=255)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    resolution: str | None = Field(None, max_length=16, description="Resolucao nativa, ex.: 1920x1080.")
    orientation: str = Field("landscape", description="landscape ou portrait.")
    size_inches: str | None = Field(None, max_length=8, description="Tamanho diagonal em polegadas.")
    publish_status: str = Field("published", pattern="^(draft|published)$")
    publish_at: datetime | None = None
    layout_locked: bool = False
    collect_stats: bool = True

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class ScreenUpdate(BaseModel):
    """Campos opcionais para atualizar uma tela."""

    name: str | None = Field(None, max_length=255)
    timezone: str | None = None
    sync_group: str | None = Field(None, max_length=64)
    tags: list[str] | None = None
    location_label: str | None = Field(None, max_length=255)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    background_audio_id: int | None = Field(
        None, description="Midia de audio (tela inteira) tocada em loop."
    )
    resolution: str | None = Field(None, max_length=16)
    orientation: str | None = Field(None)
    size_inches: str | None = Field(None, max_length=8)
    theme_bg: str | None = Field(None, max_length=16)
    theme_text: str | None = Field(None, max_length=16)
    theme_accent: str | None = Field(None, max_length=16)
    theme_ticker_bg: str | None = Field(None, max_length=16)
    theme_ticker_text: str | None = Field(None, max_length=16)
    theme_font: str | None = Field(None, max_length=120)
    background_mode: str | None = Field(None, pattern="^(color|image|transparent)$")
    background_image_id: int | None = Field(None)
    background_fit: str | None = Field(None, pattern="^(cover|contain|fill|tile)$")
    publish_status: str | None = Field(None, pattern="^(draft|published)$")
    publish_at: datetime | None = None
    layout_locked: bool | None = None
    collect_stats: bool | None = None

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class ScreenRead(BaseModel):
    """Representacao de uma tela retornada pela API, com suas zonas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    pair_code: str | None = None
    sync_group: str | None = None
    tags: list[str] = []
    location_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    resolution: str | None = None
    orientation: str = "landscape"
    size_inches: str | None = None
    publish_status: str = "published"
    publish_at: datetime | None = None
    published_at: datetime | None = None
    layout_locked: bool = False
    collect_stats: bool = True
    timezone: str
    created_at: datetime
    last_seen: datetime | None = None
    background_audio_id: int | None = None
    theme_bg: str | None = None
    theme_text: str | None = None
    theme_accent: str | None = None
    theme_ticker_bg: str | None = None
    theme_ticker_text: str | None = None
    theme_font: str | None = None
    background_mode: str = "color"
    background_image_id: int | None = None
    background_fit: str = "cover"
    zones: list[ZoneRead] = []
    overlays: list[OverlayRead] = []

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class ScreenHealth(BaseModel):
    """Estado de saude/disponibilidade de uma tela."""

    id: int
    name: str
    slug: str
    last_seen: datetime | None = None
    online: bool = Field(..., description="True se vista recentemente.")
    connected_players: int = Field(0, description="Players conectados via WebSocket.")
    seconds_since_seen: int | None = None
    tags: list[str] = []
    location_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    sync_group: str | None = None
    open_commands: int = 0

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class TemplateInfo(BaseModel):
    """Descricao de um template de tela disponivel."""

    key: str
    name: str
    description: str
    zones: int


class PairRequest(BaseModel):
    """Emparelhamento de uma TV por codigo numerico."""

    code: str = Field(..., min_length=4, max_length=12)


class PairResponse(BaseModel):
    """Resposta do emparelhamento com o slug/URL do player."""

    slug: str
    name: str


# --------------------------------------------------------------------------- #
# Overlay (HUD)
# --------------------------------------------------------------------------- #
class MediaCueBase(BaseModel):
    """Campos comuns de um cue point sincronizado ao video (L3)."""

    at_seconds: float = Field(0.0, ge=0, le=86400)
    action: str = Field("show_gfx", max_length=16)
    kind: str = Field("lowerthird", max_length=16)
    content: str | None = None
    target_id: int | None = None
    slot_id: str = Field("cue", max_length=32)
    anchor: str = Field("lower_third", max_length=16)
    enter_anim: AnimKind = "slide"
    exit_anim: AnimKind = "fade"
    duration: float = Field(0.0, ge=0, le=86400)
    enabled: bool = True


class MediaCueCreate(MediaCueBase):
    """Payload de criacao de cue point."""


class MediaCueUpdate(BaseModel):
    """Campos opcionais para atualizar um cue point."""

    at_seconds: float | None = Field(None, ge=0, le=86400)
    action: str | None = Field(None, max_length=16)
    kind: str | None = Field(None, max_length=16)
    content: str | None = None
    target_id: int | None = None
    slot_id: str | None = Field(None, max_length=32)
    anchor: str | None = Field(None, max_length=16)
    enter_anim: AnimKind | None = None
    exit_anim: AnimKind | None = None
    duration: float | None = Field(None, ge=0, le=86400)
    enabled: bool | None = None


class MediaCueRead(MediaCueBase):
    """Cue point retornado pela API."""

    id: int
    media_id: int

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Ad-breaks recorrentes/agendados (L6)
# --------------------------------------------------------------------------- #
class AdBreakScheduleBase(BaseModel):
    """Campos comuns de um ad-break recorrente/agendado (L6)."""

    name: str = Field("Ad-break", max_length=120)
    screen_id: int | None = None
    media_id: int | None = None
    every_minutes: int = Field(15, ge=1, le=1440)
    duration_seconds: int = Field(15, ge=1, le=86400)
    start_time: str = Field("00:00", max_length=5)
    end_time: str = Field("23:59", max_length=5)
    days: str = Field("0123456", max_length=16)
    enter_anim: AnimKind = "fade"
    exit_anim: AnimKind = "fade"
    enabled: bool = True

    @field_validator("start_time", "end_time")
    @classmethod
    def _valid_hhmm(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"[0-2]?\d:[0-5]\d", v or ""):
            raise ValueError("Horario deve estar no formato HH:MM.")
        h, m = v.split(":")
        if int(h) > 23:
            raise ValueError("Hora invalida (0-23).")
        return f"{int(h):02d}:{m}"

    @field_validator("days")
    @classmethod
    def _valid_days(cls, v: str) -> str:
        cleaned = "".join(sorted({c for c in (v or "") if c in "0123456"}))
        return cleaned or "0123456"


class AdBreakScheduleCreate(AdBreakScheduleBase):
    """Payload de criacao de ad-break agendado."""


class AdBreakScheduleUpdate(BaseModel):
    """Campos opcionais para atualizar um ad-break agendado."""

    name: str | None = Field(None, max_length=120)
    screen_id: int | None = None
    media_id: int | None = None
    every_minutes: int | None = Field(None, ge=1, le=1440)
    duration_seconds: int | None = Field(None, ge=1, le=86400)
    start_time: str | None = Field(None, max_length=5)
    end_time: str | None = Field(None, max_length=5)
    days: str | None = Field(None, max_length=16)
    enter_anim: AnimKind | None = None
    exit_anim: AnimKind | None = None
    enabled: bool | None = None


class AdBreakScheduleRead(AdBreakScheduleBase):
    """Ad-break agendado retornado pela API."""

    id: int
    company_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class OverlayBase(BaseModel):
    """Campos comuns de um overlay (widget sobreposto estilo HUD)."""

    name: str = Field("Overlay", max_length=255)
    kind: str = Field("clock", max_length=16)
    content: str | None = None
    position: str = Field("bottom", max_length=16)
    width: float = Field(0.0, ge=0, le=100)
    height: float = Field(0.0, ge=0, le=100)
    mode: str = Field("fixed", max_length=8)
    interval_seconds: int = Field(300, ge=1, le=86400)
    visible_seconds: int = Field(15, ge=1, le=86400)
    opacity: float = Field(1.0, ge=0.1, le=1.0)
    z_index: int = Field(50)
    enabled: bool = True
    # --- L1: Live Graphics --- #
    # Ancora de posicionamento (vazio => usa `position`). Aceita as nove
    # posicoes classicas mais `lower_third` e `fullscreen`.
    anchor: str = Field("", max_length=16)
    # Margem de area segura, em vmin.
    margin: float = Field(2.0, ge=0, le=40)
    # Animacao de entrada/saida.
    enter_anim: AnimKind = "fade"
    exit_anim: AnimKind = "fade"
    # Janela de tempo (modo "timed"). 0 nos campos abaixo => usa o legado.
    enter_at: float = Field(0.0, ge=0, le=86400)
    duration: float = Field(0.0, ge=0, le=86400)
    repeat_every: float = Field(0.0, ge=0, le=86400)


class OverlayCreate(OverlayBase):
    """Payload de criacao de overlay."""


class OverlayUpdate(BaseModel):
    """Campos opcionais para atualizar um overlay."""

    name: str | None = Field(None, max_length=255)
    kind: str | None = Field(None, max_length=16)
    content: str | None = None
    position: str | None = Field(None, max_length=16)
    width: float | None = Field(None, ge=0, le=100)
    height: float | None = Field(None, ge=0, le=100)
    mode: str | None = Field(None, max_length=8)
    interval_seconds: int | None = Field(None, ge=1, le=86400)
    visible_seconds: int | None = Field(None, ge=1, le=86400)
    opacity: float | None = Field(None, ge=0.1, le=1.0)
    z_index: int | None = None
    enabled: bool | None = None
    # --- L1: Live Graphics --- #
    anchor: str | None = Field(None, max_length=16)
    margin: float | None = Field(None, ge=0, le=40)
    enter_anim: AnimKind | None = None
    exit_anim: AnimKind | None = None
    enter_at: float | None = Field(None, ge=0, le=86400)
    duration: float | None = Field(None, ge=0, le=86400)
    repeat_every: float | None = Field(None, ge=0, le=86400)


class OverlayRead(OverlayBase):
    """Overlay retornado pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# --------------------------------------------------------------------------- #
# Display (payload consumido pelo player)
# --------------------------------------------------------------------------- #
class DisplayItem(BaseModel):
    """Item ja resolvido para reproducao no player."""

    media_id: int | None = None
    type: MediaType
    duration: int
    name: str
    fit: FitMode
    focal: str = "center"
    transition: Transition
    muted: bool = True
    play_full: bool = False
    url: str | None = None
    poster: str | None = None
    content: str | None = None
    # L3: cue points (disparos sincronizados ao tempo do video).
    cues: list["DisplayCue"] = []


class DisplayCue(BaseModel):
    """Cue point resolvido para o player (disparo por tempo de video, L3)."""

    at_seconds: float
    action: str
    kind: str = "lowerthird"
    content: str | None = None
    target_id: int | None = None
    slot_id: str = "cue"
    anchor: str = "lower_third"
    enter_anim: str = "slide"
    exit_anim: str = "fade"
    duration: float = 0.0
    # L5 (ad-break): URL/poster da midia de anuncio resolvida no backend.
    url: str | None = None
    poster: str | None = None


class DisplayAdBreak(BaseModel):
    """Ad-break recorrente resolvido para o player (disparo por relogio, L6)."""

    name: str = "Ad-break"
    media_id: int | None = None
    kind: str = "image"
    url: str | None = None
    poster: str | None = None
    every_minutes: int = 15
    duration_seconds: int = 15
    start_time: str = "00:00"
    end_time: str = "23:59"
    days: str = "0123456"
    enter_anim: str = "fade"
    exit_anim: str = "fade"


class DisplayZone(BaseModel):
    """Zona resolvida (geometria + itens da playlist ativa no momento)."""

    id: int
    name: str
    x: float
    y: float
    width: float
    height: float
    z_index: int
    bg_color: str | None = None
    opacity: float = 1.0
    radius: float = 0.0
    padding: float = 0.0
    border_width: float = 0.0
    border_color: str | None = None
    font_family: str | None = None
    playlist_name: str | None = None
    items: list[DisplayItem] = []


class DisplayOverlay(BaseModel):
    """Overlay resolvido para o player (HUD)."""

    id: int
    kind: str
    content: str | None = None
    position: str = "bottom"
    width: float = 0.0
    height: float = 0.0
    mode: str = "fixed"
    interval_seconds: int = 300
    visible_seconds: int = 15
    opacity: float = 1.0
    z_index: int = 50
    # --- L1: Live Graphics --- #
    anchor: str = ""
    margin: float = 2.0
    enter_anim: str = "fade"
    exit_anim: str = "fade"
    enter_at: float = 0.0
    duration: float = 0.0
    repeat_every: float = 0.0


class DisplayPayload(BaseModel):
    """Conteudo completo que o player precisa para reproduzir uma tela."""

    screen: str
    revision: str
    theme: dict | None = None
    zones: list[DisplayZone] = []
    overlays: list[DisplayOverlay] = []
    # L6: ad-breaks recorrentes/agendados disparados por relogio no player.
    ad_breaks: list[DisplayAdBreak] = []
    background: dict | None = None
    background_audio: str | None = None
    emergency_message: str | None = None


# --------------------------------------------------------------------------- #
# Proof-of-play e auditoria
# --------------------------------------------------------------------------- #
class PlayEventCreate(BaseModel):
    """Evento de reproducao reportado pelo player."""

    media_id: int | None = None
    zone_id: int | None = None
    media_name: str = Field("", max_length=255)
    media_type: str = Field("", max_length=32)
    duration_seconds: int = Field(0, ge=0, le=86400)
    # L5: indica que o evento e a exibicao de um anuncio (ad-break).
    is_ad: bool = False


class PlayEventBatch(BaseModel):
    """Lote de eventos de reproducao (o player agrega antes de enviar)."""

    events: list[PlayEventCreate] = Field(..., max_length=500)


class ProofOfPlayRow(BaseModel):
    """Linha agregada de proof-of-play."""

    media_id: int | None = None
    media_name: str
    plays: int
    total_seconds: int


class ProofOfPlayDetailRow(BaseModel):
    """Linha detalhada para BI/exportacao."""

    played_at: datetime
    screen_slug: str
    zone_id: int | None = None
    media_id: int | None = None
    media_name: str
    media_type: str
    duration_seconds: int


class ProofOfPlaySummary(BaseModel):
    """Resumo executivo do proof-of-play."""

    total_plays: int = 0
    total_seconds: int = 0
    unique_media: int = 0
    unique_screens: int = 0


class ReportScheduleCreate(BaseModel):
    """Cria um relatorio agendado por e-mail."""

    name: str = Field(..., min_length=2, max_length=255)
    recipients: str = Field(..., min_length=3, max_length=2000)
    frequency: str = Field("daily", pattern="^(daily|weekly)$")
    hour: int = Field(8, ge=0, le=23)
    days: int = Field(7, ge=1, le=365)
    screen_slug: str | None = Field(None, max_length=32)
    enabled: bool = True


class ReportScheduleUpdate(BaseModel):
    """Atualiza relatorio agendado."""

    name: str | None = Field(None, min_length=2, max_length=255)
    recipients: str | None = Field(None, min_length=3, max_length=2000)
    frequency: str | None = Field(None, pattern="^(daily|weekly)$")
    hour: int | None = Field(None, ge=0, le=23)
    days: int | None = Field(None, ge=1, le=365)
    screen_slug: str | None = Field(None, max_length=32)
    enabled: bool | None = None


class ReportScheduleRead(ReportScheduleCreate):
    """Relatorio agendado retornado pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    last_sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AuditLogRead(BaseModel):
    """Representacao de um registro de auditoria."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str | None = None
    detail: str | None = None
    created_at: datetime


# --------------------------------------------------------------------------- #
# P3: biblioteca (upload por URL, limpeza) e import/export de playlists
# --------------------------------------------------------------------------- #
class MediaUrlImport(BaseModel):
    """Payload para baixar um arquivo (imagem/video/audio) a partir de uma URL."""

    name: str = Field(..., max_length=255, description="Nome amigavel da midia.")
    url: str = Field(..., description="URL http(s) do arquivo a baixar.")
    folder_id: int | None = Field(None, description="Pasta de destino.")
    tags: list[str] = Field(default_factory=list, description="Tags livres.")
    expires_at: datetime | None = Field(None, description="Expira em; apos isso nao e exibida.")

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class PurgeResult(BaseModel):
    """Resultado da limpeza de midias nao utilizadas."""

    deleted: int = Field(..., description="Quantidade de midias removidas.")
    ids: list[int] = Field(default_factory=list, description="IDs removidos.")


class BulkTagRequest(BaseModel):
    """Adiciona tags a varios registros de uma vez."""

    ids: list[int] = Field(..., min_length=1, max_length=500)
    tags: list[str] = Field(..., min_length=1, max_length=50)

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class BulkActionResult(BaseModel):
    """Resultado de uma acao em massa."""

    updated: int = Field(..., description="Quantidade de registros alterados.")
    ids: list[int] = Field(default_factory=list, description="IDs processados.")


class PlaylistImportItem(BaseModel):
    """Item de uma playlist exportada/importada (midia embutida por metadados)."""

    duration: int = Field(10, ge=1, le=86400)
    fit: FitMode = FitMode.contain
    focal: str = Field("center", max_length=16)
    transition: Transition = Transition.fade
    muted: bool = True
    play_full: bool = False
    start_at: datetime | None = None
    end_at: datetime | None = None
    media_name: str = Field(..., max_length=255)
    media_type: MediaType
    source_url: str | None = None
    content: str | None = None
    tags: list[str] = Field(default_factory=list)

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class PlaylistImport(BaseModel):
    """Playlist completa para importacao (formato simetrico ao export)."""

    name: str = Field(..., max_length=255)
    tags: list[str] = Field(default_factory=list)
    folder_id: int | None = None
    items: list[PlaylistImportItem] = Field(default_factory=list, max_length=2000)

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class LayoutZoneImport(BaseModel):
    """Zona de um layout exportado/importado."""

    name: str = Field("Zona", max_length=255)
    x: float = Field(0.0, ge=0, le=100)
    y: float = Field(0.0, ge=0, le=100)
    width: float = Field(100.0, ge=1, le=100)
    height: float = Field(100.0, ge=1, le=100)
    z_index: int = 0
    default_playlist_name: str | None = None


class LayoutOverlayImport(BaseModel):
    """Overlay de um layout exportado/importado."""

    name: str = Field("Overlay", max_length=255)
    kind: str = Field("clock", max_length=16)
    content: str | None = None
    position: str = Field("bottom", max_length=16)
    width: float = Field(0.0, ge=0, le=100)
    height: float = Field(0.0, ge=0, le=100)
    mode: str = Field("fixed", max_length=8)
    interval_seconds: int = Field(300, ge=1, le=86400)
    visible_seconds: int = Field(15, ge=1, le=86400)
    opacity: float = Field(1.0, ge=0.1, le=1.0)
    z_index: int = 50
    enabled: bool = True


class LayoutImport(BaseModel):
    """Layout de tela para import/export sem conteudo binario."""

    version: int = 1
    name: str | None = Field(None, max_length=255)
    timezone: str | None = None
    sync_group: str | None = Field(None, max_length=64)
    resolution: str | None = Field(None, max_length=16)
    orientation: str | None = None
    size_inches: str | None = Field(None, max_length=8)
    theme_bg: str | None = Field(None, max_length=16)
    theme_text: str | None = Field(None, max_length=16)
    theme_accent: str | None = Field(None, max_length=16)
    theme_ticker_bg: str | None = Field(None, max_length=16)
    theme_ticker_text: str | None = Field(None, max_length=16)
    zones: list[LayoutZoneImport] = Field(default_factory=list, min_length=1, max_length=100)
    overlays: list[LayoutOverlayImport] = Field(default_factory=list, max_length=100)


# --------------------------------------------------------------------------- #
# P4: gestao de telas em escala
# --------------------------------------------------------------------------- #
class ScreenGroupCreate(BaseModel):
    """Grupo de telas estatico ou dinamico por tags."""

    name: str = Field(..., min_length=2, max_length=255)
    mode: str = Field("static", pattern="^(static|dynamic)$")
    screen_ids: list[int] = Field(default_factory=list, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=50)
    sync_group: str | None = Field(None, max_length=64)

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class ScreenGroupUpdate(BaseModel):
    """Atualizacao parcial de grupo de telas."""

    name: str | None = Field(None, min_length=2, max_length=255)
    mode: str | None = Field(None, pattern="^(static|dynamic)$")
    screen_ids: list[int] | None = Field(None, max_length=500)
    tags: list[str] | None = Field(None, max_length=50)
    sync_group: str | None = Field(None, max_length=64)

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)


class ScreenGroupRead(BaseModel):
    """Grupo de telas com quantidade resolvida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mode: str
    screen_ids: list[int] = []
    tags: list[str] = []
    sync_group: str | None = None
    screen_count: int = 0
    created_at: datetime

    _normalize_tags = field_validator("tags", mode="before")(_split_tags)
    _normalize_screen_ids = field_validator("screen_ids", mode="before")(_split_ints)


class PlayerCommandCreate(BaseModel):
    """Comando solicitado ao player/hardware."""

    command_type: str = Field(..., pattern="^(screenshot|reload|identify|power|volume|brightness|cec|shell|rs232|live_gfx|live_clear|takeover|takeover_clear)$")
    payload: dict | None = None


class PlayerCommandRead(BaseModel):
    """Comando do player retornado pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    screen_id: int
    command_type: str
    payload: dict | None = None
    status: str
    result: str | None = None
    result_path: str | None = None
    requested_by: str | None = None
    created_at: datetime
    sent_at: datetime | None = None
    completed_at: datetime | None = None

    _normalize_payload = field_validator("payload", mode="before")(_parse_json_dict)


class PlayerCommandResult(BaseModel):
    """Resultado reportado pelo player apos executar um comando."""

    status: str = Field("done", pattern="^(done|failed|unsupported)$")
    result: str | None = Field(None, max_length=4000)
    data_url: str | None = Field(None, description="Imagem data URL para screenshot.")


# --------------------------------------------------------------------------- #
# L4: Mesa de transmissao (disparo de graficos ao vivo)
# --------------------------------------------------------------------------- #
class LiveGfxTrigger(BaseModel):
    """Disparo de um grafico ao vivo (lower-third, banner, HUD) em uma tela.

    Reaproveita os tipos de widget de overlay (``text``, ``news``, ``promo``,
    ``clock`` etc.) e os mesmos atributos de posicionamento/animacao da fase
    L1. O player aplica o grafico instantaneamente, sem recarregar a playlist.

    Attributes:
        kind: tipo de widget/grafico a renderizar.
        content: texto (para ``text``) ou JSON de configuracao do widget.
        name: rotulo opcional para exibicao/log.
        slot_id: identificador logico do grafico; permite limpar um especifico.
        anchor: ancora de posicionamento (ver L1).
        enter_anim/exit_anim: animacoes de entrada/saida.
        margin: margem de area segura (vmin).
        duration: segundos visivel; ``0`` mantem ate o operador limpar.
        width/height: tamanho em % da tela (``0`` = automatico).
        opacity: opacidade do grafico (0.1-1).
        z_index: camada de empilhamento.
    """

    kind: str = Field("text", max_length=32)
    content: str = Field("", max_length=8000)
    name: str | None = Field(None, max_length=120)
    slot_id: str | None = Field(None, max_length=48)
    anchor: str = Field("lower_third", max_length=16)
    enter_anim: AnimKind = "slide"
    exit_anim: AnimKind = "fade"
    margin: float = Field(2.0, ge=0, le=40)
    duration: float = Field(0.0, ge=0, le=86400)
    width: float = Field(0.0, ge=0, le=100)
    height: float = Field(0.0, ge=0, le=100)
    opacity: float = Field(1.0, ge=0.1, le=1)
    z_index: int = Field(9500, ge=0, le=99999)


class LiveClear(BaseModel):
    """Limpa graficos ao vivo de uma tela.

    Attributes:
        slot_id: se informado, limpa apenas o grafico desse slot; caso
            contrario, limpa todos os graficos ao vivo da tela.
    """

    slot_id: str | None = Field(None, max_length=48)


class LiveTakeover(BaseModel):
    """Tomada de tela (full-screen) com mensagem destacada (ex.: ULTIMA HORA).

    Attributes:
        title: titulo em destaque (ex.: ``ULTIMA HORA``).
        subtitle: linha de apoio opcional.
        color: cor de fundo/realce (hex ou nome CSS).
        enter_anim/exit_anim: animacoes de entrada/saida.
        duration: segundos visivel; ``0`` mantem ate limpar.
    """

    title: str = Field(..., max_length=200)
    subtitle: str | None = Field(None, max_length=400)
    color: str = Field("#b91c1c", max_length=32)
    enter_anim: AnimKind = "fade"
    exit_anim: AnimKind = "fade"
    duration: float = Field(0.0, ge=0, le=86400)


class ScreenMapItem(ScreenHealth):
    """Item de mapa/lista de telas com dados operacionais."""

    group_names: list[str] = []


# --------------------------------------------------------------------------- #
# P6: publicacao, trava de layout e campanhas
# --------------------------------------------------------------------------- #
class ScreenPublishRequest(BaseModel):
    """Publica imediatamente ou agenda publicacao de uma tela."""

    publish_at: datetime | None = None


class CampaignBase(BaseModel):
    """Campanha de playlist para telas/grupos/zonas."""

    name: str = Field(..., min_length=2, max_length=255)
    playlist_id: int
    mode: str = Field("scheduled", pattern="^(scheduled|interrupt)$")
    screen_ids: list[int] = Field(default_factory=list, max_length=500)
    screen_group_ids: list[int] = Field(default_factory=list, max_length=100)
    zone_ids: list[int] = Field(default_factory=list, max_length=1000)
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: int = 0
    # L5: peso da rotacao ponderada entre campanhas empatadas em prioridade.
    weight: int = Field(1, ge=0, le=1000)
    enabled: bool = True
    max_plays_per_hour: int | None = Field(None, ge=1, le=10000)

    @model_validator(mode="after")
    def _check_window(self) -> "CampaignBase":
        if self.start_at is not None and self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("end_at nao pode ser anterior a start_at.")
        return self


class CampaignCreate(CampaignBase):
    """Payload de criacao de campanha."""


class CampaignUpdate(BaseModel):
    """Atualizacao parcial de campanha."""

    name: str | None = Field(None, min_length=2, max_length=255)
    playlist_id: int | None = None
    mode: str | None = Field(None, pattern="^(scheduled|interrupt)$")
    screen_ids: list[int] | None = Field(None, max_length=500)
    screen_group_ids: list[int] | None = Field(None, max_length=100)
    zone_ids: list[int] | None = Field(None, max_length=1000)
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: int | None = None
    weight: int | None = Field(None, ge=0, le=1000)
    enabled: bool | None = None
    max_plays_per_hour: int | None = Field(None, ge=1, le=10000)

    @model_validator(mode="after")
    def _check_window(self) -> "CampaignUpdate":
        if self.start_at is not None and self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("end_at nao pode ser anterior a start_at.")
        return self


class CampaignRead(CampaignBase):
    """Campanha retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    _normalize_screen_ids = field_validator("screen_ids", mode="before")(_split_ints)
    _normalize_group_ids = field_validator("screen_group_ids", mode="before")(_split_ints)
    _normalize_zone_ids = field_validator("zone_ids", mode="before")(_split_ints)


# --------------------------------------------------------------------------- #
# P5: widgets avancados e DataSets
# --------------------------------------------------------------------------- #
class DataSetBase(BaseModel):
    """Fonte de dados tabular/JSON usada por widgets dinamicos."""

    name: str = Field(..., min_length=2, max_length=255)
    kind: str = Field("table", pattern="^(table|csv|json_remote)$")
    source_url: str | None = Field(None, max_length=1024)
    columns: list[dict] = Field(default_factory=list, max_length=100)
    rows: list[dict] = Field(default_factory=list, max_length=5000)
    fallback_rows: list[dict] = Field(default_factory=list, max_length=5000)
    expires_at: datetime | None = None

    _normalize_columns = field_validator("columns", mode="before")(_parse_json_list)
    _normalize_rows = field_validator("rows", mode="before")(_parse_json_list)
    _normalize_fallback = field_validator("fallback_rows", mode="before")(_parse_json_list)


class DataSetCreate(DataSetBase):
    """Payload de criacao de DataSet."""


class DataSetUpdate(BaseModel):
    """Atualizacao parcial de DataSet."""

    name: str | None = Field(None, min_length=2, max_length=255)
    kind: str | None = Field(None, pattern="^(table|csv|json_remote)$")
    source_url: str | None = Field(None, max_length=1024)
    columns: list[dict] | None = Field(None, max_length=100)
    rows: list[dict] | None = Field(None, max_length=5000)
    fallback_rows: list[dict] | None = Field(None, max_length=5000)
    expires_at: datetime | None = None

    _normalize_columns = field_validator("columns", mode="before")(_parse_json_list)
    _normalize_rows = field_validator("rows", mode="before")(_parse_json_list)
    _normalize_fallback = field_validator("fallback_rows", mode="before")(_parse_json_list)


class DataSetRead(DataSetBase):
    """Representacao de DataSet retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    refresh_status: str = "idle"
    refresh_note: str | None = None
    last_refresh_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class DataSetImportCsv(BaseModel):
    """CSV colado no painel para atualizar linhas de um DataSet."""

    csv_text: str = Field(..., min_length=1, max_length=1_000_000)
    delimiter: str = Field(",", min_length=1, max_length=1)


class DataSetPublic(BaseModel):
    """Payload publico consumido pelo player."""

    id: int
    name: str
    columns: list[dict] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    stale: bool = False
    refresh_status: str = "idle"
    refresh_note: str | None = None
