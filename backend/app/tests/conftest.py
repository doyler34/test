"""Sets test environment variables before ANY other module in this test
session gets imported (pytest imports conftest.py files before collecting
test modules). This matters because app.db.session builds its async engine
at import time from settings.database_url — overriding it later, inside a
fixture, would be too late once something has already imported that module."""

import os

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/downloadcache_test"
)
os.environ["QBITTORRENT_HOST"] = "localhost"
os.environ["QBITTORRENT_PORT"] = "8080"
os.environ["QBITTORRENT_USERNAME"] = "admin"
os.environ["QBITTORRENT_PASSWORD"] = "adminadmin123"
os.environ["QBITTORRENT_TAG"] = "dlcache-test"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-at-least-32-bytes-long-for-hmac-sha256"
os.environ["FIRST_ADMIN_USERNAME"] = "admin"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@example.com"
os.environ["FIRST_ADMIN_PASSWORD"] = "admin-test-password-123"
os.environ["POLL_INTERVAL_SECONDS"] = "1"
os.environ["EVICTION_INTERVAL_SECONDS"] = "3600"  # tests trigger eviction directly, not via timer
os.environ["STORAGE_ROOT"] = "/tmp/dlcache-test-storage"
os.environ["COOKIE_SECURE"] = "false"
os.environ["MAX_STORAGE_GB"] = "500"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'
