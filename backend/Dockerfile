FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY . .
RUN pip install --no-cache-dir .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TORRENTFLOW_DATABASE_URL=sqlite+aiosqlite:////data/torrentflow.db

EXPOSE 8000
CMD ["/bin/sh", "/app/docker-entrypoint.sh"]
