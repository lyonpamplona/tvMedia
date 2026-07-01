"""Revisao incremental: graficos ao vivo, cue points e anuncios (L1-L5).

Aplica, de forma idempotente e independente de dialeto (SQLite/PostgreSQL), o
delta de esquema introduzido pelas fases de Live Graphics:

* ``overlays``    -> ancora/margem/animacoes/temporizacao (L1).
* ``campaigns``   -> ``weight`` para o rodizio ponderado de anuncios (L5).
* ``play_events`` -> ``is_ad`` para separar exibicoes de anuncio (L5).
* ``media_cues``  -> nova tabela de cue points sincronizados ao video (L3/L5).

Diferente da 0001 (``create_all``), esta revisao usa operacoes explicitas e so
aplica o que ainda falta, permitindo atualizar bancos PostgreSQL ja existentes
sem recriar tabelas. Em SQLite a migracao leve de ``database.py`` ja cobre o
mesmo delta; ainda assim, rodar ``alembic upgrade head`` aqui e seguro (no-op).

Revision ID: 0002_live_graphics
Revises: 0001_initial
Create Date: 2026-06-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_live_graphics"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _columns(inspector, table: str) -> set[str]:
    """Nomes de colunas existentes em ``table`` (vazio se a tabela nao existe)."""
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


# Delta de colunas por tabela (idempotente: so adiciona o que faltar).
_ADDITIONS: dict[str, list[tuple[str, sa.Column]]] = {
    "overlays": [
        ("anchor", sa.Column("anchor", sa.String(16), nullable=False, server_default="")),
        ("margin", sa.Column("margin", sa.Float(), nullable=False, server_default="2.0")),
        ("enter_anim", sa.Column("enter_anim", sa.String(8), nullable=False, server_default="fade")),
        ("exit_anim", sa.Column("exit_anim", sa.String(8), nullable=False, server_default="fade")),
        ("enter_at", sa.Column("enter_at", sa.Float(), nullable=False, server_default="0")),
        ("duration", sa.Column("duration", sa.Float(), nullable=False, server_default="0")),
        ("repeat_every", sa.Column("repeat_every", sa.Float(), nullable=False, server_default="0")),
    ],
    "campaigns": [
        ("weight", sa.Column("weight", sa.Integer(), nullable=False, server_default="1")),
    ],
    "play_events": [
        ("is_ad", sa.Column("is_ad", sa.Boolean(), nullable=False, server_default=sa.false())),
    ],
}


def upgrade() -> None:
    """Adiciona colunas faltantes e cria a tabela ``media_cues`` se preciso."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table, columns in _ADDITIONS.items():
        present = _columns(inspector, table)
        if not present:
            continue  # tabela inexistente: 0001/create_all cuida do esquema novo
        for name, column in columns:
            if name not in present:
                op.add_column(table, column)

    if "media_cues" not in inspector.get_table_names():
        op.create_table(
            "media_cues",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "media_id",
                sa.Integer(),
                sa.ForeignKey("media.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("at_seconds", sa.Float(), nullable=False, server_default="0"),
            sa.Column("action", sa.String(16), nullable=False, server_default="show_gfx"),
            sa.Column("kind", sa.String(16), nullable=False, server_default="lowerthird"),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("slot_id", sa.String(32), nullable=False, server_default="cue"),
            sa.Column("anchor", sa.String(16), nullable=False, server_default="lower_third"),
            sa.Column("enter_anim", sa.String(8), nullable=False, server_default="slide"),
            sa.Column("exit_anim", sa.String(8), nullable=False, server_default="fade"),
            sa.Column("duration", sa.Float(), nullable=False, server_default="0"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    """Reverte o delta L1-L5 (remove media_cues e as colunas adicionadas)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "media_cues" in inspector.get_table_names():
        op.drop_table("media_cues")

    for table, columns in _ADDITIONS.items():
        present = _columns(inspector, table)
        for name, _column in columns:
            if name in present:
                op.drop_column(table, name)
