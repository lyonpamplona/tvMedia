"""Customizacao de layout/cores/fontes/fundo da tela e estilo das zonas.

Adiciona, de forma idempotente e cross-dialect (SQLite/PostgreSQL):

* ``zones``   -> bg_color, opacity, radius, padding, border_width,
  border_color, font_family (estilo visual por zona no canvas da TV).
* ``screens`` -> theme_font, background_mode, background_image_id,
  background_fit (fonte e fundo da tela: cor/imagem/transparente).

Em SQLite, a migracao leve de ``database.py`` ja cobre o mesmo delta; rodar
``alembic upgrade head`` aqui continua seguro (no-op quando ja aplicado).

Revision ID: 0004_zone_screen_customization
Revises: 0003_ad_break_schedules
Create Date: 2026-06-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_zone_screen_customization"
down_revision = "0003_ad_break_schedules"
branch_labels = None
depends_on = None


def _columns(inspector, table: str) -> set[str]:
    """Nomes de colunas existentes em ``table`` (vazio se a tabela nao existe)."""
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


_ADDITIONS: dict[str, list[tuple[str, sa.Column]]] = {
    "zones": [
        ("bg_color", sa.Column("bg_color", sa.String(32), nullable=True)),
        ("opacity", sa.Column("opacity", sa.Float(), nullable=False, server_default="1.0")),
        ("radius", sa.Column("radius", sa.Float(), nullable=False, server_default="0")),
        ("padding", sa.Column("padding", sa.Float(), nullable=False, server_default="0")),
        ("border_width", sa.Column("border_width", sa.Float(), nullable=False, server_default="0")),
        ("border_color", sa.Column("border_color", sa.String(32), nullable=True)),
        ("font_family", sa.Column("font_family", sa.String(120), nullable=True)),
    ],
    "screens": [
        ("theme_font", sa.Column("theme_font", sa.String(120), nullable=True)),
        ("background_mode", sa.Column("background_mode", sa.String(16), nullable=False, server_default="color")),
        ("background_image_id", sa.Column("background_image_id", sa.Integer(), nullable=True)),
        ("background_fit", sa.Column("background_fit", sa.String(8), nullable=False, server_default="cover")),
    ],
}


def upgrade() -> None:
    """Adiciona as colunas de customizacao que ainda faltarem."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, columns in _ADDITIONS.items():
        present = _columns(inspector, table)
        if not present:
            continue  # tabela inexistente: create_all cuida do esquema novo
        for name, column in columns:
            if name not in present:
                op.add_column(table, column)


def downgrade() -> None:
    """Remove as colunas de customizacao adicionadas por esta revisao."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, columns in _ADDITIONS.items():
        present = _columns(inspector, table)
        for name, _column in columns:
            if name in present:
                op.drop_column(table, name)
