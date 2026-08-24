from types import SimpleNamespace

import pytest

from app.providers.download.base import DownloadProviderError
from app.providers.download.qbittorrent import QBittorrentProvider

interpret = QBittorrentProvider._hash_from_add_result


def test_ok_string_falls_through_to_hash_discovery() -> None:
    # qBittorrent 4.x success sentinel -> None (caller resolves the hash itself)
    assert interpret("Ok.") is None
    assert interpret("Ok.\n") is None


def test_fails_string_raises() -> None:
    with pytest.raises(DownloadProviderError):
        interpret("Fails.")


def test_structured_success_returns_added_hash() -> None:
    # qBittorrent 5.x structured response (the case that broke a real deploy)
    result = SimpleNamespace(
        added_torrent_ids=["dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c"],
        failure_count=0,
        pending_count=0,
        success_count=1,
    )
    assert interpret(result) == "dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c"


def test_structured_failure_raises() -> None:
    result = SimpleNamespace(
        added_torrent_ids=[], failure_count=1, pending_count=0, success_count=0
    )
    with pytest.raises(DownloadProviderError):
        interpret(result)


def test_structured_success_without_ids_falls_through() -> None:
    # success reported but no id echoed back -> fall back to hash discovery
    result = SimpleNamespace(
        added_torrent_ids=[], failure_count=0, pending_count=0, success_count=1
    )
    assert interpret(result) is None
