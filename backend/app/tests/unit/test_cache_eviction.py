import uuid
from datetime import UTC, datetime, timedelta

from app.providers.cache.base import CacheEntryView, select_eviction_candidates

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make_entry(
    *,
    days_ago: int,
    size_bytes: int,
    protected: bool = False,
) -> CacheEntryView:
    return CacheEntryView(
        id=uuid.uuid4(),
        path=f"file-{days_ago}-{size_bytes}",
        size_bytes=size_bytes,
        last_accessed_at=NOW - timedelta(days=days_ago),
        created_at=NOW - timedelta(days=days_ago),
        protected=protected,
    )


def test_no_eviction_when_under_threshold() -> None:
    entries = [make_entry(days_ago=100, size_bytes=10)]
    result = select_eviction_candidates(
        entries,
        used_bytes=50,
        max_bytes=100,
        threshold=0.85,
        retention_days=30,
        now=NOW,
    )
    assert result == []


def test_evicts_oldest_first_until_under_target() -> None:
    old = make_entry(days_ago=100, size_bytes=40)
    older = make_entry(days_ago=200, size_bytes=40)
    newest_but_still_stale = make_entry(days_ago=90, size_bytes=40)
    entries = [old, older, newest_but_still_stale]

    # used=120/max=100 => target=85; evicting the single oldest entry (40)
    # already brings projected usage to 80, under target, so eviction stops there.
    result = select_eviction_candidates(
        entries, used_bytes=120, max_bytes=100, threshold=0.85, retention_days=30, now=NOW
    )
    assert result == [older.id]


def test_respects_retention_days_under_hard_cap() -> None:
    recent = make_entry(days_ago=1, size_bytes=90)  # within retention window
    entries = [recent]
    # used=90/max=100, target=85 -> over target but NOT over hard cap (100)
    result = select_eviction_candidates(
        entries, used_bytes=90, max_bytes=100, threshold=0.85, retention_days=30, now=NOW
    )
    assert result == []  # protected by retention window


def test_ignores_retention_when_over_hard_cap() -> None:
    recent = make_entry(days_ago=1, size_bytes=150)
    entries = [recent]
    # used=150 > max=100 => hard cap exceeded, retention no longer protects it
    result = select_eviction_candidates(
        entries, used_bytes=150, max_bytes=100, threshold=0.85, retention_days=30, now=NOW
    )
    assert result == [recent.id]


def test_never_evicts_protected_entries() -> None:
    protected = make_entry(days_ago=500, size_bytes=150, protected=True)
    entries = [protected]
    result = select_eviction_candidates(
        entries, used_bytes=150, max_bytes=100, threshold=0.85, retention_days=30, now=NOW
    )
    assert result == []


def test_never_evicts_currently_streaming_entries() -> None:
    streaming = make_entry(days_ago=500, size_bytes=150)
    entries = [streaming]
    result = select_eviction_candidates(
        entries,
        used_bytes=150,
        max_bytes=100,
        threshold=0.85,
        retention_days=30,
        now=NOW,
        is_streaming=lambda path: path == streaming.path,
    )
    assert result == []


def test_stops_as_soon_as_target_is_reached() -> None:
    a = make_entry(days_ago=300, size_bytes=30)
    b = make_entry(days_ago=200, size_bytes=30)
    c = make_entry(days_ago=100, size_bytes=30)
    entries = [a, b, c]
    # used=90/max=100, target=85 -> evicting just `a` (30) brings us to 60, well under target
    result = select_eviction_candidates(
        entries, used_bytes=90, max_bytes=100, threshold=0.85, retention_days=30, now=NOW
    )
    assert result == [a.id]
