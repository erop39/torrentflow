"""Best-effort, presentation-oriented parsing of torrent release names.

The RSS title always remains the source of truth.  Parsed fields only improve
display and grouping, so a malformed or unfamiliar name must never prevent a
release from being stored.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from guessit import guessit


ReleaseKind = Literal["series", "movie", "unknown"]


@dataclass(frozen=True)
class ParsedRelease:
    """A safe normalised view of an RSS entry title."""

    display_title: str
    group_key: str
    media_type: ReleaseKind
    series_title: str | None = None
    season: int | None = None
    episode: int | None = None
    year: int | None = None


def _clean_title(value: object) -> str:
    text = " ".join(str(value or "").split())
    return text or "Untitled release"


def _group_slug(value: str) -> str:
    """Create a stable, bounded, human-debuggable grouping component."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii").casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:180] or "untitled"


def _first_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return _first_int(value[0]) if value else None
    return None


def _first_text(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        return cleaned or None
    if isinstance(value, list):
        return _first_text(value[0]) if value else None
    return None


def parse_release_title(title: object) -> ParsedRelease:
    """Parse common movie/episode names without making ingestion fragile.

    ``guessit`` recognises a broad range of release conventions.  Any parser
    failure, or a result without a usable title, falls back to the original
    entry title and a deterministic key.  The fallback deliberately has no
    false genre assertion.
    """
    raw_title = _clean_title(title)
    try:
        result = guessit(raw_title)
        parsed_title = _first_text(result.get("title"))
        media = _first_text(result.get("type"))
        season = _first_int(result.get("season"))
        episode = _first_int(result.get("episode"))
        year = _first_int(result.get("year"))
    except Exception:
        parsed_title = media = None
        season = episode = year = None

    if media == "episode" and parsed_title:
        # A series key intentionally omits season/episode: it groups all
        # episodes of the same show, while display preserves the exact episode.
        suffix = ""
        if season is not None and episode is not None:
            suffix = f" S{season:02d}E{episode:02d}"
        elif season is not None:
            suffix = f" S{season:02d}"
        elif episode is not None:
            suffix = f" E{episode:02d}"
        return ParsedRelease(
            display_title=f"{parsed_title}{suffix}",
            group_key=f"series:{_group_slug(parsed_title)}",
            media_type="series",
            series_title=parsed_title,
            season=season,
            episode=episode,
            year=year,
        )

    # ``guessit`` can label arbitrary prose as a movie.  A year is a small but
    # useful confidence floor for the basic movie presentation; without it we
    # retain the RSS title rather than misleading the operator.
    if media == "movie" and parsed_title and year is not None:
        display = f"{parsed_title} ({year})" if year is not None else parsed_title
        year_part = str(year) if year is not None else "unknown-year"
        return ParsedRelease(
            display_title=display,
            group_key=f"movie:{_group_slug(parsed_title)}:{year_part}",
            media_type="movie",
            year=year,
        )

    return ParsedRelease(
        display_title=raw_title,
        group_key=f"unknown:{_group_slug(raw_title)}",
        media_type="unknown",
    )
