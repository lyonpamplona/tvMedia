"""Retencao automatica de eventos de reproducao (proof-of-play).

A tabela ``play_events`` cresce indefinidamente em instalacoes ativas. Quando
``PLAY_EVENTS_RETENTION_DAYS`` e maior que zero, este agendador remove
periodicamente os eventos mais antigos que a janela configurada, mantendo o
banco enxuto. Vale para qualquer dialeto (SQLite ou PostgreSQL).

O laco roda como tarefa assincrona iniciada no ``lifespan`` da aplicacao e e
best-effort: uma falha na limpeza nunca derruba o app.
"""

from __future__ import annotations

import asyncio
import logging

from . import crud
from .config import settings
from .database import SessionLocal

_logger = logging.getLogger("tvmedia.retention")


def run_retention_now() -> int:
    """Remove eventos alem da janela de retencao. Retorna quantos foram apagados."""
    days = int(settings.play_events_retention_days)
    if days <= 0:
        return 0
    with SessionLocal() as db:
        removed = crud.purge_play_events(db, older_than_days=days)
    if removed:
        _logger.info("Retencao: %s eventos de reproducao removidos (>%sd).", removed, days)
    return removed


async def retention_scheduler(stop_event: asyncio.Event) -> None:
    """Laco assincrono que aplica a retencao ate receber o sinal de parada."""
    if int(settings.play_events_retention_days) <= 0:
        return
    interval = max(1, int(settings.retention_check_hours)) * 3600
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(run_retention_now)
        except Exception:  # noqa: BLE001 - limpeza nunca deve derrubar o app
            _logger.exception("Falha ao aplicar retencao de play_events.")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
