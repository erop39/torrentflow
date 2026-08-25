"""add release matching fields"""
from alembic import op
import sqlalchemy as sa

revision = "20260824_04"
down_revision = "20260824_03"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("releases", sa.Column("matched_rule_id", sa.Integer(), nullable=True))
    op.add_column("releases", sa.Column("status", sa.String(16), nullable=False, server_default="new"))

def downgrade() -> None:
    op.drop_column("releases", "status")
    op.drop_column("releases", "matched_rule_id")
