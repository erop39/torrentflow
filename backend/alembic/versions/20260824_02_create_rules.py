"""create rules table"""

from alembic import op
import sqlalchemy as sa

revision = "20260824_02"
down_revision = "20260824_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("rules", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False, unique=True), sa.Column("include_keywords", sa.Text(), nullable=False, server_default=""), sa.Column("min_seeds", sa.Integer(), nullable=False, server_default="0"), sa.Column("action", sa.String(16), nullable=False, server_default="notify"), sa.Column("priority", sa.Integer(), nullable=False, server_default="100"), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("rules")
