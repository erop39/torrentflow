"""persist RSS scan outcomes for feed health diagnostics"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_11"
down_revision = "20260826_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feed_scan_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_releases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feed_scan_runs_feed_started", "feed_scan_runs", ["feed_id", "started_at"])
    op.create_index("ix_feed_scan_runs_status_started", "feed_scan_runs", ["status", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_feed_scan_runs_status_started", table_name="feed_scan_runs")
    op.drop_index("ix_feed_scan_runs_feed_started", table_name="feed_scan_runs")
    op.drop_table("feed_scan_runs")
