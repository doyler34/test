from app.providers.download.qbittorrent import extract_magnet_hash


def test_extracts_lowercase_hex_hash() -> None:
    magnet = "magnet:?xt=urn:btih:AABBCCDDEEFF00112233445566778899AABBCCDD&dn=test"
    assert extract_magnet_hash(magnet) == "aabbccddeeff00112233445566778899aabbccdd"


def test_returns_none_for_base32_hash() -> None:
    # 32-char base32 form is not handled; caller falls back to diff-based lookup
    magnet = "magnet:?xt=urn:btih:ABCDEFGHIJKLMNOPQRSTUVWXYZ234567&dn=test"
    assert extract_magnet_hash(magnet) is None


def test_returns_none_for_non_magnet_source() -> None:
    assert extract_magnet_hash("https://example.com/file.torrent") is None
