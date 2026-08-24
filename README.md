# Download/Cache Platform

A self-hosted private download and cache platform for a small group of
authorised users. It wraps [qBittorrent](https://github.com/qbittorrent/qBittorrent)
behind a REST API, tracks jobs and cached files in PostgreSQL, evicts old
files automatically once storage fills up, and serves everything through an
authenticated, range-request-capable file API — with a Next.js dashboard on
top.

## Architecture

```
Next.js dashboard  →  FastAPI API  →  PostgreSQL
                              │
                              ├─ DownloadProvider  → qBittorrent (Web API)
                              ├─ StorageProvider    → local disk (persistent volume)
                              ├─ CacheProvider       → eviction policy over DB metadata
                              └─ StreamProvider      → authenticated range-request file serving
```

The API never talks to qBittorrent, the filesystem, or the cache directly —
everything goes through a small provider interface (`backend/app/providers/`)
so a second download engine, an object-storage backend, or a CDN can be
added later without touching job/cache logic.

## Features

- Admin + regular user accounts, JWT session cookies, and revocable API keys
  for scripts/other applications (`POST /api/api-keys`).
- Persistent download jobs (create/pause/resume/retry/cancel/delete) that
  survive an API restart — startup reconciliation re-attaches to whatever
  qBittorrent is still doing.
- Automatic cache eviction once storage crosses `CACHE_EVICTION_THRESHOLD`,
  oldest-accessed-first, never touching protected/streaming/recently-used
  files (`MAX_STORAGE_GB`, `CACHE_RETENTION_DAYS`).
- Authenticated, range-request file serving (seekable, streamed in fixed
  chunks — never loads a whole file into memory) with no client-controlled
  filesystem paths.
- Real-time job progress and system metrics over Server-Sent Events, not
  polling.
- `/health` and `/api/system/status` report real component health (DB,
  qBittorrent, storage, background workers), backed by structured logs and
  DB-persisted system/audit event logs the dashboard's System page reads.
- Full OpenAPI docs at `/docs` on the API.

## Testing

Both halves have their own check suite — see
[`backend/README.md`](backend/README.md#tests) and
[`frontend/README.md`](frontend/README.md#checks) for exact commands. The
backend's integration suite runs against a real PostgreSQL and a real
qBittorrent instance (not mocks): real job lifecycle, real startup recovery,
real cache eviction on disk, real authenticated file streaming.

## Repository layout

```
backend/    FastAPI + SQLAlchemy + Alembic + PostgreSQL — see backend/README.md
frontend/   Next.js + TypeScript dashboard — see frontend/README.md
docs/       Deployment and operational docs
docker-compose.yml
.env.example
```

## Quick start

```bash
cp .env.example .env   # edit secrets, storage paths, cache limits
docker compose up -d --build
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full deployment guide,
environment variable reference, and operational notes (backups, recovery,
reverse proxy/TLS).

For local development without Docker, see `backend/README.md` and
`frontend/README.md`.
