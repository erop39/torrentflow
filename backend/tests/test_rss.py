from app.rss import _proxy_for_client, _size_bytes, _torrentleech_metadata


def test_proxy_accepts_socks_and_rejects_unsafe_shapes() -> None:
    assert _proxy_for_client("socks5://127.0.0.1:1080") == "socks5://127.0.0.1:1080"
    assert _proxy_for_client("https://proxy.example:8443") == "https://proxy.example:8443"
    for invalid in (
        "ftp://proxy.example",
        "socks5://proxy.example/path?secret=x",
        "http://proxy.example bad",
        "socks5://user:password@proxy.example:1080",
        "https://user@proxy.example:8443",
    ):
        try:
            _proxy_for_client(invalid)
        except ValueError:
            continue
        raise AssertionError(f"Expected invalid proxy to be rejected: {invalid}")


def test_torrentleech_metadata_normalizes_flags_uploader_and_size() -> None:
    metadata = _torrentleech_metadata({"torrent_uploader": "Trusted", "torrent_freeleech": "yes", "torrent_doubleupload": "1", "torrent_size": "1.5 GB"})
    assert metadata == {"uploader": "Trusted", "freeleech": True, "double_upload": True, "size_bytes": 1610612736}
    assert _size_bytes("not a size") == 0
