from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="production")
    log_level: str = Field(default="INFO")

    # --- database ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/downloadcache"
    )

    # --- auth ---
    jwt_secret_key: str = Field(default="change-me-in-.env")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=14)

    first_admin_username: str = Field(default="admin")
    first_admin_email: str = Field(default="admin@example.com")
    first_admin_password: str = Field(default="change-me-in-.env")

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cookie_secure: bool = Field(default=True)
    cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax")

    login_rate_limit: str = Field(default="5/minute")
    default_rate_limit: str = Field(default="120/minute")

    # --- qBittorrent ---
    qbittorrent_host: str = Field(default="localhost")
    qbittorrent_port: int = Field(default=8080)
    qbittorrent_username: str = Field(default="admin")
    qbittorrent_password: str = Field(default="adminadmin")
    qbittorrent_use_https: bool = Field(default=False)
    qbittorrent_tag: str = Field(default="dlcache")

    poll_interval_seconds: float = Field(default=2.0)

    # --- storage / cache ---
    storage_root: str = Field(default="/data")
    max_storage_gb: float = Field(default=500.0)
    cache_eviction_threshold: float = Field(default=0.85)
    cache_retention_days: int = Field(default=30)
    eviction_interval_seconds: float = Field(default=300.0)

    stream_chunk_size_bytes: int = Field(default=1024 * 1024)

    @property
    def max_storage_bytes(self) -> int:
        return int(self.max_storage_gb * 1024**3)


@lru_cache
def get_settings() -> Settings:
    return Settings()
