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
        "users": [("company_id", "INTEGER"), ("is_super_admin", "BOOLEAN NOT NULL DEFAULT 0")],
        "media_folders": [("company_id", "INTEGER")],
        "media": [("company_id", "INTEGER")],
        "playlists": [("company_id", "INTEGER")],
        "screens": [("pair_code", "VARCHAR(12)"), ("sync_group", "VARCHAR(64)")],
        "audit_logs": [("company_id", "INTEGER")],
        "play_events": [("company_id", "INTEGER")],
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
