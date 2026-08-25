"""Create rotating SQLite backups without copying a live database file directly."""

import os
import sqlite3
import time
import logging
from datetime import UTC, datetime
from pathlib import Path


def database_path() -> Path:
    url = os.getenv("TORRENTFLOW_DATABASE_URL", "sqlite+aiosqlite:///./data/torrentflow.db")
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        raise RuntimeError("SQLite backups require TORRENTFLOW_DATABASE_URL to use sqlite+aiosqlite")
    return Path(url.removeprefix(prefix))


logger = logging.getLogger(__name__)


def backup_retention() -> int:
    retention = int(os.getenv("TORRENTFLOW_BACKUP_RETENTION", "7"))
    if retention < 1:
        raise ValueError("TORRENTFLOW_BACKUP_RETENTION must be at least 1")
    return retention


def create_backup() -> Path | None:
    source_path = database_path()
    if not source_path.exists():
        return None
    backup_dir = Path(os.getenv("TORRENTFLOW_BACKUP_DIR", "/backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backup_dir / f"torrentflow-{timestamp}.db"
    temporary = destination.with_suffix(".tmp")
    with sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True) as source, sqlite3.connect(temporary) as target:
        source.backup(target)
    temporary.replace(destination)
    retention = backup_retention()
    backups = sorted(backup_dir.glob("torrentflow-*.db"), reverse=True)
    for expired in backups[retention:]:
        expired.unlink()
    return destination


def main() -> None:
    interval = max(60, int(os.getenv("TORRENTFLOW_BACKUP_INTERVAL_SECONDS", "86400")))
    while True:
        try:
            created = create_backup()
            if created is not None:
                logger.info("Created SQLite backup at %s", created)
        except Exception:
            logger.exception("SQLite backup failed")
        time.sleep(interval)


if __name__ == "__main__":
    main()
