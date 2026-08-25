"""add automation and integration fields"""
from alembic import op
import sqlalchemy as sa

revision = "20260825_05"
down_revision = "20260824_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("feeds", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rules", sa.Column("category", sa.String(32), nullable=False, server_default="series"))
    op.add_column("releases", sa.Column("category", sa.String(32), nullable=False, server_default="series"))
    op.add_column("releases", sa.Column("seeds", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("audit_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("release_id", sa.Integer(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_column("releases", "seeds")
    op.drop_column("releases", "category")
    op.drop_column("rules", "category")
    op.drop_column("feeds", "last_checked_at")
