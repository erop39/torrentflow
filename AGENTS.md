# TorrentFlow agent guide

## Memory Bank

Before planning, debugging, reviewing, or changing this project, read `memory-bank/projectbrief.md`, `productContext.md`, `systemPatterns.md`, `techContext.md`, `activeContext.md`, and `progress.md`.

After a material change, update `activeContext.md` and `progress.md` in the same change. Record durable architecture or workflow decisions in `systemPatterns.md`. Keep the bank concise, factual, and free of credentials, tokens, passwords, RSS keys, database URLs, or copied implementation blocks.

## Verification

- Backend: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` from `backend/`.
- Frontend: `npm run build` from `frontend/`.
- Log user-visible changes in `CHANGELOG.md`.
