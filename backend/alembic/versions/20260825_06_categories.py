"""add configurable release categories"""

from alembic import op
import sqlalchemy as sa

revision = "20260825_06"
down_revision = "20260825_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(32), nullable=False, unique=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#ad8cff"),
        sa.Column("is_interesting", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.bulk_insert(sa.table("categories", sa.column("name", sa.String), sa.column("color", sa.String), sa.column("is_interesting", sa.Boolean)), [
        {"name": "series", "color": "#ad8cff", "is_interesting": True},
        {"name": "linux", "color": "#69e5a5", "is_interesting": True},
    ])


def downgrade() -> None:
    op.drop_table("categories")
