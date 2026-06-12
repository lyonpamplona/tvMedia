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

from .models import MediaType


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


class PlaylistItemUpdate(BaseModel):
    """Campos opcionais para atualizar um item da playlist."""

    duration: int | None = Field(None, ge=1, le=86400)
    position: int | None = None


class PlaylistItemRead(BaseModel):
    """Item de playlist com a mídia associada embutida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: int
    position: int
    duration: int
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
# Screen
# --------------------------------------------------------------------------- #
class ScreenCreate(BaseModel):
    """Payload para registrar uma nova tela."""

    name: str = Field(..., max_length=255)
    playlist_id: int | None = Field(
        None, description="Playlist inicial atribuída à tela."
    )


class ScreenUpdate(BaseModel):
    """Campos opcionais para atualizar uma tela."""

    name: str | None = Field(None, max_length=255)
    playlist_id: int | None = Field(None, description="Nova playlist (ou null).")


class ScreenRead(BaseModel):
    """Representação de uma tela retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    playlist_id: int | None = None
    created_at: datetime
    last_seen: datetime | None = None


# --------------------------------------------------------------------------- #
# Display (payload consumido pelo player)
# --------------------------------------------------------------------------- #
class DisplayItem(BaseModel):
    """Item já resolvido para reprodução no player."""

    type: MediaType
    duration: int
    name: str
    url: str | None = None
    content: str | None = None


class DisplayPayload(BaseModel):
    """Conteúdo completo que o player precisa para reproduzir uma tela."""

    screen: str
    playlist_name: str | None = None
    revision: str
    items: list[DisplayItem] = []
