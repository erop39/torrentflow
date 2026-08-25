"""create stored releases"""
from alembic import op
import sqlalchemy as sa

revision = "20260824_03"
down_revision = "20260824_02"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("releases", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("feed_id", sa.Integer(), nullable=False), sa.Column("external_id", sa.String(255), nullable=False, unique=True), sa.Column("title", sa.Text(), nullable=False), sa.Column("link", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_releases_feed_id", "releases", ["feed_id"])

def downgrade() -> None:
    op.drop_index("ix_releases_feed_id", table_name="releases")
    op.drop_table("releases")
