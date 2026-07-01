"""L6: tabela de ad-breaks recorrentes/agendados.

Cria ``ad_break_schedules`` quando ausente, de forma idempotente e
agnostica de dialeto (usa ``sa.inspect`` para nao falhar se a tabela ja
existir -- por exemplo, em bancos SQLite criados via ``create_all``).

Revision ID: 0003_ad_break_schedules
Revises: 0002_live_graphics
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_ad_break_schedules"
down_revision = "0002_live_graphics"
branch_labels = None
depends_on = None

TABLE = "ad_break_schedules"


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if _has_table(TABLE):
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, server_default="Ad-break"),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("screen_id", sa.Integer(), nullable=True),
        sa.Column("media_id", sa.Integer(), nullable=True),
        sa.Column("every_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("start_time", sa.String(length=5), nullable=False, server_default="00:00"),
        sa.Column("end_time", sa.String(length=5), nullable=False, server_default="23:59"),
        sa.Column("days", sa.String(length=16), nullable=False, server_default="0123456"),
        sa.Column("enter_anim", sa.String(length=8), nullable=False, server_default="fade"),
        sa.Column("exit_anim", sa.String(length=8), nullable=False, server_default="fade"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["screen_id"], ["screens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_ad_break_schedules_company_id", TABLE, ["company_id"]
    )
    op.create_index(
        "ix_ad_break_schedules_screen_id", TABLE, ["screen_id"]
    )


def downgrade() -> None:
    if not _has_table(TABLE):
        return
    op.drop_index("ix_ad_break_schedules_screen_id", table_name=TABLE)
    op.drop_index("ix_ad_break_schedules_company_id", table_name=TABLE)
    op.drop_table(TABLE)
