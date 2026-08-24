import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class DownloadProviderError(Exception):
    """Raised when a download provider fails to perform a requested operation."""


class ProviderJobState(str, enum.Enum):
    """Canonical states a download provider can report, independent of any
    single engine's own vocabulary (qBittorrent's `state` strings, etc.)."""

    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProviderFile:
    relative_path: str
    size_bytes: int


@dataclass
class ProviderStatus:
    external_id: str
    state: ProviderJobState
    progress: float  # 0..1
    downloaded_size_bytes: int
    speed_bytes_s: int
    total_size_bytes: int | None = None
    eta_seconds: int | None = None
    save_path: str | None = None
    error_message: str | None = None
    files: list[ProviderFile] = field(default_factory=list)


class DownloadProvider(ABC):
    """Abstraction over a download engine (qBittorrent today; another torrent
    client, a usenet client, or a direct-HTTP downloader could implement this
    later without JobService or the API layer changing)."""

    @abstractmethod
    async def add(self, source: str, save_path: str) -> str:
        """Submit a new download. Returns the provider's external job id."""

    @abstractmethod
    async def pause(self, external_id: str) -> None: ...

    @abstractmethod
    async def resume(self, external_id: str) -> None: ...

    @abstractmethod
    async def cancel(self, external_id: str, *, delete_files: bool = True) -> None: ...

    @abstractmethod
    async def get_status(self, external_id: str) -> ProviderStatus | None:
        """Fresh, on-demand status for a single job. None if unknown to the provider."""

    @abstractmethod
    async def list_all(self) -> list[ProviderStatus]:
        """Status for every job this platform has submitted (used by the poller
        and by startup recovery). Providers may use a cheaper incremental/diff
        API internally as long as this returns the full current set."""

    @abstractmethod
    async def list_files(self, external_id: str) -> list[ProviderFile]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
