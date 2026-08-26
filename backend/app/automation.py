"""RSS scan and disk-monitor orchestration.

This module deliberately accepts its external operations as parameters.  It keeps
the scheduler independent of the HTTP application while allowing the API layer
to retain stable monkeypatch seams for tests and integrations.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .configuration import get_telegram_message_template
from .models import AuditEvent, Feed, FeedScanRun, Rule, StoredRelease
from .release_parsing import parse_release_title
from .schemas import FeedCheckItem, FeedCheckResponse
from .secrets import TrackerCredentials
from .telegram_templates import render_telegram_message

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
    """Scan one feed and persist an operationally safe outcome record.

    A scan can fail before the release transaction is committed.  In that
    case, rollback the attempted release changes and write a separate failed
    run so the health log remains truthful.
    """
    started_at = datetime.now(UTC)
    started_monotonic = time.perf_counter()
    feed_id = feed.id
    try:
        result = await _scan_feed_entries(
            feed,
            session,
            fetch_entries=fetch_entries,
            match_rule=match_rule,
            qbit_configured=qbit_configured,
            qbit_add=qbit_add,
            telegram_configured=telegram_configured,
            telegram_send=telegram_send,
            load_tracker_credentials=load_tracker_credentials,
            audit=audit,
        )
        session.add(FeedScanRun(
            feed_id=feed_id,
            status="succeeded",
            discovered=result.discovered,
            new_releases=result.new,
            duration_ms=max(0, round((time.perf_counter() - started_monotonic) * 1000)),
            started_at=started_at,
            completed_at=datetime.now(UTC),
        ))
        await session.commit()
        return result
    except Exception as error:
        await session.rollback()
        # Do not persist exception text: tracker URLs and HTTP diagnostics can
        # embed credentials.  The exception class is sufficient to diagnose
        # the failure category without disclosing request data.
        session.add(FeedScanRun(
            feed_id=feed_id,
            status="failed",
            duration_ms=max(0, round((time.perf_counter() - started_monotonic) * 1000)),
            error_summary=f"Scan failed ({type(error).__name__})",
            started_at=started_at,
            completed_at=datetime.now(UTC),
        ))
        persisted_feed = await session.get(Feed, feed_id)
        if persisted_feed is not None:
            persisted_feed.last_checked_at = datetime.now(UTC)
        await session.commit()
        raise


async def _scan_feed_entries(
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
    audit: Audit,
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
    telegram_template = await get_telegram_message_template(session)
    created = 0
    items: list[FeedCheckItem] = []
    for entry in entries:
        external_id = str(entry["external_id"])
        existing = await session.scalar(select(StoredRelease).where(StoredRelease.external_id == external_id))
        if existing is None:
            seeds = int(entry.get("seeds", 0))
            parsed_release = parse_release_title(entry["title"])
            matched = match_rule(
                str(entry["title"]), seeds, rules,
                freeleech=entry.get("freeleech") is True,
                double_upload=entry.get("double_upload") is True,
                size_bytes=entry.get("size_bytes") if isinstance(entry.get("size_bytes"), int) else None,
                uploader=str(entry.get("uploader") or ""),
            )
            action = matched.action if matched else "ignored"
            existing = StoredRelease(
                feed_id=feed.id,
                external_id=external_id,
                title=str(entry["title"]),
                display_title=parsed_release.display_title,
                group_key=parsed_release.group_key,
                media_type=parsed_release.media_type,
                parsed_series_title=parsed_release.series_title,
                parsed_season=parsed_release.season,
                parsed_episode=parsed_release.episode,
                parsed_year=parsed_release.year,
                link=str(entry["link"]),
                seeds=seeds,
                category=matched.category if matched else "series",
                matched_rule_id=matched.id if matched else None,
                status=action,
            )
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
                    await audit(session, "qbit.failed", f"{existing.title}: {type(error).__name__}", existing.id)
            if action in {"notify", "both"} and telegram_configured():
                try:
                    await telegram_send(render_telegram_message(telegram_template, {
                        "title": existing.title,
                        "rule": matched.name if matched else "—",
                        "category": existing.category,
                        "seeds": existing.seeds,
                        "feed": feed.name,
                        "link": existing.link,
                    }))
                    await audit(session, "telegram.sent", existing.title, existing.id)
                except Exception as error:
                    await audit(session, "telegram.failed", f"{existing.title}: {type(error).__name__}", existing.id)
        items.append(FeedCheckItem(title=existing.title, status=existing.status, rule_name=rule_names.get(existing.matched_rule_id), category=existing.category, seeds=existing.seeds))
    feed.last_checked_at = datetime.now(UTC)
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
