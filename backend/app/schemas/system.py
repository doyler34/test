from typing import Literal

from pydantic import BaseModel

ComponentState = Literal["ok", "degraded", "down"]


class ComponentStatus(BaseModel):
    name: str
    status: ComponentState
    detail: str | None = None


class SystemStatus(BaseModel):
    status: ComponentState
    components: list[ComponentStatus]


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_used_bytes: int
    memory_total_bytes: int
    network_rx_bytes_s: float
    network_tx_bytes_s: float
    active_downloads: int
    active_users: int
    cache_used_bytes: int
    uptime_seconds: float
