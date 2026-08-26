"""Shared validation for persisted network configuration."""

from urllib.parse import urlparse


SUPPORTED_ADAPTER_TYPES = frozenset({"generic_rss", "torrentleech", "torrent_leech"})
SUPPORTED_PROXY_SCHEMES = frozenset({"http", "https", "socks5", "socks5h"})


def validate_proxy_url(value: str | None) -> str | None:
    """Return a safe proxy endpoint or raise ``ValueError``.

    Proxy credentials must not be persisted because feeds are exported as
    configuration. Authentication, when required, belongs in a local proxy
    service rather than in its URL.
    """
    if value is None or not value.strip():
        return None
    if value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("Proxy URL must not contain whitespace")
    parsed = urlparse(value)
    if parsed.scheme.lower() not in SUPPORTED_PROXY_SCHEMES or not parsed.hostname:
        raise ValueError("Proxy URL must use http(s) or socks5 and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Proxy URL must not include credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Proxy URL must not include a query or fragment")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Proxy URL has an invalid port") from error
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Proxy URL has an invalid port")
    return value
