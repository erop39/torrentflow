# Active context

Current focus: release handoff after final static QA. Smart rules support TorrentLeech metadata conditions and qBittorrent routing; per-feed proxy, disk alerting, and secret-free configuration export/import are implemented. Credentials remain environment-only.

Recent implementation: RSS scheduler, persistent category/seed fields, `notify`/`auto_add`/`both` actions, qBittorrent and Telegram adapters, audit events, configurable release-category catalog/default filter, Smart Auto-Add fields, TorrentLeech/proxy adapter support, disk monitoring, and configuration backup APIs. Alembic runs through `20260826_08`.

Known gaps: the accidentally exposed Telegram token was removed from Git history and the rewritten history was force-pushed, but the token must still be revoked and regenerated in BotFather before any live Telegram test. Docker Desktop must be installed and running before the local Compose test; `scripts/setup-docker-env.sh` is ready to create the untracked `.env` with hidden input. A temporary Alembic verification database remains at `C:\Users\eGoR\AppData\Local\Temp\torrentflow-migration-final.db` because automated deletion was blocked by the shell safety policy.
