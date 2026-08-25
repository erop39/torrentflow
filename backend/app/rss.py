import hashlib

import feedparser
import httpx


async def fetch_entries(url: str) -> list[dict[str, str | int]]:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    parsed = feedparser.parse(response.content)
    entries: list[dict[str, str | int]] = []
    for entry in parsed.entries:
        raw_seeds = entry.get("torrent_seeds") or entry.get("seeds") or 0
        try:
            seeds = int(raw_seeds)
        except (TypeError, ValueError):
            seeds = 0
        entries.append({"external_id": entry.get("id") or entry.get("guid") or hashlib.sha256((entry.get("link") or entry.get("title") or "").encode()).hexdigest(), "title": entry.get("title") or "Untitled release", "link": entry.get("link") or "", "seeds": max(0, seeds)})
    return entries
