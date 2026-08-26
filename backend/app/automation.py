"""RSS scan and disk-monitor orchestration.

This module deliberately accepts its external operations as parameters.  It keeps
the scheduler independent of the HTTP application while allowing the API layer
to retain stable monkeypatch seams for tests and integrations.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import AuditEvent, Feed, Rule, StoredRelease
from .schemas import FeedCheckItem, FeedCheckResponse
from .secrets import TrackerCredentials

logger = logging.getLogger(__name__)

Audit = Callable[[AsyncSession, str, str, int | None], Awaitable[None]]
ScanFeed = Callable[[Feed, AsyncSession], Awaitable[FeedCheckResponse]]


async def record_audit(session: AsyncSession, event_type: str, message: str, release_id: int | None = None) -> None:
    session.add(AuditEvent(event_type=event_type, message=message, release_id=release_id))


async def scan_feed(
    feed: Feed,
    session: AsyncSession,
    *,
    fetch_entries: Callable[..., Awaitable[list[dict[str, object]]]],
    match_rule: Callable[..., Rule | None],
    qbit_configured: Callable[[], bool],
    qbit_add: Callable[..., Awaitable[None]],
    telegram_configured: Callable[[], bool],
    telegram_send: Callable[[str], Awaitable[None]],
    load_tracker_credentials: Callable[[AsyncSession, int], Awaitable[TrackerCredentials | None]],
    audit: Audit = record_audit,
) -> FeedCheckResponse:
    fetch_options: dict[str, str] = {}
    if feed.proxy_url:
        fetch_options["proxy_url"] = feed.proxy_url
    if feed.adapter_type != "generic_rss":
        fetch_options["adapter_type"] = feed.adapter_type
    credentials = await load_tracker_credentials(session, feed.id)
    if credentials is not None and credentials.cookie:
        fetch_options["cookie"] = credentials.cookie
    entries = await fetch_entries(feed.url, **fetch_options)
    rules = list((await session.scalars(select(Rule).order_by(Rule.priority, Rule.id))).all())
    rule_names = {rule.id: rule.name for rule in rules}
    created = 0
    items: list[FeedCheckItem] = []
    for entry in entries:
        external_id = str(entry["external_id"])
        existing = await session.scalar(select(StoredRelease).where(StoredRelease.external_id == external_id))
        if existing is None:
            seeds = int(entry.get("seeds", 0))
            matched = match_rule(
                str(entry["title"]), seeds, rules,
                freeleech=entry.get("freeleech") is True,
                double_upload=entry.get("double_upload") is True,
                size_bytes=entry.get("size_bytes") if isinstance(entry.get("size_bytes"), int) else None,
                uploader=str(entry.get("uploader") or ""),
            )
            action = matched.action if matched else "ignored"
            existing = StoredRelease(feed_id=feed.id, external_id=external_id, title=str(entry["title"]), link=str(entry["link"]), seeds=seeds, category=matched.category if matched else "series", matched_rule_id=matched.id if matched else None, status=action)
            session.add(existing)
            await session.flush()
            created += 1
            await audit(session, "release.discovered", f"{feed.name}: {existing.title}", existing.id)
            if action in {"auto_add", "both"} and existing.link and qbit_configured():
                try:
                    qbit_options = {key: value for key, value in {"category": matched.qb_category, "save_path": matched.save_path}.items() if value}
                    await qbit_add(existing.link, **qbit_options)
                    await audit(session, "qbit.added", existing.title, existing.id)
                except Exception as error:
                    await audit(session, "qbit.failed", f"{existing.title}: {error}", existing.id)
            if action in {"notify", "both"} and telegram_configured():
                try:
                    await telegram_send(f"TorrentFlow: {existing.title}\nRule: {matched.name if matched else '—'}\nCategory: {existing.category}")
                    await audit(session, "telegram.sent", existing.title, existing.id)
                except Exception as error:
                    await audit(session, "telegram.failed", f"{existing.title}: {error}", existing.id)
        items.append(FeedCheckItem(title=existing.title, status=existing.status, rule_name=rule_names.get(existing.matched_rule_id), category=existing.category, seeds=existing.seeds))
    feed.last_checked_at = datetime.now(UTC)
    await session.commit()
    return FeedCheckResponse(discovered=len(entries), new=created, items=items[:25])


async def scan_due_feeds_once(
    session_factory: async_sessionmaker[AsyncSession],
    scan_feed: ScanFeed,
    check_disk_space_and_alert: Callable[[], Awaitable[None]],
) -> None:
    try:
        async with session_factory() as listing_session:
            now = datetime.now(UTC)
            feed_ids = list((await listing_session.scalars(select(Feed.id).where(Feed.enabled.is_(True)))).all())
        for feed_id in feed_ids:
            async with session_factory() as session:
                feed = await session.get(Feed, feed_id)
                if feed is None or not feed.enabled:
                    continue
                last_checked_at = feed.last_checked_at
                if last_checked_at is not None and last_checked_at.tzinfo is None:
                    last_checked_at = last_checked_at.replace(tzinfo=UTC)
                if last_checked_at is not None and (now - last_checked_at).total_seconds() < feed.interval_minutes * 60:
                    continue
                try:
                    await scan_feed(feed, session)
                except Exception as error:
                    await session.rollback()
                    logger.warning("Scheduled RSS scan failed for feed %s: %s", feed_id, error)
    except Exception as error:
        logger.exception("RSS scheduler iteration failed: %s", error)
    await check_disk_space_and_alert()


async def scheduled_scan_loop(scan_due_feeds_once: Callable[[], Awaitable[None]], sleep: Callable[[float], Awaitable[None]]) -> None:
    while True:
        await scan_due_feeds_once()
        await sleep(60)
