# Active context

Current focus: pre-deployment validation. Smart rules support TorrentLeech metadata conditions and qBittorrent routing; per-feed proxy, disk alerting, encrypted tracker credentials, configuration export/import, parsed release groups, configurable Telegram templates, filtering APIs, and scan diagnostics are implemented.

Recent implementation: security-review fixes in `c26abb5` and operational additions in `602e0e0`; backend verification is 51 passing tests and the frontend production build passes. Alembic runs through `20260826_12`.

Known gaps: encryption-key rotation is not yet automated; preserve `TORRENTFLOW_ENCRYPTION_KEY` to decrypt stored tracker credentials. The accidentally exposed Telegram token was removed from Git history and the rewritten history was force-pushed, but the token must still be revoked and regenerated in BotFather before any live Telegram test. Docker Desktop must be installed and running before the local Compose test; `scripts/setup-docker-env.sh` is ready to create the untracked `.env` with hidden input.
