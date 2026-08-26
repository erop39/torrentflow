# System patterns

- FastAPI backend owns authentication, persistence, RSS polling, rule matching, integrations, and audit events.
- React/Vite frontend consumes typed JSON API contracts with session cookies.
- SQLite models are changed only with Alembic migrations; legacy local databases must be stamped/migrated, never deleted for schema repair.
- API startup applies `alembic upgrade head` idempotently for every environment; direct ORM `create_all` is not used at runtime.
- Rule evaluation is deterministic: enabled rules sorted by priority then id; the first matching rule wins. Comma-separated keywords are OR; seed minimum, freeleech/double-upload gates, maximum size, and uploader allow/block lists are mandatory constraints when configured.
- Release categories are persistent configuration records (name, color, and default visibility). Rules select configured categories; the Releases screen initially filters to categories marked interesting, while its temporary "All categories" view exposes the rest.
- Manual and scheduled RSS scans share `scan_feed` so their outcomes are identical.
- qBittorrent and Telegram adapters are optional and fail explicitly when their environment configuration is absent; adapter outcomes are persisted as audit events.
- Feed adapters may use a shared-validated per-feed HTTP(S)/SOCKS5 proxy. Proxy userinfo is forbidden, and migration `20260826_10` removes legacy persisted values containing it; authentication belongs in the proxy service. TorrentLeech extraction normalizes uploader, freeleech, double-upload, and size metadata for matching; matching qBittorrent actions can set a per-rule category and save path.
- Configuration export/import is versioned and excludes environment credentials; merge is the safe default and replace requires explicit confirmation. Disk monitoring emits audit/Telegram state transitions rather than repeatedly alerting every scheduler cycle.
- Integration secrets are environment variables only. Tracker cookies/passkeys are the explicit exception: write-only API inputs are Fernet-encrypted in a separate SQLite table with `TORRENTFLOW_ENCRYPTION_KEY`, never returned or exported, and deleted with their feed. Memory Bank, exports, and UI logs must not expose any plaintext secret.
- Docker deployment runs Alembic against `TORRENTFLOW_DATABASE_URL` before the API starts, validates non-placeholder production session credentials, keeps SQLite in a named data volume, and creates rotating backups through SQLite's backup API rather than copying a live database file.
- User-visible changes are recorded in `CHANGELOG.md`.
