"""add smart auto-add rule constraints and qBittorrent targets"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_07"
down_revision = "20260825_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rules", sa.Column("freeleech_only", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("rules", sa.Column("double_upload_only", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("rules", sa.Column("max_size_bytes", sa.Integer(), nullable=True))
    op.add_column("rules", sa.Column("uploader_whitelist", sa.Text(), nullable=False, server_default=""))
    op.add_column("rules", sa.Column("uploader_blacklist", sa.Text(), nullable=False, server_default=""))
    op.add_column("rules", sa.Column("qb_category", sa.String(255), nullable=False, server_default=""))
    op.add_column("rules", sa.Column("save_path", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("rules", "save_path")
    op.drop_column("rules", "qb_category")
    op.drop_column("rules", "uploader_blacklist")
    op.drop_column("rules", "uploader_whitelist")
    op.drop_column("rules", "max_size_bytes")
    op.drop_column("rules", "double_upload_only")
    op.drop_column("rules", "freeleech_only")
