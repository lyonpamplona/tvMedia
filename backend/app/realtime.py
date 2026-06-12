"""Camada de notificação em tempo real.

Funciona como ponte entre os roteadores REST e o :class:`ConnectionManager`
(WebSocket). Em vez de cada endpoint conhecer os detalhes de quais telas avisar,
ele chama uma destas funções de alto nível.

A mensagem enviada é sempre ``{"type": "reload", "reason": ...}``. O player,
ao receber, busca novamente o payload de exibição e re-renderiza. Essa
abordagem ("avisar para recarregar") é simples e robusta: a fonte da verdade
continua sendo o endpoint REST de display.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .websocket_manager import manager


async def notify_screen(slug: str, *, reason: str) -> None:
    """Pede a uma tela específica que recarregue seu conteúdo.

    Args:
        slug: identificador público da tela.
        reason: motivo da atualização (apenas para depuração/log no player).
    """
    await manager.broadcast(slug, {"type": "reload", "reason": reason})


async def notify_playlist_screens(
    db: Session, playlist_id: int, *, reason: str
) -> None:
    """Notifica todas as telas vinculadas a uma playlist.

    Args:
        db: sessão ativa para consultar as telas.
        playlist_id: ID da playlist alterada.
        reason: motivo da atualização.
    """
    slugs = db.scalars(
        select(models.Screen.slug).where(models.Screen.playlist_id == playlist_id)
    )
    for slug in slugs:
        await manager.broadcast(slug, {"type": "reload", "reason": reason})


async def notify_all_screens(db: Session, *, reason: str) -> None:
    """Notifica todas as telas conhecidas (útil quando uma mídia muda).

    Args:
        db: sessão ativa para consultar as telas.
        reason: motivo da atualização.
    """
    slugs = db.scalars(select(models.Screen.slug))
    for slug in slugs:
        await manager.broadcast(slug, {"type": "reload", "reason": reason})
