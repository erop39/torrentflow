# Active context

Current focus: release handoff after final static QA. Categories are persistent and selectable by rules; Settings controls their colors and default visibility, while credentials remain environment-only. Local `main` is clean and synchronized with GitHub `origin/main` at commit `61419f4`.

Recent implementation: RSS scheduler, persistent category/seed fields, `notify`/`auto_add`/`both` actions, qBittorrent and Telegram adapters, audit events, configurable release-category catalog/default filter, Alembic revision `20260825_06`, and typed frontend API methods for downloads, audit, integration status, connection tests, and categories.

Known gaps: the accidentally exposed Telegram token was removed from Git history and the rewritten history was force-pushed, but the token must still be revoked and regenerated in BotFather before any live Telegram test. Docker Desktop must be installed and running before the local Compose test; `scripts/setup-docker-env.sh` is ready to create the untracked `.env` with hidden input. A temporary Alembic verification database remains at `C:\Users\eGoR\AppData\Local\Temp\torrentflow-migration-final.db` because automated deletion was blocked by the shell safety policy.
