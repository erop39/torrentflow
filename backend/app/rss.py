import hashlib
import re
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

from .validation import SUPPORTED_ADAPTER_TYPES, validate_proxy_url


def _proxy_for_client(proxy_url: str | None) -> str | None:
    """Validate a user supplied outbound proxy URL before handing it to httpx.

    Local proxy endpoints are intentionally allowed: a SOCKS gateway commonly runs
    beside TorrentFlow. This validation limits protocols and avoids malformed URLs.
    """
    return validate_proxy_url(proxy_url)


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "free", "freeleech", "doubleupload", "double_upload"}
    return False


def _first_value(entry: Any, *keys: str) -> Any:
    for key in keys:
        value = entry.get(key)
        if value not in (None, ""):
            return value
    return None


def _size_bytes(value: Any) -> int:
    """Normalise RSS sizes such as `1.5 GB` and raw byte counts to bytes."""
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not isinstance(value, str):
        return 0
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgtpe]?i?b)?\s*", value, re.IGNORECASE)
    if not match:
        return 0
    amount = float(match.group(1))
    unit = (match.group(2) or "b").lower().replace("ib", "b")
    powers = {"b": 0, "kb": 1, "mb": 2, "gb": 3, "tb": 4, "pb": 5, "eb": 6}
    power = powers.get(unit)
    return max(0, int(amount * (1024**power))) if power is not None else 0


def _entry_link(entry: Any) -> str:
    link = str(entry.get("link") or "")
    if link:
        return link
    for item in entry.get("links", []):
        href = item.get("href") if isinstance(item, dict) else getattr(item, "href", None)
        if href:
            return str(href)
    return ""


def _torrentleech_metadata(entry: Any) -> dict[str, str | int | bool]:
    """Extract TorrentLeech RSS extension fields while tolerating feed variants."""
    uploader = _first_value(entry, "torrent_uploader", "uploader", "author", "dc_creator")
    freeleech = _as_bool(_first_value(entry, "torrent_freeleech", "freeleech", "is_freeleech"))
    double_upload = _as_bool(_first_value(entry, "torrent_doubleupload", "torrent_double_upload", "doubleupload", "double_upload", "is_double_upload"))
    size_bytes = _size_bytes(_first_value(entry, "torrent_size", "size", "contentlength", "content_length"))
    return {
        "uploader": str(uploader or ""),
        "freeleech": freeleech,
        "double_upload": double_upload,
        "size_bytes": size_bytes,
    }


async def fetch_entries(
    url: str,
    *,
    proxy_url: str | None = None,
    adapter_type: str = "generic_rss",
    cookie: str | None = None,
) -> list[dict[str, str | int | bool]]:
    """Fetch and normalise generic RSS or TorrentLeech feed entries.

    The keyword-only additions retain compatibility with callers that only pass a
    feed URL. SOCKS support additionally requires the optional ``socksio`` httpx
    dependency at runtime; a missing dependency is reported without proxy secrets.
    """
    normalized_adapter = adapter_type.lower().strip()
    if normalized_adapter not in SUPPORTED_ADAPTER_TYPES:
        raise ValueError(f"Unsupported feed adapter: {adapter_type}")
    proxy = _proxy_for_client(proxy_url)
    try:
        headers = {"Cookie": cookie} if cookie else None
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, proxy=proxy, trust_env=False) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except ImportError as error:
        if proxy and urlparse(proxy).scheme.lower().startswith("socks"):
            raise RuntimeError("SOCKS proxy support requires the socksio dependency") from error
        raise

    parsed = feedparser.parse(response.content)
    entries: list[dict[str, str | int | bool]] = []
    for entry in parsed.entries:
        link = _entry_link(entry)
        result: dict[str, str | int | bool] = {
            "external_id": str(entry.get("id") or entry.get("guid") or hashlib.sha256((link or entry.get("title") or "").encode()).hexdigest()),
            "title": str(entry.get("title") or "Untitled release"),
            "link": link,
            "seeds": _as_int(_first_value(entry, "torrent_seeds", "seeds")),
        }
        if normalized_adapter in {"torrentleech", "torrent_leech"}:
            result.update(_torrentleech_metadata(entry))
        entries.append(result)
    return entries
