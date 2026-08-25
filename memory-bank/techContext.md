# Technical context

Backend: Python 3.12+, FastAPI, SQLAlchemy async, SQLite/aiosqlite, Alembic, httpx, feedparser, uvicorn.

Frontend: React, TypeScript, Vite, Lucide, local Inter and JetBrains Mono fonts.

Local URLs: frontend `http://127.0.0.1:4175`; backend `http://127.0.0.1:8000`.

Runtime configuration is documented in `backend/.env.example`. qBittorrent and Telegram are optional until relevant rules are enabled.

Verification: run backend pytest with plugin autoload disabled; run the Vite production build. Alembic revisions currently run through `20260825_06`. There is currently no Git repository in this workspace.
