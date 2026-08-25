# Active context

Current focus: release handoff after configurable categories. Categories are persistent and selectable by rules; Settings controls their colors and default visibility, while credentials remain environment-only.

Recent implementation: RSS scheduler, persistent category/seed fields, `notify`/`auto_add`/`both` actions, qBittorrent and Telegram adapters, audit events, configurable release-category catalog/default filter, Alembic revision `20260825_06`, and typed frontend API methods for downloads, audit, integration status, connection tests, and categories.

Known gaps: live qBittorrent/Telegram credentials are intentionally not available in the workspace, so their production reachability needs a post-deploy administrator check. A desktop/mobile visual QA of authenticated screens remains before release. A local dev backend is running on `127.0.0.1:8000`. A temporary Alembic verification database remains at `C:\Users\eGoR\AppData\Local\Temp\torrentflow-migration-final.db` because automated deletion was blocked by the shell safety policy.
