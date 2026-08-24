from pathlib import Path

import pytest

from app.providers.storage.base import StorageProviderError, safe_join


def test_safe_join_resolves_normal_relative_path(tmp_path: Path) -> None:
    result = safe_join(tmp_path, "job-123/movie.mkv")
    assert result == (tmp_path / "job-123" / "movie.mkv").resolve()


@pytest.mark.parametrize(
    "malicious_path",
    [
        "../../etc/passwd",
        "job-123/../../../etc/passwd",
        "/etc/passwd",
        "//etc/passwd",
        "..",
        "a/../../b",
    ],
)
def test_safe_join_rejects_traversal_attempts(tmp_path: Path, malicious_path: str) -> None:
    with pytest.raises(StorageProviderError):
        safe_join(tmp_path, malicious_path)


def test_safe_join_rejects_empty_path(tmp_path: Path) -> None:
    with pytest.raises(StorageProviderError):
        safe_join(tmp_path, "")


def test_safe_join_allows_nested_directories(tmp_path: Path) -> None:
    result = safe_join(tmp_path, "a/b/c/d.txt")
    assert result == (tmp_path / "a" / "b" / "c" / "d.txt").resolve()
