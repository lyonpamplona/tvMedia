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


def _as_aware(dt: datetime | None) -> datetime | None:
    """Garante datetime com fuso (assume UTC quando ingenuo) para comparar."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def item_is_active(item: models.PlaylistItem, now: datetime) -> bool:
    """True se o item esta dentro da janela de validade (start_at/end_at)."""
    start = _as_aware(getattr(item, "start_at", None))
    end = _as_aware(getattr(item, "end_at", None))
    if start is not None and now < start:
        return False
    if end is not None and now > end:
        return False
    return True


def media_is_active(media: models.Media, now: datetime) -> bool:
    """True se a midia ainda nao expirou (expires_at)."""
    exp = _as_aware(getattr(media, "expires_at", None))
    if exp is not None and now > exp:
        return False
    return True


def _screen_is_published(screen: models.Screen, now: datetime) -> bool:
    """Tela aparece no player se publicada ou com publicacao agendada vencida."""
    if getattr(screen, "publish_status", "published") == "published":
        return True
    publish_at = _as_aware(getattr(screen, "publish_at", None))
    return publish_at is not None and now >= publish_at


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
    if media.type in (
        models.MediaType.url,
        models.MediaType.live,
        models.MediaType.pdf,
        models.MediaType.webpage,
    ):
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
            if not item_is_active(item, now) or not media_is_active(item.media, now):
                continue
            if item.media.type in (models.MediaType.youtube, models.MediaType.embed):
                resolved_url = build_embed_url(item.media, muted=item.muted, play_full=getattr(item, "play_full", False))
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
                    play_full=getattr(item, "play_full", False),
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


def _campaign_targets_screen(
    db: Session, campaign: models.Campaign, screen: models.Screen
) -> bool:
    """Indica se uma campanha mira a tela atual."""
    screen_ids = crud._json_to_ints(campaign.screen_ids)  # noqa: SLF001
    group_ids = crud._json_to_ints(campaign.screen_group_ids)  # noqa: SLF001
    if not screen_ids and not group_ids:
        return True
    if screen.id in screen_ids:
        return True
    for group_id in group_ids:
        group = crud.get_screen_group(db, group_id)
        if group is not None and screen.id in [s.id for s in crud.resolve_group_screens(db, group)]:
            return True
    return False


def _campaign_is_active(
    db: Session,
    campaign: models.Campaign,
    *,
    screen: models.Screen,
    zone: models.Zone,
    now: datetime,
) -> bool:
    """Filtro de campanha por janela, alvo e zona."""
    if not campaign.enabled:
        return False
    start = _as_aware(campaign.start_at)
    end = _as_aware(campaign.end_at)
    if start is not None and now < start:
        return False
    if end is not None and now > end:
        return False
    if not _campaign_targets_screen(db, campaign, screen):
        return False
    zone_ids = crud._json_to_ints(campaign.zone_ids)  # noqa: SLF001
    if campaign.mode == "interrupt":
        return True
    return not zone_ids or zone.id in zone_ids


def _choose_campaign(campaigns: list[models.Campaign], now: datetime) -> models.Campaign | None:
    """Escolhe campanha por prioridade e alterna empatadas em ciclos de 10 min."""
    if not campaigns:
        return None
    campaigns = sorted(campaigns, key=lambda c: (c.priority, c.id), reverse=True)
    top_priority = campaigns[0].priority
    top = [c for c in campaigns if c.priority == top_priority]
    if len(top) == 1:
        return top[0]
    return top[(now.minute // 10) % len(top)]


def _effective_playlist_for_zone(
    db: Session, screen: models.Screen, zone: models.Zone, now: datetime
) -> tuple[models.Playlist | None, models.Campaign | None]:
    """Resolve playlist considerando interrupt/layout e campanhas P6."""
    campaigns = [
        campaign
        for campaign in crud.list_campaigns(db, company_id=screen.company_id)
        if _campaign_is_active(db, campaign, screen=screen, zone=zone, now=now)
    ]
    interrupt = _choose_campaign([c for c in campaigns if c.mode == "interrupt"], now)
    if interrupt is not None:
        return crud.get_playlist(db, interrupt.playlist_id), interrupt
    scheduled = _choose_campaign([c for c in campaigns if c.mode == "scheduled"], now)
    if scheduled is not None:
        return crud.get_playlist(db, scheduled.playlist_id), scheduled
    playlist_id = crud.resolve_active_playlist_id(zone, now)
    return (crud.get_playlist(db, playlist_id) if playlist_id else None), None


def _under_play_limit(
    db: Session,
    *,
    screen: models.Screen,
    item: models.PlaylistItem,
    now: datetime,
    campaign: models.Campaign | None = None,
) -> bool:
    """Aplica limite por hora de item/campanha quando configurado."""
    limits = [
        value
        for value in (
            getattr(item, "max_plays_per_hour", None),
            getattr(campaign, "max_plays_per_hour", None) if campaign else None,
        )
        if value is not None
    ]
    if not limits:
        return True
    since = now.replace(minute=0, second=0, microsecond=0)
    plays = crud.play_count_since(
        db, screen_slug=screen.slug, media_id=item.media_id, since=since
    )
    return plays < min(limits)


def build_zone_payload_for_screen(
    base_url: str, db: Session, screen: models.Screen, zone: models.Zone, now: datetime
) -> schemas.DisplayZone:
    """Monta zona considerando campanhas P6 e limites de exibicao."""
    playlist, campaign = _effective_playlist_for_zone(db, screen, zone, now)

    items: list[schemas.DisplayItem] = []
    if playlist is not None:
        for item in sorted(playlist.items, key=lambda i: i.position):
            if (
                not item_is_active(item, now)
                or not media_is_active(item.media, now)
                or not _under_play_limit(db, screen=screen, item=item, now=now, campaign=campaign)
            ):
                continue
            if item.media.type in (models.MediaType.youtube, models.MediaType.embed):
                resolved_url = build_embed_url(item.media, muted=item.muted, play_full=getattr(item, "play_full", False))
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
                    play_full=getattr(item, "play_full", False),
                    url=resolved_url,
                    poster=poster_url,
                    content=item.media.content,
                )
            )

    playlist_name = playlist.name if playlist else None
    if campaign is not None and playlist_name:
        playlist_name = "Campanha: " + campaign.name
    return schemas.DisplayZone(
        id=zone.id,
        name=zone.name,
        x=zone.x,
        y=zone.y,
        width=zone.width,
        height=zone.height,
        z_index=zone.z_index,
        playlist_name=playlist_name,
        items=items,
    )


def compute_revision(payload: schemas.DisplayPayload) -> str:
    """Calcula um hash curto e estável do conteúdo (detecta mudanças)."""
    snapshot = payload.model_dump(exclude={"revision"})
    raw = repr(snapshot).encode()
    return hashlib.sha256(raw).hexdigest()[:12]


def _screen_theme(screen: models.Screen) -> dict | None:
    """Monta o dicionario de tema (somente cores definidas) para o player."""
    theme: dict = {}
    mapping = (
        ("bg", "theme_bg"),
        ("text", "theme_text"),
        ("accent", "theme_accent"),
        ("tickerBg", "theme_ticker_bg"),
        ("tickerText", "theme_ticker_text"),
    )
    for key, attr in mapping:
        value = getattr(screen, attr, None)
        if value:
            theme[key] = value
    return theme or None


def build_overlays_payload(screen: models.Screen) -> list[schemas.DisplayOverlay]:
    """Resolve os overlays habilitados de uma tela para o player."""
    items: list[schemas.DisplayOverlay] = []
    for overlay in sorted(
        getattr(screen, "overlays", []) or [], key=lambda o: o.z_index
    ):
        if not overlay.enabled:
            continue
        items.append(
            schemas.DisplayOverlay(
                id=overlay.id,
                kind=overlay.kind,
                content=overlay.content,
                position=overlay.position,
                width=overlay.width,
                height=overlay.height,
                mode=overlay.mode,
                interval_seconds=overlay.interval_seconds,
                visible_seconds=overlay.visible_seconds,
                opacity=overlay.opacity,
                z_index=overlay.z_index,
            )
        )
    return items


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
    if not _screen_is_published(screen, now):
        payload = schemas.DisplayPayload(
            screen=screen.slug,
            revision="",
            theme=_screen_theme(screen),
            zones=[],
            overlays=[],
            background_audio=None,
            emergency_message=None,
        )
        payload.revision = compute_revision(payload)
        return payload
    zones = [
        build_zone_payload_for_screen(base_url, db, screen, zone, now)
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
        theme=_screen_theme(screen),
        zones=zones,
        overlays=build_overlays_payload(screen),
        background_audio=background_audio,
        emergency_message=emergency_message,
    )
    payload.revision = compute_revision(payload)
    return payload
