"""Backup automático do banco SQLite com rotação e agendador assíncrono.

Usa a API nativa ``sqlite3.Connection.backup`` (consistente mesmo com o banco
em uso, graças ao WAL). Para bancos não-SQLite, o backup automático é ignorado
(use as ferramentas do próprio SGBD). O agendador roda como uma tarefa
assíncrona iniciada no ``lifespan`` da aplicação.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

_logger = logging.getLogger("adsignage.backup")


def _sqlite_path() -> Path | None:
    """Extrai o caminho do arquivo do ``database_url`` (ou None se não-SQLite)."""
    url = settings.database_url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    return Path(url[len(prefix):])


def create_backup() -> Path | None:
    """Cria um backup pontual do banco SQLite.

    Returns:
        Path | None: caminho do arquivo gerado, ou None se não aplicável.
    """
    source = _sqlite_path()
    if source is None or not source.exists():
        return None

    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = settings.backup_dir / f"adsignage-{stamp}.db"

    src_conn = sqlite3.connect(str(source))
    try:
        dst_conn = sqlite3.connect(str(destination))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    _logger.info("Backup criado: %s", destination)
    return destination


def rotate_backups(keep: int | None = None) -> list[Path]:
    """Mantém apenas os ``keep`` backups mais recentes, removendo o excedente.

    Args:
        keep: quantos manter (usa ``settings.backup_keep`` se omitido).

    Returns:
        list[Path]: arquivos removidos.
    """
    keep = keep if keep is not None else settings.backup_keep
    if not settings.backup_dir.exists():
        return []
    backups = sorted(
        settings.backup_dir.glob("adsignage-*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed: list[Path] = []
    for stale in backups[keep:]:
        try:
            stale.unlink()
            removed.append(stale)
        except OSError:  # pragma: no cover - falha rara de FS
            _logger.warning("Não foi possível remover backup antigo: %s", stale)
    return removed


def run_backup_now() -> Path | None:
    """Cria um backup e aplica a rotação (uso manual/endpoint)."""
    path = create_backup()
    if path is not None:
        rotate_backups()
    return path


async def backup_scheduler(stop_event: asyncio.Event) -> None:
    """Laço assíncrono que gera backups periódicos até receber sinal de parada.

    Args:
        stop_event: evento usado para encerrar o laço no shutdown.
    """
    if not settings.backup_enabled or _sqlite_path() is None:
        return
    interval = max(1, settings.backup_interval_hours) * 3600
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(run_backup_now)
        except Exception:  # noqa: BLE001 - backup nunca deve derrubar o app
            _logger.exception("Falha ao gerar backup automático.")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
