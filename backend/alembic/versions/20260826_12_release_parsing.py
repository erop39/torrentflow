"""persist best-effort release parsing and grouping fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_12"
down_revision = "20260826_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("releases", sa.Column("display_title", sa.Text(), nullable=False, server_default=""))
    op.add_column("releases", sa.Column("group_key", sa.String(length=200), nullable=False, server_default=""))
    op.add_column("releases", sa.Column("media_type", sa.String(length=16), nullable=False, server_default="unknown"))
    op.add_column("releases", sa.Column("parsed_series_title", sa.Text(), nullable=True))
    op.add_column("releases", sa.Column("parsed_season", sa.Integer(), nullable=True))
    op.add_column("releases", sa.Column("parsed_episode", sa.Integer(), nullable=True))
    op.add_column("releases", sa.Column("parsed_year", sa.Integer(), nullable=True))
    op.create_index("ix_releases_group_key", "releases", ["group_key"])


def downgrade() -> None:
    op.drop_index("ix_releases_group_key", table_name="releases")
    op.drop_column("releases", "parsed_year")
    op.drop_column("releases", "parsed_episode")
    op.drop_column("releases", "parsed_season")
    op.drop_column("releases", "parsed_series_title")
    op.drop_column("releases", "media_type")
    op.drop_column("releases", "group_key")
    op.drop_column("releases", "display_title")
