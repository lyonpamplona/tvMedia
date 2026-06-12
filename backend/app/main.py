"""Ponto de entrada da aplicação FastAPI do AdSignage (v2).

Responsabilidades:

* Inicializar o banco de dados no startup (via ``lifespan``).
* Configurar CORS.
* Registrar os roteadores da API (auth, media, playlists, screens, zones,
  schedules, display).
* Servir os arquivos de mídia enviados e o frontend estático (painel + player).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .database import init_db
from .routers import auth, display, media, playlists, schedules, screens, zones


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Executa tarefas de inicialização e finalização da aplicação.

    No startup, cria as tabelas do banco caso ainda não existam.
    """
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Sistema autohospedado de sinalização digital para TVs.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Roteadores da API.
app.include_router(auth.router)
app.include_router(media.router)
app.include_router(playlists.router)
app.include_router(screens.router)
app.include_router(zones.router)
app.include_router(schedules.router)
app.include_router(display.router)


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
