"""create feeds table

Revision ID: 20260824_01
Revises:
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260824_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feeds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("adapter_type", sa.String(length=32), nullable=False, server_default="generic_rss"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("feeds")
