# TorrentFlow

TorrentFlow is a LAN-first control room for RSS/Atom releases on a NAS. It scans feeds, evaluates priority rules, records decisions, can notify via Telegram, and can add matching releases to qBittorrent.

> Current state: active MVP development. The dashboard, RSS/rules/audit pipeline, optional integrations, and Synology-oriented Docker deployment are ready for verification.

## What works

- Single-admin session authentication.
- RSS feed creation, checking, scheduling, and deletion.
- Persistent release queue in SQLite.
- Priority rules with comma-separated keyword matching, minimum seed threshold, category, and actions: `notify`, `auto_add`, `both`.
- qBittorrent and Telegram integration adapters, configured through environment variables.
- Audit events for discoveries and integration outcomes.
- React dashboard with API-bound RSS feeds, Releases, Rules, Downloads, History, Notifications, and Settings screens.
- Docker Compose deployment with Alembic startup migrations, health checks, and rotating SQLite backups.

## Architecture

| Area | Technology |
| --- | --- |
| Backend | Python 3.12+, FastAPI, SQLAlchemy async, Alembic |
| Database | SQLite / aiosqlite |
| RSS and integrations | feedparser, httpx |
| Frontend | React, TypeScript, Vite, Lucide |

## Local development

Prerequisites: Python 3.12+ and Node.js 20+.

### 1. Configure the backend

From `backend/`, set environment variables. Use [`backend/.env.example`](backend/.env.example) as a reference; do not commit a populated environment file.

PowerShell example:

```powershell
cd backend
$env:TORRENTFLOW_ADMIN_PASSWORD = "choose-a-strong-password"
$env:TORRENTFLOW_SESSION_SECRET = "use-a-long-random-value"
```

Optional qBittorrent and Telegram variables are documented in `backend/.env.example`.

### 2. Apply migrations and start the API

```powershell
cd backend
python -m alembic -c alembic.ini upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`.

### 3. Start the frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 4175
```

Open `http://127.0.0.1:4175` and sign in with `TORRENTFLOW_ADMIN_PASSWORD`.

## First workflow

1. Open **RSS feeds** and add the full RSS URL.
2. Open **Rules** and create a rule with category, keywords, minimum seeds, action, and priority.
3. Click **Check now** on a feed.
4. Inspect persistent outcomes in **Releases**.
5. For `auto_add` or `both`, configure qBittorrent first. For `notify` or `both`, configure Telegram first.

## Synology / Docker Compose deployment

For Windows Git Bash or a NAS shell, [`scripts/setup-docker-env.sh`](scripts/setup-docker-env.sh) creates the untracked `.env` file with hidden secret input before deployment.

1. Copy `.env.example` to `.env` beside `docker-compose.yml`, then replace the two required session values. The deployment refuses placeholder values, passwords shorter than 12 characters, and session secrets shorter than 32 characters. Keep `.env` private.
2. In Synology Container Manager, create a project from this directory or run `docker compose up -d --build` over SSH.
3. Open `http://<NAS-IP>:4175`. The `backend` container runs Alembic migrations before accepting requests; `frontend` waits for its health check.
4. Persistent database data is stored in the `torrentflow-data` volume. The `backup` service writes rotating SQLite snapshots to `torrentflow-backups`; its retention and interval are controlled by the two backup variables in `.env`. Set `TORRENTFLOW_COOKIE_SECURE=true` when accessing TorrentFlow through HTTPS.

Do not manually copy the live SQLite database while TorrentFlow is running. The backup service uses SQLite's backup API so its snapshots are consistent.

For the complete Container Manager procedure—including multi-architecture GHCR images, volume ownership, bind-mount permissions, HTTPS, upgrades, and troubleshooting—see [Synology deployment](docs/SYNOLOGY_DEPLOYMENT.md). The default Docker-managed volumes avoid Synology UID/GID issues; do not delete them during upgrades.

### Restoring a backup

1. Stop the project in Container Manager so SQLite is not open.
2. Export the desired `torrentflow-*.db` file from the `torrentflow-backups` volume, or copy it inside the NAS volume store.
3. Replace `torrentflow.db` in the `torrentflow-data` volume with that snapshot, preserving the filename.
4. Start the project again. Startup runs Alembic against the restored database before the API accepts requests.

Test restoration on a copy before relying on it for incident recovery.

## Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `TORRENTFLOW_ADMIN_PASSWORD` | Yes | Local administrator password |
| `TORRENTFLOW_SESSION_SECRET` | Yes | Cookie signing secret |
| `TORRENTFLOW_QBITTORRENT_URL` | For qB | qBittorrent Web API base URL |
| `TORRENTFLOW_QBITTORRENT_USERNAME` | For qB | qBittorrent username |
| `TORRENTFLOW_QBITTORRENT_PASSWORD` | For qB | qBittorrent password |
| `TORRENTFLOW_TELEGRAM_BOT_TOKEN` | For Telegram | Telegram bot token |
| `TORRENTFLOW_TELEGRAM_CHAT_ID` | For Telegram | Target chat ID |

Never put passwords, RSS keys, tokens, or database URLs in committed files, screenshots, or the Memory Bank.

## Verification

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest -q

cd ..\frontend
npm run build
```

## Project context

- [CHANGELOG.md](CHANGELOG.md) — user-visible changes.
- [memory-bank](memory-bank) — concise project memory for humans and coding agents.
- [docs/UI_DESIGN_SPEC.md](docs/UI_DESIGN_SPEC.md) — approved interface contract.
- [backend/.env.example](backend/.env.example) — configuration reference.
- [.env.example](.env.example) — Docker Compose configuration reference.

## Roadmap

- Final UI QA on desktop and mobile, plus a live check against the administrator's qBittorrent and Telegram instances.
- Windows tray client in a later phase.
