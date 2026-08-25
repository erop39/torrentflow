# System patterns

- FastAPI backend owns authentication, persistence, RSS polling, rule matching, integrations, and audit events.
- React/Vite frontend consumes typed JSON API contracts with session cookies.
- SQLite models are changed only with Alembic migrations; legacy local databases must be stamped/migrated, never deleted for schema repair.
- Rule evaluation is deterministic: enabled rules sorted by priority then id; the first matching rule wins. Comma-separated keywords are OR; seed minimum is a mandatory threshold.
- Release categories are persistent configuration records (name, color, and default visibility). Rules select configured categories; the Releases screen initially filters to categories marked interesting, while its temporary "All categories" view exposes the rest.
- Manual and scheduled RSS scans share `scan_feed` so their outcomes are identical.
- qBittorrent and Telegram adapters are optional and fail explicitly when their environment configuration is absent; adapter outcomes are persisted as audit events.
- Secrets are environment variables only. Memory Bank, SQLite exports, and UI logs must not expose them.
- Docker deployment runs Alembic against `TORRENTFLOW_DATABASE_URL` before the API starts, validates non-placeholder production session credentials, keeps SQLite in a named data volume, and creates rotating backups through SQLite's backup API rather than copying a live database file.
- User-visible changes are recorded in `CHANGELOG.md`.
