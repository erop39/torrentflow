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
- Smart Auto-Add constraints, uploader lists, TorrentLeech flags, qBittorrent targets, per-feed proxy, disk alerts, and JSON/YAML configuration backup are implemented.
- README, changelog, and TODO were reconciled with current functionality and review findings.
- Final review findings were closed: proxy userinfo is rejected and legacy values scrubbed by migration; adapter types and proxy validation are centralized; matching has an explicit API; automation/configuration routes are extracted from `main.py`; tracker credentials are Fernet-encrypted and excluded from backups; disk threshold joins portable settings; JSON/YAML export and local HTTP/SOCKS adapter tests are available.
- Immediate follow-up features are complete: best-effort release parsing/grouping, safe Telegram templates, filtered/paginated release and audit APIs, and persisted feed scan run diagnostics.

## Next

- Install/start Docker Desktop, run `scripts/setup-docker-env.sh` to create `.env`, then run Docker Compose end-to-end and live qBittorrent/Telegram tests.
- Plan encryption-key rotation before long-lived tracker credentials are used broadly.
