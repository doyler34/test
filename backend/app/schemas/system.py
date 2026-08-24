import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

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


class SystemEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    level: str
    component: str
    message: str
    meta: dict[str, Any] | None
    created_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime
