"""Serviços de domínio reutilizáveis por mais de um roteador.

Concentra a montagem do *payload de exibição* (consumido tanto pelo player,
via ``/api/display/{slug}``, quanto pela pré-visualização do painel) e o
cálculo da ``revision`` (hash do conteúdo). Manter isso fora dos roteadores
evita duplicação e mantém uma única fonte da verdade.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from . import crud, models, schemas
from .embeds import build_embed_url


def media_url(base_url: str, media: models.Media) -> str | None:
    """Resolve a URL pública de uma mídia conforme o tipo.

    Args:
        base_url: base absoluta da requisição (ex.: ``http://host/``).
        media: mídia a resolver.

    Returns:
        str | None: URL absoluta do arquivo/origem, ou None para texto/HTML.
    """
    if media.type in (
        models.MediaType.image,
        models.MediaType.video,
        models.MediaType.audio,
    ):
        # Prefere a versao otimizada (reescalada/transcodificada) quando existir;
        # o original permanece como backup e e usado se nao houver otimizada.
        served = getattr(media, "optimized_path", None) or media.path
        if served:
            return base_url + f"media/{served}"
    if media.type == models.MediaType.url:
        return media.source_url
    return None


def now_in_timezone(tz_name: str) -> datetime:
    """Retorna o instante atual no fuso informado (com fallback para UTC)."""
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = timezone.utc
    return datetime.now(tz)


def build_zone_payload(
    base_url: str, db: Session, zone: models.Zone, now: datetime
) -> schemas.DisplayZone:
    """Monta o payload de uma zona resolvendo a playlist ativa no momento."""
    playlist_id = crud.resolve_active_playlist_id(zone, now)
    playlist = crud.get_playlist(db, playlist_id) if playlist_id else None

    items: list[schemas.DisplayItem] = []
    if playlist is not None:
        for item in sorted(playlist.items, key=lambda i: i.position):
            if item.media.type in (models.MediaType.youtube, models.MediaType.embed):
                resolved_url = build_embed_url(item.media, muted=item.muted)
            else:
                resolved_url = media_url(base_url, item.media)
            poster_url = None
            if getattr(item.media, "poster_path", None):
                poster_url = base_url + f"media/{item.media.poster_path}"
            items.append(
                schemas.DisplayItem(
                    media_id=item.media_id,
                    type=item.media.type,
                    duration=item.duration,
                    name=item.media.name,
                    fit=item.fit,
                    focal=getattr(item, "focal", "center") or "center",
                    transition=item.transition,
                    muted=item.muted,
                    url=resolved_url,
                    poster=poster_url,
                    content=item.media.content,
                )
            )

    return schemas.DisplayZone(
        id=zone.id,
        name=zone.name,
        x=zone.x,
        y=zone.y,
        width=zone.width,
        height=zone.height,
        z_index=zone.z_index,
        playlist_name=playlist.name if playlist else None,
        items=items,
    )


def compute_revision(payload: schemas.DisplayPayload) -> str:
    """Calcula um hash curto e estável do conteúdo (detecta mudanças)."""
    snapshot = payload.model_dump(exclude={"revision"})
    raw = repr(snapshot).encode()
    return hashlib.sha256(raw).hexdigest()[:12]


def build_display_payload(
    base_url: str, db: Session, screen: models.Screen
) -> schemas.DisplayPayload:
    """Monta o payload completo de uma tela (todas as zonas resolvidas).

    Args:
        base_url: base absoluta da requisição.
        db: sessão ativa.
        screen: tela com zonas e agendamentos carregados.

    Returns:
        schemas.DisplayPayload: conteúdo pronto para o player, com revision.
    """
    now = now_in_timezone(screen.timezone)
    zones = [
        build_zone_payload(base_url, db, zone, now)
        for zone in sorted(screen.zones, key=lambda z: z.z_index)
    ]
    background_audio = None
    if screen.background_audio_id is not None:
        audio_media = crud.get_media(db, screen.background_audio_id)
        if audio_media is not None:
            background_audio = media_url(base_url, audio_media)
    emergency_message = None
    if screen.company_id is not None:
        company = crud.get_company(db, screen.company_id)
        if company is not None and getattr(company, "emergency_active", False):
            emergency_message = company.emergency_message or None
    payload = schemas.DisplayPayload(
        screen=screen.slug,
        revision="",
        zones=zones,
        background_audio=background_audio,
        emergency_message=emergency_message,
    )
    payload.revision = compute_revision(payload)
    return payload
