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


def build_cues_payload(
    media: models.Media,
    base_url: str | None = None,
    db: Session | None = None,
) -> list[schemas.DisplayCue]:
    """Converte os cue points (L3/L5) de uma midia em itens para o player.

    Apenas cues habilitados sao emitidos, ja ordenados por ``at_seconds``. O
    player escuta o ``timeupdate`` do video e dispara cada cue no instante certo.

    Para cues de **ad-break** (L5, ``action == "ad_break"``) com ``target_id``,
    resolve a midia de anuncio referenciada e injeta sua ``url``/``poster`` e o
    tipo real em ``kind``, para o player exibir o anuncio em tela cheia. Exige
    ``base_url`` e ``db`` para montar a URL absoluta da midia.
    """
    cues = getattr(media, "cues", None) or []
    payload: list[schemas.DisplayCue] = []
    for cue in sorted(cues, key=lambda c: c.at_seconds):
        if not getattr(cue, "enabled", True):
            continue
        kind = cue.kind
        anchor = cue.anchor
        url: str | None = None
        poster: str | None = None
        if cue.action == "ad_break" and cue.target_id and db is not None:
            ad = crud.get_media(db, cue.target_id)
            if ad is not None:
                kind = getattr(ad.type, "value", str(ad.type))
                url = media_url(base_url or "", ad)
                if getattr(ad, "poster_path", None) and base_url:
                    poster = base_url + f"media/{ad.poster_path}"
                # Anuncio ocupa a tela inteira por padrao.
                if anchor in ("", "lower_third"):
                    anchor = "fullscreen"
        payload.append(
            schemas.DisplayCue(
                at_seconds=cue.at_seconds,
                action=cue.action,
                kind=kind,
                content=cue.content,
                target_id=cue.target_id,
                slot_id=cue.slot_id,
                anchor=anchor,
                enter_anim=cue.enter_anim,
                exit_anim=cue.exit_anim,
                duration=cue.duration,
                url=url,
                poster=poster,
            )
        )
    return payload


def _zone_style(zone: models.Zone) -> dict:
    """Campos de customizacao visual de uma zona para o payload do player."""
    return dict(
        bg_color=getattr(zone, "bg_color", None),
        opacity=getattr(zone, "opacity", 1.0),
        radius=getattr(zone, "radius", 0.0),
        padding=getattr(zone, "padding", 0.0),
        border_width=getattr(zone, "border_width", 0.0),
        border_color=getattr(zone, "border_color", None),
        font_family=getattr(zone, "font_family", None),
    )


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
                    cues=build_cues_payload(item.media, base_url, db),
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
        **_zone_style(zone),
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
    """Escolhe a campanha ativa por prioridade, com rotacao ponderada (L5).

    A campanha de maior ``priority`` vence. Havendo empate, aplica-se uma
    **rotacao ponderada**: cada campanha entra na roda ``weight`` vezes e o ciclo
    de 10 minutos (``now.minute // 10``) seleciona a posicao. Assim, pesos
    maiores aparecem proporcionalmente mais, de forma deterministica (igual em
    todas as telas, sem aleatoriedade). Peso 0 remove a campanha do rodizio
    quando ha outras com peso; se todas tiverem peso 0, cai numa alternancia
    simples.
    """
    if not campaigns:
        return None
    campaigns = sorted(campaigns, key=lambda c: (c.priority, c.id), reverse=True)
    top_priority = campaigns[0].priority
    top = [c for c in campaigns if c.priority == top_priority]
    if len(top) == 1:
        return top[0]
    wheel: list[models.Campaign] = []
    for campaign in top:
        weight = max(0, int(getattr(campaign, "weight", 1) or 0))
        wheel.extend([campaign] * weight)
    if not wheel:
        wheel = top  # todas com peso 0: volta a alternancia simples
    return wheel[(now.minute // 10) % len(wheel)]


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
                    cues=build_cues_payload(item.media, base_url, db),
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
        **_zone_style(zone),
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
    if getattr(screen, "theme_font", None):
        theme["font"] = screen.theme_font
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
                # L1 - Live Graphics: posicionamento, animacao e janela de tempo.
                # `getattr` com fallback garante compatibilidade com bancos
                # antigos cujas colunas ainda nao migraram.
                anchor=getattr(overlay, "anchor", "") or "",
                margin=getattr(overlay, "margin", 2.0) or 0.0,
                enter_anim=getattr(overlay, "enter_anim", "fade") or "fade",
                exit_anim=getattr(overlay, "exit_anim", "fade") or "fade",
                enter_at=getattr(overlay, "enter_at", 0.0) or 0.0,
                duration=getattr(overlay, "duration", 0.0) or 0.0,
                repeat_every=getattr(overlay, "repeat_every", 0.0) or 0.0,
            )
        )
    return items


def build_ad_breaks_payload(
    base_url: str, db: Session, screen: models.Screen
) -> list[schemas.DisplayAdBreak]:
    """Resolve os ad-breaks recorrentes/agendados (L6) aplicaveis a uma tela.

    Para cada agendamento habilitado que vale para a tela, resolve a midia do
    anuncio (URL/poster/tipo) e emite os parametros de recorrencia. O disparo em
    si acontece no ``player.js`` por relogio de parede; aqui apenas entregamos a
    "agenda" ja resolvida. Agendamentos sem midia valida sao ignorados.
    """
    out: list[schemas.DisplayAdBreak] = []
    for sched in crud.list_ad_breaks_for_screen(db, screen):
        if not sched.media_id:
            continue
        ad = crud.get_media(db, sched.media_id)
        if ad is None:
            continue
        url = media_url(base_url or "", ad)
        if not url:
            continue
        poster = None
        if getattr(ad, "poster_path", None) and base_url:
            poster = base_url + f"media/{ad.poster_path}"
        out.append(
            schemas.DisplayAdBreak(
                name=sched.name,
                media_id=sched.media_id,
                kind=getattr(ad.type, "value", str(ad.type)),
                url=url,
                poster=poster,
                every_minutes=sched.every_minutes,
                duration_seconds=sched.duration_seconds,
                start_time=sched.start_time,
                end_time=sched.end_time,
                days=sched.days,
                enter_anim=sched.enter_anim,
                exit_anim=sched.exit_anim,
            )
        )
    return out


def _screen_background(base_url: str, db: Session, screen: models.Screen) -> dict | None:
    """Fundo da tela: cor (tema), imagem (midia) ou transparente."""
    mode = getattr(screen, "background_mode", "color") or "color"
    bg: dict = {"mode": mode, "fit": getattr(screen, "background_fit", "cover") or "cover"}
    if mode == "image" and getattr(screen, "background_image_id", None):
        media = crud.get_media(db, screen.background_image_id)
        if media is not None:
            bg["image"] = media_url(base_url, media)
    return bg


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
            background=_screen_background(base_url, db, screen),
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
        background=_screen_background(base_url, db, screen),
        zones=zones,
        overlays=build_overlays_payload(screen),
        ad_breaks=build_ad_breaks_payload(base_url, db, screen),
        background_audio=background_audio,
        emergency_message=emergency_message,
    )
    payload.revision = compute_revision(payload)
    return payload
