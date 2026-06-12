"""Ponto de entrada da aplicação FastAPI (AdSignage).

Responsabilidades deste módulo:

* Criar a instância ``app`` do FastAPI e configurar CORS.
* Inicializar o banco de dados no startup.
* Registrar os roteadores REST e o WebSocket de exibição.
* Servir arquivos estáticos: mídia enviada (``/media``), painel administrativo
  (``/admin``) e player (``/player``).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .database import init_db
from .routers import display, media, playlists, screens


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação.

    No startup, garante que as tabelas existam. É o local ideal para futuras
    rotinas de inicialização (ex.: migrações, seeds).
    """
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    summary="Sistema autohospedado de sinalização digital (digital signage).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Roteadores da API REST e o WebSocket.
app.include_router(media.router)
app.include_router(playlists.router)
app.include_router(screens.router)
app.include_router(display.router)


@app.get("/api/health", tags=["sistema"])
def health() -> dict[str, str]:
    """Endpoint simples de verificação de saúde (healthcheck)."""
    return {"status": "ok", "app": settings.app_name, "version": __version__}


# --------------------------------------------------------------------------- #
# Arquivos estáticos
# --------------------------------------------------------------------------- #
# Mídias enviadas pelos usuários.
app.mount(
    "/media",
    StaticFiles(directory=str(settings.media_dir)),
    name="media",
)

# Frontend: painel administrativo e player. Servidos apenas se o diretório
# existir (em desenvolvimento o frontend pode ser servido separadamente).
if (settings.frontend_dir / "admin").is_dir():
    app.mount(
        "/admin",
        StaticFiles(directory=str(settings.frontend_dir / "admin"), html=True),
        name="admin",
    )
if (settings.frontend_dir / "player").is_dir():
    app.mount(
        "/player",
        StaticFiles(directory=str(settings.frontend_dir / "player"), html=True),
        name="player",
    )


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    """Redireciona a raiz para o painel administrativo."""
    return RedirectResponse(url="/admin/")
