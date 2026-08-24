from app.api.routes.files import parse_range_header


def test_no_header_returns_none() -> None:
    assert parse_range_header(None, 1000) is None


def test_simple_range() -> None:
    result = parse_range_header("bytes=0-499", 1000)
    assert result is not None
    assert (result.start, result.end) == (0, 499)


def test_open_ended_range_goes_to_end_of_file() -> None:
    result = parse_range_header("bytes=900-", 1000)
    assert result is not None
    assert (result.start, result.end) == (900, 999)


def test_suffix_range_returns_last_n_bytes() -> None:
    result = parse_range_header("bytes=-100", 1000)
    assert result is not None
    assert (result.start, result.end) == (900, 999)


def test_range_end_is_clamped_to_file_size() -> None:
    result = parse_range_header("bytes=0-999999", 1000)
    assert result is not None
    assert (result.start, result.end) == (0, 999)


def test_multi_range_falls_back_to_full_content() -> None:
    assert parse_range_header("bytes=0-99,200-299", 1000) is None


def test_malformed_range_falls_back_to_full_content() -> None:
    assert parse_range_header("bytes=abc-def", 1000) is None


def test_start_beyond_file_size_is_rejected() -> None:
    assert parse_range_header("bytes=5000-", 1000) is None
