# Deployment

Target: a single Ubuntu/Debian VPS running Docker Compose. No Kubernetes,
no bundled reverse proxy — this stays deliberately simple.

## Prerequisites

- Docker Engine + the Compose plugin (`docker compose version` should work).
- A persistent disk with enough room for `MAX_STORAGE_GB` worth of downloads.

## First deploy

```bash
git clone <this-repo> && cd <this-repo>
cp .env.example .env
# edit .env: at minimum set POSTGRES_PASSWORD, JWT_SECRET_KEY,
# FIRST_ADMIN_PASSWORD, and QBITTORRENT_PASSWORD (see below)

docker compose up -d --build
```

This starts four services: `postgres`, `qbittorrent`, `api`, `dashboard`.
The `api` container runs `alembic upgrade head` before starting, so the
schema is created automatically on first boot — no manual migration step.

### qBittorrent's WebUI password

qBittorrent generates a random temporary WebUI password on first start and
prints it to its logs:

```bash
docker compose logs qbittorrent | grep -i password
```

Log into qBittorrent's WebUI once (it isn't published outside the compose
network by default — see "Reaching qBittorrent's own WebUI" below) and set
a fixed username/password under *Tools → Options → Web UI*, then put that
same password in `.env` as `QBITTORRENT_PASSWORD` and restart the `api`
service (`docker compose restart api`). Until this is done, the API can't
authenticate to qBittorrent and `/api/system/status` will report it `down`.

### First login

Visit `http://<server>:3000` (or `DASHBOARD_PORT` if you changed it) and log
in with `FIRST_ADMIN_USERNAME`/`FIRST_ADMIN_PASSWORD` from `.env`. This
account is created automatically the first time the `api` container starts
against an empty `users` table — change the password via the Users page (or
create a new admin and disable this one) once you're in.

## Reverse proxy / TLS

Nothing here terminates TLS or owns a domain — that's intentionally left to
whatever you already run in front of this VPS (nginx, Caddy, Traefik,
Cloudflare Tunnel, ...), since assuming one would fight an existing setup
more often than it'd help. Two upstreams to point at:

- `dashboard` container, port 3000 — the web UI. Proxy your public domain's
  `/` here.
- `api` container, port 8000 — for API-key-authenticated scripts/apps that
  can't go through the dashboard. Proxy e.g. `api.yourdomain.com` or
  `yourdomain.com/api` here, or just leave it unpublished by removing the
  `ports:` entry on `api` in `docker-compose.yml` if nothing needs direct
  access.

Once you have a real TLS-terminating proxy in front, set `COOKIE_SECURE=true`
in `.env` (the default) so session cookies get the `Secure` flag. Only set
it `false` for plain-HTTP local testing.

A minimal Caddy example, if you don't already have one:

```caddyfile
yourdomain.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy localhost:3000
}
```

## Reaching qBittorrent's own WebUI

qBittorrent's WebUI isn't published to the host by default — the `api`
container is the only thing that talks to it, over the internal Docker
network, so there's one less exposed unauthenticated-by-default surface to
worry about. If you want occasional direct access (debugging, manually
inspecting a torrent), add a port mapping to the `qbittorrent` service in
`docker-compose.yml`:

```yaml
  qbittorrent:
    ports:
      - "127.0.0.1:8080:8080"   # bind to localhost only; SSH-tunnel in
```

## Backups

Two things need backing up:

- **Postgres** (`postgres_data` volume) — all users, jobs, cache metadata,
  audit/event logs. `docker compose exec postgres pg_dump -U postgres
  downloadcache | gzip > backup-$(date +%F).sql.gz` on a cron job is enough
  for most single-VPS setups.
- **`downloads_data` volume** — the actual cached files. Back this up like
  any other data directory (`docker volume inspect downloads_data` for its
  host path, then your usual file-level backup tool). Depending on
  `MAX_STORAGE_GB` this can be large; whether it's worth backing up at all
  vs. just re-downloading is a judgment call.

`qbittorrent_config` is small and mostly recreatable, but back it up too if
you've done nontrivial WebUI configuration.

## Surviving restarts (the actual requirement, not just a checkbox)

- **Container restart / server reboot**: `restart: unless-stopped` on every
  service means Docker brings everything back on daemon start. Postgres and
  qBittorrent both persist to named volumes, so no data is lost.
- **API restart**: on boot, `JobService.reconcile_on_startup()` re-attaches
  to whatever qBittorrent is still doing for every job that was
  `queued`/`downloading`/`paused`/`processing` when the process went down —
  it doesn't re-create torrents, it re-discovers the existing ones by the
  hash stored in `jobs.external_id`. A job qBittorrent no longer knows about
  (lost before the download engine assigned an id, or genuinely missing) is
  marked `failed` with an explanation rather than silently disappearing.
- **qBittorrent restart**: it reloads its own resume data from `/config`
  independently; the API's next poll tick (`POLL_INTERVAL_SECONDS`) just
  picks its state back up.

This is exercised by real integration tests against a live Postgres +
qBittorrent (`backend/app/tests/integration/test_job_recovery.py`), not
mocked.

## Updating

```bash
git pull
docker compose up -d --build
```

Alembic migrations run automatically on `api` container start, forward-only.
There's no automatic rollback — if a migration needs undoing, restore the
`postgres_data` backup from before the update.

## Environment reference

See [`.env.example`](../.env.example) — every variable is documented inline
there, including the cache eviction knobs (`MAX_STORAGE_GB`,
`CACHE_EVICTION_THRESHOLD`, `CACHE_RETENTION_DAYS`) and auth secrets.

## Local development without Docker

See [`backend/README.md`](../backend/README.md) and
[`frontend/README.md`](../frontend/README.md).
