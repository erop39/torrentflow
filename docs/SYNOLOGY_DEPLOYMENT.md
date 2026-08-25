# Deploying TorrentFlow on Synology

This guide deploys TorrentFlow through Synology Container Manager using the included Compose file. It applies to both x86_64 and ARM64 NAS models: the GitHub Actions workflow publishes matching multi-architecture backend and frontend images to GitHub Container Registry (GHCR).

TorrentFlow is intended for a trusted LAN. Do not expose it directly to the public Internet. Put it behind an authenticated reverse proxy and HTTPS before remote access.

## Prerequisites

- DSM with **Container Manager** installed and running.
- An administrator account that can create projects and, if using SSH, run `sudo`.
- The repository files, including `docker-compose.yml` and `.env.example`.
- A unique administrator password (at least 12 characters) and a random session secret (at least 32 characters).

Use the current image release rather than a branch if you need repeatable upgrades. The CI workflow pushes `main`, version-tag, and immutable `sha-...` tags for both `torrentflow-backend` and `torrentflow-frontend` to GHCR.

## Prepare the project

1. Create a project directory, for example `/volume1/docker/torrentflow`, and copy the repository contents into it. Keep the directory private: it will contain `.env`.
2. In that directory, copy `.env.example` to `.env`. Do not add `.env` to Git, shared folders, screenshots, or support tickets.
3. Set these required values in `.env`:

   ```dotenv
   TORRENTFLOW_ADMIN_PASSWORD=use-a-unique-password-of-12-or-more-characters
   TORRENTFLOW_SESSION_SECRET=use-a-random-secret-of-32-or-more-characters
   TORRENTFLOW_COOKIE_SECURE=false
   ```

   Generate the session secret on the NAS with `openssl rand -hex 32`, then paste only the output into `.env`. Set `TORRENTFLOW_COOKIE_SECURE=true` only after HTTPS is serving TorrentFlow.
4. Add qBittorrent and Telegram values only when you enable rules that use those integrations. Rotate any Telegram token that was ever committed or shared.

The repository's `scripts/setup-docker-env.sh` can create this file interactively from Git Bash or an SSH shell and hides secret input.

## Choose an image source

### Build on the NAS

This is the default in `docker-compose.yml`. It is simplest for a first test but can be slow and memory-intensive on smaller NAS devices. In Container Manager, create a Project and select the copied directory; Container Manager reads `docker-compose.yml` and builds the images.

### Pull the CI-built images

For an ARM NAS or a repeatable deployment, use the multi-architecture images built by GitHub Actions. In the project directory, create a local, uncommitted `docker-compose.images.yml` with the following content, replacing the tag with a reviewed release tag or immutable SHA tag:

```yaml
services:
  backend:
    image: ghcr.io/erop39/torrentflow-backend:main
    pull_policy: always
  frontend:
    image: ghcr.io/erop39/torrentflow-frontend:main
    pull_policy: always
  backup:
    image: ghcr.io/erop39/torrentflow-backend:main
    pull_policy: always
```

Deploy with both files selected in Container Manager, or over SSH:

```sh
cd /volume1/docker/torrentflow
sudo docker compose -f docker-compose.yml -f docker-compose.images.yml pull
sudo docker compose -f docker-compose.yml -f docker-compose.images.yml up -d
```

GHCR packages must be public for unauthenticated NAS pulls. If you keep them private, authenticate Docker to `ghcr.io` with a GitHub fine-grained token limited to `read:packages`; never put that token in Compose or `.env`.

## Start and verify

In Container Manager, create/start the Project. Over SSH the equivalent is:

```sh
cd /volume1/docker/torrentflow
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=100 backend
```

The backend applies Alembic migrations before it becomes healthy. Wait until its health check is healthy, then open `http://<NAS-IP>:4175` from the LAN and sign in. Do not remove a database volume to fix a migration problem; startup manages migrations.

Useful checks:

```sh
sudo docker compose ps
sudo docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/ready').read().decode())"
sudo docker compose logs --tail=100 backup
```

## Storage and volume permissions

By default, the Compose file uses Docker-managed named volumes:

- `torrentflow-data` stores `torrentflow.db`.
- `torrentflow-backups` stores consistent `torrentflow-*.db` snapshots.

They are intentionally not mapped into a shared DSM folder. Containers in the provided images run as root, so Docker creates and uses these volumes with the expected ownership. This avoids the common Synology UID/GID mismatch. Do **not** change ownership inside Docker's internal volume directory (`/var/lib/docker/volumes`) or delete either volume during upgrades.

Inspect the actual location and mount points only through Docker:

```sh
sudo docker volume ls | grep torrentflow
sudo docker volume inspect torrentflow-data torrentflow-backups
```

### Optional bind mounts

Use bind mounts only if you need backups visible in File Station. Stop the project first, create dedicated private folders, then ensure they are writable by the root process used by the supplied containers:

```sh
sudo install -d -m 700 -o root -g root /volume1/docker/torrentflow-data
sudo install -d -m 700 -o root -g root /volume1/docker/torrentflow-backups
```

Create a local override file, `docker-compose.bind-mounts.yml`, and do not commit it:

```yaml
services:
  backend:
    volumes:
      - /volume1/docker/torrentflow-data:/data
  backup:
    volumes:
      - /volume1/docker/torrentflow-data:/data:ro
      - /volume1/docker/torrentflow-backups:/backups
```

Start with all applicable Compose files, for example:

```sh
sudo docker compose -f docker-compose.yml -f docker-compose.bind-mounts.yml up -d --build
```

Keep the data and backup directories at mode `0700`; they contain operational release and audit data. Do not use `chmod 777`. If a future image is configured with a non-root user, change ownership to that image's documented numeric UID:GID instead of guessing or broadening permissions.

## Backup, restoration, and upgrades

The `backup` service creates SQLite-consistent snapshots; its interval and retention are set in `.env`. Check it after first startup and periodically:

```sh
sudo docker compose logs --tail=100 backup
```

To restore, stop the project, replace `torrentflow.db` with a selected snapshot in the same data volume/bind mount, preserve the name and private permissions, then start the project. Test restoration using a copy before an incident.

Before upgrading, make a verified backup, then pull/copy the new project files and run:

```sh
sudo docker compose pull
sudo docker compose up -d --build
sudo docker compose ps
```

For CI-built images use the same command with `-f docker-compose.images.yml` as in the pull section. Never run `docker compose down -v` for an upgrade: the `-v` flag deletes the database and backups.

## HTTPS and exposure

For Synology Reverse Proxy, forward an HTTPS hostname to `http://127.0.0.1:4175` (or to the NAS LAN address and port if loopback is unavailable). Enable HSTS and a valid certificate in DSM, set `TORRENTFLOW_COOKIE_SECURE=true`, recreate the frontend/backend containers, and verify that login still works over HTTPS. Keep the raw port restricted to the LAN.

## Troubleshooting

- **Backend is unhealthy:** inspect `sudo docker compose logs backend`; a weak or placeholder session credential prevents production startup by design.
- **Permission denied with bind mounts:** stop the project, verify the exact host paths and `root:root` ownership/mode `0700`, then start again. Do not modify Docker's managed volume directory.
- **An ARM NAS cannot pull an image:** verify the workflow completed and use a current `main`, release, or `sha-...` tag; both `linux/amd64` and `linux/arm64` are published.
- **No backups:** inspect the `backup` service logs and ensure its target volume/folder has not been replaced with a read-only mount.
