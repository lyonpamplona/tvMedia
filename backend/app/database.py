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


def init_db() -> None:
    """Cria todas as tabelas declaradas nos modelos, se ainda não existirem.

    Importa o módulo de modelos dentro da função para evitar import circular
    e, em seguida, chama ``Base.metadata.create_all``.
    """
    from . import models  # noqa: F401  (registra os modelos na metadata)

    Base.metadata.create_all(bind=engine)
