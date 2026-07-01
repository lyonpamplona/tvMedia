"""Ponto de entrada da aplicação FastAPI do tvMedia.

Responsabilidades:

* Inicializar o banco no startup e semear o administrador padrão.
* Validar a configuração de segurança (recusa subir em produção com
  segredos padrão; emite avisos em desenvolvimento).
* Iniciar/parar a tarefa de backup automático do banco.
* Configurar CORS (credenciais só quando as origens são explícitas).
* Registrar os roteadores da API (auth, users, media, folders, playlists,
  screens, zones, schedules, display, analytics, audit).
* Servir os arquivos de mídia enviados e o frontend estático (painel + player).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, alerts, backup, crud, reports, retention
from .config import settings
from .database import SessionLocal, init_db
from .routers import (
    ad_breaks,
    analytics,
    audit,
    auth,
    campaigns,
    companies,
    datasets,
    display,
    folders,
    live,
    media,
    metrics,
    overlays,
    playlists,
    schedules,
    screen_groups,
    screens,
    system,
    users,
    widgets,
    zones,
)

logger = logging.getLogger("tvmedia")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Executa tarefas de inicialização e finalização da aplicação.

    No startup: valida a segurança, cria as tabelas, semeia o administrador
    padrão e inicia o agendador de backups. No shutdown: sinaliza e aguarda o
    encerramento da tarefa de backup.
    """
    # Falha cedo em produção se houver segredos padrão; só avisa em dev.
    settings.validate_security()
    for warning in settings.security_warnings():
        logger.warning("[segurança] %s", warning)

    init_db()
    with SessionLocal() as db:
        # Garante a empresa padrão "Matriz" e migra dados antigos sem empresa.
        default_company = crud.seed_default_company(db)
        crud.backfill_company(db, default_company.id)
        admin = crud.seed_admin(db)
        if admin is not None:
            logger.warning(
                "Administrador inicial criado (usuário 'admin'). "
                "Altere a senha padrão assim que possível."
            )

    stop_event = asyncio.Event()
    backup_task: asyncio.Task | None = None
    alert_task: asyncio.Task | None = None
    report_task: asyncio.Task | None = None
    retention_task: asyncio.Task | None = None
    if settings.backup_enabled:
        backup_task = asyncio.create_task(backup.backup_scheduler(stop_event))
    if settings.offline_alert_enabled:
        alert_task = asyncio.create_task(alerts.offline_alert_scheduler(stop_event))
    if settings.report_scheduler_enabled:
        report_task = asyncio.create_task(reports.report_scheduler(stop_event))
    if settings.play_events_retention_days > 0:
        retention_task = asyncio.create_task(
            retention.retention_scheduler(stop_event)
        )

    try:
        yield
    finally:
        stop_event.set()
        if backup_task is not None:
            backup_task.cancel()
            try:
                await backup_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if alert_task is not None:
            alert_task.cancel()
            try:
                await alert_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if report_task is not None:
            report_task.cancel()
            try:
                await report_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if retention_task is not None:
            retention_task.cancel()
            try:
                await retention_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Sistema autohospedado de sinalização digital para TVs.",
    lifespan=lifespan,
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
)

if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Adiciona headers de seguranca basicos (P8)."""
    response = await call_next(request)
    if settings.security_headers_enabled:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.scheme == "https" or settings.force_https:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={settings.hsts_seconds}; includeSubDomains",
            )
    return response

# Roteadores da API.
app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(companies.router)
app.include_router(companies.branding_router)
app.include_router(companies.templates_router)
app.include_router(users.router)
app.include_router(media.router)
app.include_router(datasets.router)
app.include_router(folders.router)
app.include_router(playlists.router)
app.include_router(screen_groups.router)
app.include_router(screens.router)
app.include_router(system.router)
app.include_router(zones.router)
app.include_router(overlays.router)
app.include_router(live.router)
app.include_router(schedules.router)
app.include_router(display.router)
app.include_router(widgets.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(metrics.router)
app.include_router(ad_breaks.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """Healthcheck simples usado pelo Docker e por monitoramento."""
    return {"status": "ok", "version": __version__}


# Arquivos de mídia enviados (público, somente leitura).
app.mount("/media", StaticFiles(directory=str(settings.media_dir)), name="media")

# Frontend estático: painel administrativo e player.
admin_dir = settings.frontend_dir / "admin"
player_dir = settings.frontend_dir / "player"
if admin_dir.is_dir():
    app.mount("/admin", StaticFiles(directory=str(admin_dir), html=True), name="admin")
if player_dir.is_dir():
    app.mount("/player", StaticFiles(directory=str(player_dir), html=True), name="player")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redireciona a raiz para o painel administrativo."""
    return RedirectResponse(url="/admin/")
