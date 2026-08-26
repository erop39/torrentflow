# Active context

Current focus: release handoff after final security review and the immediate v1.1 usability additions. Smart rules support TorrentLeech metadata conditions and qBittorrent routing; per-feed proxy, disk alerting, encrypted tracker credentials, configuration export/import, parsed release groups, configurable Telegram templates, and scan diagnostics are implemented.

Recent implementation: common proxy validation, strict adapter types, explicit matching inputs, extracted automation/configuration routes, encrypted write-only tracker cookie/passkey storage, persisted disk threshold, JSON/YAML export, local HTTP/SOCKS adapter integration tests, guessit parsing/grouping, configurable Telegram templates, filter APIs, and persisted feed scan runs. Alembic runs through `20260826_12`.

Known gaps: encryption-key rotation is not yet automated; preserve `TORRENTFLOW_ENCRYPTION_KEY` to decrypt stored tracker credentials. The accidentally exposed Telegram token was removed from Git history and the rewritten history was force-pushed, but the token must still be revoked and regenerated in BotFather before any live Telegram test. Docker Desktop must be installed and running before the local Compose test; `scripts/setup-docker-env.sh` is ready to create the untracked `.env` with hidden input.
