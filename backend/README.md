# Backend

FastAPI + SQLAlchemy (async) + Alembic + PostgreSQL. See the repo root
[`README.md`](../README.md) for the overall architecture.

## Local development (without Docker)

Requires Python 3.11+ and a running PostgreSQL instance.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp ../.env.example .env   # then edit: DATABASE_URL, QBITTORRENT_* to point
                          # at localhost instead of the compose service names,
                          # STORAGE_ROOT to a local directory you can write to

alembic upgrade head
uvicorn app.main:app --reload
```

You'll also need a real qBittorrent instance reachable at `QBITTORRENT_HOST`
— either `docker compose up qbittorrent` from the repo root, or a local
`qbittorrent-nox --webui-port=8080`.

API docs are auto-generated at `http://localhost:8000/docs`.

## Tests

```bash
ruff check .
mypy app
pytest app/tests/unit           # pure logic, no external services
pytest app/tests/integration    # needs a real Postgres + real qBittorrent —
                                 # see app/tests/conftest.py for the expected
                                 # connection details, or override via env vars
```

The integration suite exercises real job creation/pause/resume/cancel
against a live qBittorrent instance, real startup recovery, real cache
eviction on disk, and real authenticated range-request file serving — none
of it is mocked.

## Layout

```
app/
  core/        config, security (JWT/password hashing), logging, rate limiting
  db/          SQLAlchemy async engine/session, declarative base
  models/      ORM models — one file per table
  schemas/     Pydantic request/response models
  providers/   DownloadProvider (qBittorrent), StorageProvider, CacheProvider,
               StreamProvider — the abstraction layer future engines/backends
               plug into without touching services/ or api/
  services/    JobService, CacheManager, AuthService — business logic
  workers/     PollerWorker, EvictorWorker — background asyncio loops
  api/routes/  FastAPI routers
  tests/       unit/ (no external deps) and integration/ (real DB + qBittorrent)
alembic/       migrations
```
