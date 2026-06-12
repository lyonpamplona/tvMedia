"""Configuração da camada de persistência com SQLAlchemy.

Expõe o ``engine``, a fábrica de sessões ``SessionLocal``, a ``Base``
declarativa usada pelos modelos e a dependência :func:`get_db`, consumida
pelos endpoints do FastAPI para obter uma sessão de banco por requisição.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
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
)

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
