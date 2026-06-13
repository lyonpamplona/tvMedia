"""Construção de URLs de incorporação (embed) para YouTube e players de música.

O player exibe conteúdo externo dentro de um ``<iframe>``. Para que vídeos e
playlists toquem corretamente (autoplay, loop, sem controles), é preciso
converter os links "normais" (compartilhamento/watch) nas URLs de **embed**
com os parâmetros adequados. Este módulo concentra essa lógica.

Suporta:

* **YouTube** — vídeo único (com loop) e playlists (``list=...``).
* **Spotify** — faixas, álbuns e playlists (converte ``/...`` em ``/embed/...``).
* **Genérico** — qualquer outra URL de embed é usada como está.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, quote, urlparse

from . import models

# Um ID de vídeo do YouTube tem 11 caracteres no alfabeto base64-url.
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _extract_youtube(url: str) -> tuple[str | None, str | None]:
    """Extrai ``(video_id, playlist_id)`` de uma URL do YouTube.

    Aceita os formatos mais comuns: ``watch?v=``, ``youtu.be/<id>``,
    ``/embed/<id>``, ``/shorts/<id>``, ``/playlist?list=`` e também um ID
    "cru" (apenas os 11 caracteres do vídeo).

    Args:
        url: URL (ou ID) informada pelo usuário.

    Returns:
        tuple[str | None, str | None]: o ID do vídeo e/ou o ID da playlist.
    """
    raw = (url or "").strip()
    if _YOUTUBE_ID.match(raw):
        return raw, None

    try:
        parsed = urlparse(raw)
    except ValueError:
        return None, None

    host = (parsed.hostname or "").lower()
    query = parse_qs(parsed.query)
    playlist_id = query.get("list", [None])[0]
    video_id: str | None = None

    if "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/")[0] or None
    elif "youtube" in host or "youtube-nocookie" in host:
        path = parsed.path
        if path.startswith("/watch"):
            video_id = query.get("v", [None])[0]
        elif path.startswith("/embed/"):
            video_id = path.split("/embed/", 1)[1].split("/")[0] or None
        elif path.startswith("/shorts/"):
            video_id = path.split("/shorts/", 1)[1].split("/")[0] or None

    return video_id, playlist_id


def build_youtube_embed(url: str, *, muted: bool = True, loop: bool = True, jsapi: bool = False) -> str:
    """Monta a URL de embed do YouTube com autoplay e loop.

    Para um vídeo único, o loop exige repetir o próprio ID em ``playlist=``
    (limitação do player do YouTube). Para playlists, usa ``videoseries``.

    Args:
        url: link do vídeo ou da playlist.
        muted: se True, inicia sem som (recomendado para autoplay confiável).

    Returns:
        str: URL pronta para uso em ``<iframe src=...>`` (ou a original como
        fallback, se não for possível interpretar).
    """
    video_id, playlist_id = _extract_youtube(url)
    mute = "1" if muted else "0"
    common = (
        f"autoplay=1&mute={mute}&controls=0&rel=0"
        "&modestbranding=1&playsinline=1"
    )
    if jsapi:
        common += "&enablejsapi=1"
    if playlist_id:
        loop_part = "&loop=1" if loop else ""
        return (
            "https://www.youtube.com/embed/videoseries"
            f"?list={quote(playlist_id)}{loop_part}&{common}"
        )
    if video_id:
        loop_part = f"loop=1&playlist={video_id}&" if loop else ""
        return (
            f"https://www.youtube.com/embed/{video_id}"
            f"?{loop_part}{common}"
        )
    return url


def _build_spotify_embed(url: str) -> str:
    """Converte um link do Spotify em sua URL de embed (``/embed/...``)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    if "open.spotify.com" not in (parsed.hostname or "").lower():
        return url
    if parsed.path.startswith("/embed"):
        return url
    return f"https://open.spotify.com/embed{parsed.path}"


def build_embed_url(media: "models.Media", *, muted: bool = True, play_full: bool = False) -> str:
    """Resolve a URL final de incorporação conforme o tipo da mídia.

    Args:
        media: mídia do tipo ``youtube`` ou ``embed``.
        muted: preferência de áudio (aplicável ao YouTube).

    Returns:
        str: URL pronta para o ``<iframe>`` do player.
    """
    url = media.source_url or ""
    if media.type == models.MediaType.youtube:
        return build_youtube_embed(url, muted=muted, loop=not play_full, jsapi=play_full)
    if media.type == models.MediaType.embed:
        host = (urlparse(url).hostname or "").lower() if url else ""
        if "spotify.com" in host:
            return _build_spotify_embed(url)
        if "youtube" in host or "youtu.be" in host:
            return build_youtube_embed(url, muted=muted, loop=not play_full, jsapi=play_full)
        return url
    return url
