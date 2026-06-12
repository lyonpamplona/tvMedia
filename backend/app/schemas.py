"""Esquemas Pydantic para validação de entrada e serialização de saída.

Separar os esquemas (DTOs) dos modelos ORM mantém a fronteira da API explícita
e evita expor detalhes internos de persistência. Os sufixos seguem a convenção:

* ``*Create`` — payload de criação.
* ``*Update`` — payload de atualização parcial.
* ``*Read`` — representação retornada pela API.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import FitMode, MediaType, Transition


# --------------------------------------------------------------------------- #
# Autenticação
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    """Payload de login do painel."""

    password: str = Field(..., description="Senha do painel administrativo.")


class TokenResponse(BaseModel):
    """Resposta de login contendo o token de sessão assinado."""

    token: str
    expires_in: int = Field(..., description="Validade do token em segundos.")


# --------------------------------------------------------------------------- #
# Media
# --------------------------------------------------------------------------- #
class MediaBase(BaseModel):
    """Campos comuns de mídia compartilhados entre criação e leitura."""

    name: str = Field(..., max_length=255, description="Nome amigável da mídia.")
    type: MediaType = Field(..., description="Tipo da mídia.")
    source_url: str | None = Field(
        None, description="URL de origem (para o tipo 'url')."
    )
    content: str | None = Field(
        None, description="Conteúdo textual ou HTML (tipos 'text'/'html')."
    )


class MediaCreate(MediaBase):
    """Payload para criar mídia sem arquivo (texto, html ou url).

    Para imagens e vídeos use o endpoint de upload, que recebe o arquivo via
    ``multipart/form-data`` e preenche ``path`` automaticamente.
    """


class MediaUpdate(BaseModel):
    """Campos opcionais para atualização parcial de mídia."""

    name: str | None = Field(None, max_length=255)
    source_url: str | None = None
    content: str | None = None


class MediaRead(MediaBase):
    """Representação de mídia retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str | None = None
    created_at: datetime


# --------------------------------------------------------------------------- #
# PlaylistItem
# --------------------------------------------------------------------------- #
class PlaylistItemCreate(BaseModel):
    """Payload para adicionar um item a uma playlist."""

    media_id: int = Field(..., description="ID da mídia referenciada.")
    duration: int = Field(
        10, ge=1, le=86400, description="Tempo de exibição em segundos."
    )
    position: int | None = Field(
        None, description="Posição desejada; ao final se omitido."
    )
    fit: FitMode = Field(FitMode.contain, description="Modo de ajuste à zona.")
    transition: Transition = Field(
        Transition.fade, description="Efeito de entrada do item."
    )


class PlaylistItemUpdate(BaseModel):
    """Campos opcionais para atualizar um item da playlist."""

    duration: int | None = Field(None, ge=1, le=86400)
    position: int | None = None
    fit: FitMode | None = None
    transition: Transition | None = None


class PlaylistItemRead(BaseModel):
    """Item de playlist com a mídia associada embutida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: int
    position: int
    duration: int
    fit: FitMode
    transition: Transition
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

    item_ids: list[int] = Field(
        ..., description="IDs dos itens na nova ordem desejada."
    )


# --------------------------------------------------------------------------- #
# Schedule (agendamento)
# --------------------------------------------------------------------------- #
class ScheduleBase(BaseModel):
    """Campos de uma regra de agendamento de zona."""

    playlist_id: int = Field(..., description="Playlist exibida quando ativa.")
    days_of_week: str = Field(
        "0,1,2,3,4,5,6",
        description="Dias da semana (CSV, 0=segunda … 6=domingo).",
    )
    start_minute: int = Field(
        0, ge=0, le=1440, description="Início (minutos desde a meia-noite)."
    )
    end_minute: int = Field(
        1440, ge=0, le=1440, description="Fim (minutos desde a meia-noite)."
    )
    priority: int = Field(0, description="Maior vence em caso de sobreposição.")


class ScheduleCreate(ScheduleBase):
    """Payload para criar um agendamento."""


class ScheduleUpdate(BaseModel):
    """Campos opcionais para atualizar um agendamento."""

    playlist_id: int | None = None
    days_of_week: str | None = None
    start_minute: int | None = Field(None, ge=0, le=1440)
    end_minute: int | None = Field(None, ge=0, le=1440)
    priority: int | None = None


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
    """Payload para registrar uma nova tela.

    Por padrão, a tela é criada com uma única zona cobrindo 100% (modo
    simples). Use os endpoints de zona para criar layouts com múltiplas zonas.
    """

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


# --------------------------------------------------------------------------- #
# Display (payload consumido pelo player)
# --------------------------------------------------------------------------- #
class DisplayItem(BaseModel):
    """Item já resolvido para reprodução no player."""

    type: MediaType
    duration: int
    name: str
    fit: FitMode
    transition: Transition
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
