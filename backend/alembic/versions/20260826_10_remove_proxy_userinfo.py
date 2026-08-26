"""remove legacy proxy URLs that may contain credentials

Proxy authentication must be configured outside TorrentFlow.  Older releases
allowed ``scheme://user:password@host`` values, so null them during upgrade
instead of retaining an exportable credential in SQLite.
"""

from alembic import op


revision = "20260826_10"
down_revision = "20260826_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE feeds SET proxy_url = NULL WHERE proxy_url LIKE '%://%@%'")


def downgrade() -> None:
    # Redacted credentials cannot and must not be restored.
    pass
