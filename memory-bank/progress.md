# Progress

## Completed

- React dashboard shell and the eight-screen UI structure.
- Session auth, RSS CRUD/checking, persistent release queue, rule creation, and RSS feed deletion.
- Alembic migrations through `20260825_06` applied locally.
- Automated RSS scheduler, rule categories/seed thresholds/actions, qBittorrent and Telegram integration APIs, and audit persistence.
- Typed frontend API support for downloads, audit history, integration status, and qBittorrent/Telegram connection tests.
- API-bound Downloads, History, Notifications, and Settings screens with loading, error, empty, unconfigured, and connection-test states.
- Synology-oriented Docker Compose with migration startup, health checks, persistent SQLite volumes, and rotating consistent SQLite backups.
- Integration tests for RSS rule actions, qBittorrent, Telegram, Downloads, and audit events.
- Production review findings resolved: runtime Alembic URL, database readiness, credentials validation, safe Docker build contexts, backup safety, isolated test database, scheduler timezone handling, and recovery instructions.
- Persistent category catalog, colors, default Releases filter, and Settings management are complete and verified.
- Root README with local setup, configuration, verification, and MVP status.
- Backend tests (17) and frontend production build pass at the latest implementation checkpoint.
- Reusable `scripts/setup-docker-env.sh` wizard is ready for hidden-input local `.env` setup before Docker Compose deployment.
- Exposed Telegram token was redacted from all reachable Git history and rewritten `main` was force-pushed to GitHub.
- Runtime schema creation was removed in favour of an idempotent Alembic startup upgrade; qBittorrent/Telegram adapters and rule matching now have 26 automated backend tests.
- Multi-architecture GHCR build CI and a Synology deployment runbook, including named-volume and bind-mount permissions, are complete.
- Smart Auto-Add constraints, uploader lists, TorrentLeech flags, qBittorrent targets, per-feed proxy, disk alerts, and secret-free JSON/YAML configuration backup are implemented.

## Next

- Fix proxy credential persistence/export before using authenticated proxies; then add local HTTP/SOCKS adapter integration coverage and validate feed adapter types at API input.
- Install/start Docker Desktop, run `scripts/setup-docker-env.sh` to create `.env`, then run Docker Compose end-to-end and live qBittorrent/Telegram tests.
