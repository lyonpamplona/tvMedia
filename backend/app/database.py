"""Configuração da camada de persistência com SQLAlchemy.

Expõe o ``engine``, a fábrica de sessões ``SessionLocal``, a ``Base``
declarativa usada pelos modelos e a dependência :func:`get_db`, consumida
pelos endpoints do FastAPI para obter uma sessão de banco por requisição.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings

# Para SQLite é necessário desabilitar a checagem de thread, pois o FastAPI
# pode acessar a mesma conexão a partir de threads diferentes.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    future=True,
    # Pool pequeno: poucas conexões simultâneas bastam para um único worker e
    # evitam manter muitos buffers de cache do SQLite em memória.
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        """Aplica PRAGMAs voltados a baixo uso de memória e boa concorrência.

        * ``journal_mode=WAL`` + ``synchronous=NORMAL``: leituras e escritas
          concorrentes sem travar, com bom equilíbrio de durabilidade.
        * ``cache_size=-2000``: limita o cache de páginas a ~2 MB por conexão.
        * ``temp_store=MEMORY`` e ``mmap_size=0``: mantêm o uso de RAM previsível.
        * ``busy_timeout``: aguarda em vez de falhar sob contenção de escrita.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA cache_size=-2000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=0")
        cursor.close()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

# Base declarativa herdada por todos os modelos ORM.
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco de dados por requisição.

    É usada como dependência do FastAPI (``Depends(get_db)``). Garante que a
    sessão seja fechada ao final, mesmo em caso de exceção.

    Yields:
        Session: sessão ativa do SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_sqlite_migrations() -> None:
    """Migracao leve para bancos SQLite ja existentes (sem Alembic).

    ``create_all`` cria apenas tabelas que ainda nao existem; ele NAO altera
    tabelas antigas. Quando o usuario reaproveita um ``adsignage.db`` de uma
    versao anterior, as colunas multiempresa/sincronia ficam faltando e os
    novos recursos nao aparecem. Esta rotina adiciona, de forma idempotente,
    as colunas que faltarem e gera codigos de emparelhamento para telas antigas.
    """
    if not settings.database_url.startswith("sqlite"):
        return

    import secrets

    additions = {
        "users": [("company_id", "INTEGER"), ("is_super_admin", "BOOLEAN NOT NULL DEFAULT 0"), ("totp_secret", "VARCHAR(64)"), ("totp_enabled", "BOOLEAN NOT NULL DEFAULT 0")],
        "api_tokens": [("company_id", "INTEGER"), ("expires_at", "DATETIME"), ("last_used_at", "DATETIME")],
        "media_folders": [("company_id", "INTEGER")],
        "media": [("company_id", "INTEGER"), ("width", "INTEGER"), ("height", "INTEGER"), ("optimized_path", "VARCHAR(512)"), ("poster_path", "VARCHAR(512)"), ("processing_status", "VARCHAR(16) NOT NULL DEFAULT 'pending'"), ("processing_note", "TEXT"), ("expires_at", "DATETIME"), ("collect_stats", "BOOLEAN NOT NULL DEFAULT 1")],
        "playlist_folders": [("company_id", "INTEGER")],
        "playlists": [("company_id", "INTEGER"), ("tags", "VARCHAR(512)"), ("folder_id", "INTEGER")],
        "playlist_items": [("focal", "VARCHAR(16) NOT NULL DEFAULT 'center'"), ("play_full", "BOOLEAN NOT NULL DEFAULT 0"), ("start_at", "DATETIME"), ("end_at", "DATETIME"), ("max_plays_per_hour", "INTEGER")],
        "companies": [("emergency_message", "TEXT"), ("emergency_active", "BOOLEAN NOT NULL DEFAULT 0")],
        "screens": [("pair_code", "VARCHAR(12)"), ("sync_group", "VARCHAR(64)"), ("publish_status", "VARCHAR(16) NOT NULL DEFAULT 'published'"), ("publish_at", "DATETIME"), ("published_at", "DATETIME"), ("layout_locked", "BOOLEAN NOT NULL DEFAULT 0"), ("collect_stats", "BOOLEAN NOT NULL DEFAULT 1"), ("tags", "VARCHAR(512)"), ("location_label", "VARCHAR(255)"), ("latitude", "FLOAT"), ("longitude", "FLOAT"), ("resolution", "VARCHAR(16)"), ("orientation", "VARCHAR(16) NOT NULL DEFAULT 'landscape'"), ("size_inches", "VARCHAR(8)"), ("theme_bg", "VARCHAR(16)"), ("theme_text", "VARCHAR(16)"), ("theme_accent", "VARCHAR(16)"), ("theme_ticker_bg", "VARCHAR(16)"), ("theme_ticker_text", "VARCHAR(16)"), ("theme_font", "VARCHAR(120)"), ("background_mode", "VARCHAR(16) NOT NULL DEFAULT 'color'"), ("background_image_id", "INTEGER"), ("background_fit", "VARCHAR(8) NOT NULL DEFAULT 'cover'")],
        "zones": [("bg_color", "VARCHAR(32)"), ("opacity", "FLOAT NOT NULL DEFAULT 1.0"), ("radius", "FLOAT NOT NULL DEFAULT 0"), ("padding", "FLOAT NOT NULL DEFAULT 0"), ("border_width", "FLOAT NOT NULL DEFAULT 0"), ("border_color", "VARCHAR(32)"), ("font_family", "VARCHAR(120)")],
        "overlays": [("anchor", "VARCHAR(16) NOT NULL DEFAULT ''"), ("margin", "FLOAT NOT NULL DEFAULT 2.0"), ("enter_anim", "VARCHAR(8) NOT NULL DEFAULT 'fade'"), ("exit_anim", "VARCHAR(8) NOT NULL DEFAULT 'fade'"), ("enter_at", "FLOAT NOT NULL DEFAULT 0"), ("duration", "FLOAT NOT NULL DEFAULT 0"), ("repeat_every", "FLOAT NOT NULL DEFAULT 0")],
        "campaigns": [("mode", "VARCHAR(16) NOT NULL DEFAULT 'scheduled'"), ("screen_ids", "TEXT"), ("screen_group_ids", "TEXT"), ("zone_ids", "TEXT"), ("start_at", "DATETIME"), ("end_at", "DATETIME"), ("priority", "INTEGER NOT NULL DEFAULT 0"), ("weight", "INTEGER NOT NULL DEFAULT 1"), ("enabled", "BOOLEAN NOT NULL DEFAULT 1"), ("max_plays_per_hour", "INTEGER"), ("company_id", "INTEGER"), ("updated_at", "DATETIME")],
        "datasets": [("kind", "VARCHAR(24) NOT NULL DEFAULT 'table'"), ("source_url", "VARCHAR(1024)"), ("columns", "TEXT"), ("rows", "TEXT"), ("fallback_rows", "TEXT"), ("refresh_status", "VARCHAR(16) NOT NULL DEFAULT 'idle'"), ("refresh_note", "TEXT"), ("last_refresh_at", "DATETIME"), ("expires_at", "DATETIME"), ("company_id", "INTEGER"), ("updated_at", "DATETIME")],
        "audit_logs": [("company_id", "INTEGER")],
        "play_events": [("company_id", "INTEGER"), ("is_ad", "BOOLEAN NOT NULL DEFAULT 0")],
        "report_schedules": [("recipients", "TEXT NOT NULL DEFAULT ''"), ("frequency", "VARCHAR(16) NOT NULL DEFAULT 'daily'"), ("hour", "INTEGER NOT NULL DEFAULT 8"), ("days", "INTEGER NOT NULL DEFAULT 7"), ("screen_slug", "VARCHAR(32)"), ("enabled", "BOOLEAN NOT NULL DEFAULT 1"), ("last_sent_at", "DATETIME"), ("company_id", "INTEGER"), ("updated_at", "DATETIME")],
    }

    with engine.begin() as conn:
        existing_tables = {
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table, cols in additions.items():
            if table not in existing_tables:
                continue
            present = {
                r[1]
                for r in conn.exec_driver_sql(
                    "PRAGMA table_info(" + table + ")"
                ).fetchall()
            }
            for name, ddl in cols:
                if name not in present:
                    conn.exec_driver_sql(
                        "ALTER TABLE " + table + " ADD COLUMN " + name + " " + ddl
                    )

        if "screens" in existing_tables:
            present = {
                r[1]
                for r in conn.exec_driver_sql(
                    "PRAGMA table_info(screens)"
                ).fetchall()
            }
            if "pair_code" in present:
                conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_screens_pair_code "
                    "ON screens(pair_code)"
                )
                used = {
                    r[0]
                    for r in conn.exec_driver_sql(
                        "SELECT pair_code FROM screens WHERE pair_code IS NOT NULL"
                    ).fetchall()
                }
                rows = conn.exec_driver_sql(
                    "SELECT id FROM screens WHERE pair_code IS NULL"
                ).fetchall()
                for (screen_id,) in rows:
                    code = "".join(secrets.choice("0123456789") for _ in range(6))
                    while code in used:
                        code = "".join(secrets.choice("0123456789") for _ in range(6))
                    used.add(code)
                    conn.exec_driver_sql(
                        "UPDATE screens SET pair_code = '" + code
                        + "' WHERE id = " + str(int(screen_id))
                    )


def init_db() -> None:
    """Cria todas as tabelas declaradas nos modelos, se ainda não existirem.

    Importa o módulo de modelos dentro da função para evitar import circular
    e, em seguida, chama ``Base.metadata.create_all``.
    """
    from . import models  # noqa: F401  (registra os modelos na metadata)

    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()
