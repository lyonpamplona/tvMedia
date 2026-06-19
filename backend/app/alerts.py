"""Alertas operacionais de telas offline (P4).

O monitor percorre periodicamente as telas e dispara alerta por webhook e/ou
SMTP quando uma tela fica sem heartbeat por tempo configurado. Se nenhum canal
externo estiver configurado, ele apenas atualiza o estado no banco.
"""

from __future__ import annotations

import asyncio
import json
import logging
import smtplib
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from . import crud, models
from .config import settings
from .database import SessionLocal

logger = logging.getLogger("tvmedia.alerts")


def _as_utc(value: datetime | None) -> datetime | None:
    """Normaliza datetime para UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _should_send(alert, now: datetime) -> bool:
    """Indica se o alerta pode ser reenviado conforme intervalo configurado."""
    if alert is None or alert.last_alert_at is None:
        return True
    last = _as_utc(alert.last_alert_at)
    return (now - last) >= timedelta(minutes=settings.offline_alert_repeat_minutes)


def _send_webhook(screen: models.Screen, offline_minutes: int) -> bool:
    """Envia alerta via webhook JSON, se configurado."""
    if not settings.offline_alert_webhook_url:
        return False
    payload = {
        "type": "screen_offline",
        "screen": {
            "id": screen.id,
            "name": screen.name,
            "slug": screen.slug,
            "location": screen.location_label,
            "sync_group": screen.sync_group,
        },
        "offline_minutes": offline_minutes,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    req = urllib.request.Request(
        settings.offline_alert_webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "tvMedia/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao enviar webhook de alerta offline: %s", exc)
        return False


def _send_email(screen: models.Screen, offline_minutes: int) -> bool:
    """Envia alerta via SMTP, se configurado."""
    if not (
        settings.smtp_host
        and settings.smtp_from
        and settings.offline_alert_email_to
    ):
        return False
    msg = EmailMessage()
    msg["Subject"] = f"tvMedia: tela offline - {screen.name}"
    msg["From"] = settings.smtp_from
    msg["To"] = settings.offline_alert_email_to
    msg.set_content(
        "\n".join(
            [
                f"Tela offline: {screen.name}",
                f"Slug: {screen.slug}",
                f"Local: {screen.location_label or '-'}",
                f"Grupo de sincronia: {screen.sync_group or '-'}",
                f"Sem contato ha aproximadamente {offline_minutes} minuto(s).",
            ]
        )
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao enviar email de alerta offline: %s", exc)
        return False


def check_offline_alerts_once() -> None:
    """Executa uma rodada de checagem de telas offline."""
    if not settings.offline_alert_enabled:
        return
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=settings.offline_alert_after_minutes)
    with SessionLocal() as db:
        for screen in crud.list_screens(db):
            last_seen = _as_utc(screen.last_seen)
            offline = last_seen is None or last_seen < cutoff
            alert = crud.get_offline_alert(db, screen.id)
            if not offline:
                if alert is not None and alert.is_offline:
                    crud.set_offline_alert_state(db, screen, is_offline=False)
                continue
            if not _should_send(alert, now):
                crud.set_offline_alert_state(db, screen, is_offline=True)
                continue
            offline_minutes = (
                settings.offline_alert_after_minutes
                if last_seen is None
                else max(0, int((now - last_seen).total_seconds() // 60))
            )
            sent = _send_webhook(screen, offline_minutes)
            sent = _send_email(screen, offline_minutes) or sent
            crud.set_offline_alert_state(db, screen, is_offline=True, alerted=sent)


async def offline_alert_scheduler(stop_event: asyncio.Event) -> None:
    """Loop assíncrono de monitoramento offline."""
    while not stop_event.is_set():
        try:
            check_offline_alerts_once()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha na checagem de alertas offline: %s", exc)
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=settings.offline_alert_check_seconds
            )
        except asyncio.TimeoutError:
            pass
