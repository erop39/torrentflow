"""add optional per-feed proxy URL"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_08"
down_revision = "20260826_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("feeds", sa.Column("proxy_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("feeds", "proxy_url")
