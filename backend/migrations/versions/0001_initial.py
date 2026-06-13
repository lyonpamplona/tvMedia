"""Migração inicial: cria todas as tabelas a partir dos modelos ORM.

Esta revisão inicial materializa o esquema completo definido em
``app.models`` usando ``Base.metadata``. Manter a primeira revisão ancorada
nos metadados garante que o banco criado pelo Alembic seja idêntico ao criado
por ``init_db`` (``create_all``). Revisões seguintes devem usar operações
explícitas (``op.add_column`` etc.) geradas via ``alembic revision``.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-12
"""
from __future__ import annotations

from alembic import op  # noqa: F401  (mantido por convenção Alembic)

from app import models  # noqa: F401  (registra as tabelas em Base.metadata)
from app.database import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria todas as tabelas do esquema atual."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Remove todas as tabelas do esquema atual."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
