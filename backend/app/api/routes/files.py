import mimetypes
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession, get_cache_manager, get_stream
from app.models.cache_entry import CacheEntryStatus
from app.models.user import UserRole
from app.providers.stream.base import RangeSpec
from app.providers.stream.local import LocalStreamProvider
from app.services.cache_manager import CacheManager
from app.services.usage_service import record_usage

router = APIRouter(prefix="/api/files", tags=["files"])


def parse_range_header(range_header: str | None, file_size: int) -> RangeSpec | None:
    """Parses a single-range `Range: bytes=...` header. Returns None for a
    missing/unparseable/multi-range header, meaning "serve the whole file" —
    pure and independently testable."""
    if not range_header or not range_header.startswith("bytes=") or file_size <= 0:
        return None
    spec = range_header[len("bytes=") :].strip()
    if "," in spec:
        return None  # multiple ranges not supported; fall back to full content

    start_str, _, end_str = spec.partition("-")
    if start_str == "" and end_str == "":
        return None

    if start_str == "":
        suffix_len = int(end_str) if end_str.isdigit() else 0
        if suffix_len <= 0:
            return None
        start = max(file_size - suffix_len, 0)
        end = file_size - 1
    else:
        if not start_str.isdigit():
            return None
        start = int(start_str)
        end = int(end_str) if end_str.isdigit() else file_size - 1

    end = min(end, file_size - 1)
    if start < 0 or start > end:
        return None
    return RangeSpec(start=start, end=end)


@router.get("/{entry_id}")
async def download_file(
    entry_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    session: DbSession,
    manager: Annotated[CacheManager, Depends(get_cache_manager)],
    stream: Annotated[LocalStreamProvider, Depends(get_stream)],
) -> StreamingResponse:
    entry = await manager.get(entry_id)
    if entry is None or entry.status != CacheEntryStatus.ACTIVE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if entry.owner_user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")

    range_spec = parse_range_header(request.headers.get("range"), entry.size_bytes)
    media_type = mimetypes.guess_type(entry.path)[0] or "application/octet-stream"
    filename = entry.path.rsplit("/", 1)[-1]

    await manager.record_access(entry)
    served_bytes = (
        range_spec.end - range_spec.start + 1 if range_spec else entry.size_bytes
    )
    await record_usage(
        session, user_id=user.id, cache_entry_id=entry.id, bytes_served=served_bytes
    )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    if range_spec:
        headers["Content-Range"] = f"bytes {range_spec.start}-{range_spec.end}/{entry.size_bytes}"
        headers["Content-Length"] = str(served_bytes)
        status_code = status.HTTP_206_PARTIAL_CONTENT
    else:
        headers["Content-Length"] = str(entry.size_bytes)
        status_code = status.HTTP_200_OK

    return StreamingResponse(
        stream.open_range(entry.path, range_spec),
        status_code=status_code,
        media_type=media_type,
        headers=headers,
    )
