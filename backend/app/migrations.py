"""Application startup helpers for the Alembic schema lifecycle.

The API never creates ORM tables directly.  Every database, including a new
local development database, is brought to the revision recorded by Alembic.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config

from .database import DATABASE_URL


def upgrade_database() -> None:
    """Apply all schema migrations to the configured database.

    Alembic runs synchronously while the application is starting.  Its normal
    engine does not support SQLAlchemy's async driver suffix, so preserve the
    database target while converting ``sqlite+aiosqlite`` to ``sqlite``.
    """
    backend_root = Path(__file__).resolve().parent.parent
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+aiosqlite", ""))
    command.upgrade(config, "head")
