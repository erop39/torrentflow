#!/bin/sh
set -eu

mkdir -p /data
python -m alembic -c alembic.ini upgrade head
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
