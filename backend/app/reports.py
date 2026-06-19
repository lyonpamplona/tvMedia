"""Relatorios agendados de proof-of-play (P7)."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from . import crud, models
from .config import settings
from .database import SessionLocal

logger = logging.getLogger("tvmedia.reports")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_csv(rows) -> str:
    """Gera CSV UTF-8 em texto a partir de linhas detalhadas."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["played_at", "screen_slug", "zone_id", "media_id", "media_name", "media_type", "duration_seconds"]
    )
    for row in rows:
        writer.writerow(
            [
                row.played_at.isoformat(),
                row.screen_slug,
                row.zone_id or "",
                row.media_id or "",
                row.media_name,
                row.media_type,
                row.duration_seconds,
            ]
        )
    return out.getvalue()


def _pdf_escape(text: object) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(summary, rows, *, title: str) -> bytes:
    """Gera um PDF textual simples sem dependencias externas."""
    lines = [
        title,
        f"Gerado em: {datetime.now(timezone.utc).isoformat()}",
        f"Plays: {summary.total_plays} | Tempo: {summary.total_seconds}s | Midias: {summary.unique_media} | Telas: {summary.unique_screens}",
        "",
    ]
    for row in rows[:35]:
        lines.append(
            f"{row.played_at:%Y-%m-%d %H:%M}  {row.screen_slug}  {row.media_name[:42]}  {row.duration_seconds}s"
        )
    stream = "BT /F1 10 Tf 40 780 Td\n"
    for idx, line in enumerate(lines):
        if idx:
            stream += "0 -14 Td\n"
        stream += f"({_pdf_escape(line)}) Tj\n"
    stream += "ET"
    stream_bytes = stream.encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream_bytes)).encode() + b" >>\nstream\n" + stream_bytes + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(pdf)


def _should_send(row: models.ReportSchedule, now: datetime) -> bool:
    if not row.enabled or now.hour != row.hour:
        return False
    last = _as_utc(row.last_sent_at)
    if row.frequency == "weekly" and now.weekday() != 0:
        return False
    if last is None:
        return True
    return last.date() < now.date()


def send_report_once(db, row: models.ReportSchedule, now: datetime | None = None) -> bool:
    """Envia um relatorio agendado imediatamente."""
    if not settings.smtp_host or not settings.smtp_from:
        logger.info("SMTP nao configurado; relatorio %s nao enviado.", row.id)
        return False
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=row.days)
    summary = crud.proof_of_play_summary(
        db, since=since, screen_slug=row.screen_slug, company_id=row.company_id
    )
    details = crud.proof_of_play_details(
        db, since=since, screen_slug=row.screen_slug, company_id=row.company_id, limit=5000
    )
    csv_text = build_csv(details)
    pdf_bytes = build_pdf(summary, details, title=f"tvMedia - {row.name}")
    msg = EmailMessage()
    msg["Subject"] = f"tvMedia: relatorio {row.name}"
    msg["From"] = settings.smtp_from
    msg["To"] = row.recipients
    msg.set_content(
        "\n".join(
            [
                f"Relatorio: {row.name}",
                f"Janela: ultimos {row.days} dia(s)",
                f"Total de plays: {summary.total_plays}",
                f"Tempo total: {summary.total_seconds} segundo(s)",
                "Anexos: PDF resumido e CSV detalhado.",
            ]
        )
    )
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename="proof-of-play.pdf")
    msg.add_attachment(csv_text.encode("utf-8-sig"), maintype="text", subtype="csv", filename="proof-of-play.csv")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
    crud.mark_report_sent(db, row, now)
    return True


def check_reports_once() -> None:
    """Executa uma rodada de envio dos relatorios agendados."""
    if not settings.report_scheduler_enabled:
        return
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for row in crud.list_report_schedules(db):
            if not _should_send(row, now):
                continue
            try:
                send_report_once(db, row, now)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Falha ao enviar relatorio %s: %s", row.id, exc)


async def report_scheduler(stop_event: asyncio.Event) -> None:
    """Loop periodico de relatorios agendados."""
    while not stop_event.is_set():
        check_reports_once()
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=settings.report_scheduler_check_seconds
            )
        except asyncio.TimeoutError:
            continue
