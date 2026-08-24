import asyncio
import re
import time
from typing import Any, cast

import qbittorrentapi

from app.providers.download.base import (
    DownloadProvider,
    DownloadProviderError,
    ProviderFile,
    ProviderJobState,
    ProviderStatus,
)

_MAGNET_HASH_RE = re.compile(r"xt=urn:btih:([A-Za-z0-9]{32,40})")

# qBittorrent's own `state` strings, mapped to our canonical states.
_STATE_MAP: dict[str, ProviderJobState] = {
    "error": ProviderJobState.FAILED,
    "missingFiles": ProviderJobState.FAILED,
    "uploading": ProviderJobState.COMPLETED,
    "pausedUP": ProviderJobState.COMPLETED,
    "queuedUP": ProviderJobState.COMPLETED,
    "stalledUP": ProviderJobState.COMPLETED,
    "checkingUP": ProviderJobState.COMPLETED,
    "forcedUP": ProviderJobState.COMPLETED,
    "allocating": ProviderJobState.DOWNLOADING,
    "downloading": ProviderJobState.DOWNLOADING,
    "metaDL": ProviderJobState.DOWNLOADING,
    "forcedDL": ProviderJobState.DOWNLOADING,
    "stalledDL": ProviderJobState.DOWNLOADING,
    "moving": ProviderJobState.DOWNLOADING,
    "pausedDL": ProviderJobState.PAUSED,
    "queuedDL": ProviderJobState.QUEUED,
    "checkingDL": ProviderJobState.PROCESSING,
    "checkingResumeData": ProviderJobState.PROCESSING,
    "unknown": ProviderJobState.DOWNLOADING,
}


def extract_magnet_hash(source: str) -> str | None:
    """Pull the BTIH out of a magnet URI directly, avoiding any race with
    qBittorrent to discover which torrent we just added. Only handles the
    common 40-char hex form; base32 magnets fall back to diff-based lookup."""
    match = _MAGNET_HASH_RE.search(source)
    if not match:
        return None
    value = match.group(1)
    return value.lower() if len(value) == 40 else None


class QBittorrentProvider(DownloadProvider):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_https: bool,
        tag: str,
    ) -> None:
        self._client = qbittorrentapi.Client(
            host=host,
            port=port,
            username=username,
            password=password,
            VERIFY_WEBUI_CERTIFICATE=use_https,
            REQUESTS_ARGS={"timeout": (5, 15)},
        )
        self._tag = tag
        self._rid = 0
        self._maindata_cache: dict[str, dict[str, Any]] = {}

    async def _call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except qbittorrentapi.APIError as exc:
            raise DownloadProviderError(str(exc)) from exc

    def _to_status(self, torrent_hash: str, t: dict[str, Any]) -> ProviderStatus:
        state = _STATE_MAP.get(t.get("state", "unknown"), ProviderJobState.DOWNLOADING)
        total = t.get("size")
        return ProviderStatus(
            external_id=torrent_hash,
            state=state,
            progress=float(t.get("progress", 0.0)),
            downloaded_size_bytes=int(t.get("completed", 0) or 0),
            speed_bytes_s=int(t.get("dlspeed", 0) or 0),
            total_size_bytes=int(total) if total else None,
            eta_seconds=self._eta(t),
            save_path=t.get("save_path"),
            error_message=t.get("state") if state == ProviderJobState.FAILED else None,
        )

    @staticmethod
    def _eta(t: dict[str, Any]) -> int | None:
        eta = t.get("eta")
        if eta is None or eta >= 8640000:  # qBittorrent's "infinite" sentinel
            return None
        return int(eta)

    @staticmethod
    def _hash_from_add_result(result: Any) -> str | None:
        """Interpret torrents_add's return value across qBittorrent versions.

        - qBittorrent 4.x returns the plain string "Ok." on success (or
          "Fails." on failure).
        - qBittorrent 5.x returns a TorrentsAddedMetadata mapping with
          success_count / failure_count / added_torrent_ids.

        Returns the added torrent's hash when the structured response gives it
        directly, or None to fall back to hash discovery. Raises
        DownloadProviderError only when the add clearly failed.
        """
        if isinstance(result, str):
            if result.strip().lower() != "ok.":
                raise DownloadProviderError(f"qBittorrent rejected the download: {result}")
            return None

        added_ids = list(getattr(result, "added_torrent_ids", None) or [])
        success_count = int(getattr(result, "success_count", 0) or 0)
        failure_count = int(getattr(result, "failure_count", 0) or 0)
        if not added_ids and success_count < 1 and failure_count > 0:
            raise DownloadProviderError(f"qBittorrent rejected the download: {result}")
        return str(added_ids[0]) if added_ids else None

    async def add(self, source: str, save_path: str) -> str:
        def _add() -> str:
            known_hash = extract_magnet_hash(source)
            before = {t.hash for t in self._client.torrents_info(tag=self._tag)}
            result = self._client.torrents_add(
                urls=source,
                save_path=save_path,
                tags=self._tag,
                use_auto_torrent_management=False,
            )
            direct_hash = self._hash_from_add_result(result)
            if direct_hash:
                return direct_hash

            if known_hash:
                for _ in range(10):
                    if self._client.torrents_info(torrent_hashes=known_hash):
                        return known_hash
                    time.sleep(0.3)
                return known_hash

            for _ in range(10):
                after = {t.hash for t in self._client.torrents_info(tag=self._tag)}
                new_hashes = after - before
                if new_hashes:
                    return next(iter(new_hashes))
                time.sleep(0.3)
            raise DownloadProviderError("Could not determine the added torrent's hash")

        return await self._call(_add)

    async def pause(self, external_id: str) -> None:
        await self._call(self._client.torrents_pause, torrent_hashes=external_id)

    async def resume(self, external_id: str) -> None:
        await self._call(self._client.torrents_resume, torrent_hashes=external_id)

    async def cancel(self, external_id: str, *, delete_files: bool = True) -> None:
        await self._call(
            self._client.torrents_delete, delete_files=delete_files, torrent_hashes=external_id
        )

    async def get_status(self, external_id: str) -> ProviderStatus | None:
        def _get() -> ProviderStatus | None:
            info = self._client.torrents_info(torrent_hashes=external_id)
            if not info:
                return None
            return self._to_status(external_id, dict(info[0]))

        return await self._call(_get)

    async def list_all(self) -> list[ProviderStatus]:
        def _sync() -> list[ProviderStatus]:
            data = cast(dict[str, Any], self._client.sync_maindata(rid=self._rid))
            self._rid = data.get("rid", self._rid)
            if data.get("full_update"):
                self._maindata_cache = {k: dict(v) for k, v in data.get("torrents", {}).items()}
            else:
                for torrent_hash, patch in data.get("torrents", {}).items():
                    self._maindata_cache.setdefault(torrent_hash, {}).update(patch)
                for torrent_hash in data.get("torrents_removed", []):
                    self._maindata_cache.pop(torrent_hash, None)

            statuses = []
            for torrent_hash, t in self._maindata_cache.items():
                tags = t.get("tags") or ""
                if self._tag in [tag.strip() for tag in tags.split(",")]:
                    statuses.append(self._to_status(torrent_hash, t))
            return statuses

        return await self._call(_sync)

    async def list_files(self, external_id: str) -> list[ProviderFile]:
        def _files() -> list[ProviderFile]:
            files = self._client.torrents_files(torrent_hash=external_id)
            return [
                ProviderFile(relative_path=f.name, size_bytes=int(f.size)) for f in files
            ]

        return await self._call(_files)

    async def health_check(self) -> bool:
        try:
            await self._call(self._client.app_version)
            return True
        except DownloadProviderError:
            return False
