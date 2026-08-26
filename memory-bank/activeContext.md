# Active context

Current focus: release handoff after closing the final security and architecture review. Smart rules support TorrentLeech metadata conditions and qBittorrent routing; per-feed proxy, disk alerting, encrypted tracker credentials, and versioned configuration export/import are implemented.

Recent implementation: common proxy validation, strict adapter types, explicit matching inputs, extracted automation/configuration routes, encrypted write-only tracker cookie/passkey storage, persisted disk threshold, JSON/YAML export, and local HTTP/SOCKS adapter integration tests. Alembic runs through `20260826_10`.

Known gaps: encryption-key rotation is not yet automated; preserve `TORRENTFLOW_ENCRYPTION_KEY` to decrypt stored tracker credentials. The accidentally exposed Telegram token was removed from Git history and the rewritten history was force-pushed, but the token must still be revoked and regenerated in BotFather before any live Telegram test. Docker Desktop must be installed and running before the local Compose test; `scripts/setup-docker-env.sh` is ready to create the untracked `.env` with hidden input.
