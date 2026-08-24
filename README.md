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
