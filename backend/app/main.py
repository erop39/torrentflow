import contextlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import hmac
import os
import asyncio
import logging
import sys

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import delete, select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal, get_session
from .models import AuditEvent, Category, Feed, Rule, StoredRelease
from .migrations import upgrade_database
from .rss import fetch_entries
from .matching import match_rule
from .integrations import qbit_add, qbit_configured, qbit_downloads, telegram_configured, telegram_send
from .schemas import AuditEventResponse, CategoryCreate, CategoryResponse, CategoryUpdate, DownloadItem, FeedCheckItem, FeedCheckResponse, FeedCreate, FeedResponse, FeedUpdate, HealthResponse, IntegrationStatus, LoginRequest, Release, ReleaseOutcome, RuleCreate, RuleResponse, ServiceHealth, ServiceStatus, SessionResponse, StoredReleaseResponse

IS_PRODUCTION = os.getenv("TORRENTFLOW_ENV") == "production"
ADMIN_PASSWORD = os.getenv("TORRENTFLOW_ADMIN_PASSWORD", "change-me")
SESSION_SECRET = os.getenv("TORRENTFLOW_SESSION_SECRET", "replace-this-dev-session-secret")


def validate_runtime_configuration() -> None:
    placeholders = {"", "change-me", "change-this-password", "replace-this-dev-session-secret", "replace-with-a-long-random-secret"}
    if IS_PRODUCTION and (ADMIN_PASSWORD in placeholders or len(ADMIN_PASSWORD) < 12 or SESSION_SECRET in placeholders or len(SESSION_SECRET) < 32):
        raise RuntimeError("Production requires a 12+ character TORRENTFLOW_ADMIN_PASSWORD and a non-placeholder 32+ character TORRENTFLOW_SESSION_SECRET")


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_configuration()
    # Keep local development and production on the same, versioned schema
    # lifecycle.  Docker also performs this command before the API starts;
    # Alembic upgrades are idempotent, so the second check is harmless.
    await asyncio.to_thread(upgrade_database)
    task = None if "pytest" in sys.modules else asyncio.create_task(scheduled_scan_loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="TorrentFlow API", version="0.1.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, https_only=os.getenv("TORRENTFLOW_COOKIE_SECURE", "false").lower() == "true", same_site="lax")

# The production UI is served by this app. Vite origins are allowed only for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:4175", "http://localhost:4175"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

RELEASES = [
    Release(id="arcane", title="Arcane.S02E01.2160p.WEB", source="TorrentLeech", rule="Animation 4K", category="series", size="18.2 GB", seeds=42, outcome=ReleaseOutcome.ADDED),
    Release(id="ubuntu", title="Ubuntu.24.04.2.LTS", source="Ubuntu RSS", rule="Linux ISO", category="linux", size="5.6 GB", seeds=185, outcome=ReleaseOutcome.NOTIFY),
]

logger = logging.getLogger(__name__)


async def require_admin(request: Request) -> None:
    if request.session.get("admin") is not True:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


async def audit(session: AsyncSession, event_type: str, message: str, release_id: int | None = None) -> None:
    session.add(AuditEvent(event_type=event_type, message=message, release_id=release_id))


async def scan_feed(feed: Feed, session: AsyncSession) -> FeedCheckResponse:
    entries = await fetch_entries(feed.url)
    rules = list((await session.scalars(select(Rule).order_by(Rule.priority, Rule.id))).all())
    rule_names = {rule.id: rule.name for rule in rules}
    created = 0
    items: list[FeedCheckItem] = []
    for entry in entries:
        external_id = str(entry["external_id"])
        existing = await session.scalar(select(StoredRelease).where(StoredRelease.external_id == external_id))
        if existing is None:
            seeds = int(entry.get("seeds", 0))
            matched = match_rule(str(entry["title"]), seeds, rules)
            action = matched.action if matched else "ignored"
            existing = StoredRelease(feed_id=feed.id, external_id=external_id, title=str(entry["title"]), link=str(entry["link"]), seeds=seeds, category=matched.category if matched else "series", matched_rule_id=matched.id if matched else None, status=action)
            session.add(existing)
            await session.flush()
            created += 1
            await audit(session, "release.discovered", f"{feed.name}: {existing.title}", existing.id)
            if action in {"auto_add", "both"} and existing.link and qbit_configured():
                try:
                    await qbit_add(existing.link)
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


async def scan_due_feeds_once() -> None:
    try:
        async with SessionLocal() as session:
            now = datetime.now(UTC)
            feeds = list((await session.scalars(select(Feed).where(Feed.enabled.is_(True)))).all())
            for feed in feeds:
                last_checked_at = feed.last_checked_at
                if last_checked_at is not None and last_checked_at.tzinfo is None:
                    last_checked_at = last_checked_at.replace(tzinfo=UTC)
                if last_checked_at is not None and (now - last_checked_at).total_seconds() < feed.interval_minutes * 60:
                    continue
                try:
                    await scan_feed(feed, session)
                except Exception as error:
                    feed_id = feed.id
                    await session.rollback()
                    logger.warning("Scheduled RSS scan failed for feed %s: %s", feed_id, error)
    except Exception as error:
        logger.exception("RSS scheduler iteration failed: %s", error)


async def scheduled_scan_loop() -> None:
    while True:
        await scan_due_feeds_once()
        await asyncio.sleep(60)


@app.post("/api/auth/login", response_model=SessionResponse, tags=["auth"])
async def login(payload: LoginRequest, request: Request) -> SessionResponse:
    if not hmac.compare_digest(payload.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    request.session["admin"] = True
    return SessionResponse(authenticated=True)


@app.post("/api/auth/logout", response_model=SessionResponse, tags=["auth"])
async def logout(request: Request) -> SessionResponse:
    request.session.clear()
    return SessionResponse(authenticated=False)


@app.get("/api/auth/me", response_model=SessionResponse, tags=["auth"])
async def me(request: Request) -> SessionResponse:
    return SessionResponse(authenticated=request.session.get("admin") is True)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def get_health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    rule_count = len(list((await session.scalars(select(Rule).where(Rule.enabled.is_(True)))).all()))
    return HealthResponse(
        services=[
            ServiceHealth(name="RSS", status=ServiceStatus.HEALTHY, detail="Scheduler active"),
            ServiceHealth(name="Rules", status=ServiceStatus.HEALTHY, detail=f"{rule_count} active rules"),
            ServiceHealth(name="qBittorrent", status=ServiceStatus.HEALTHY if qbit_configured() else ServiceStatus.UNCONFIGURED, detail="Configured; test connection in Settings" if qbit_configured() else "Not configured"),
            ServiceHealth(name="Telegram", status=ServiceStatus.HEALTHY if telegram_configured() else ServiceStatus.UNCONFIGURED, detail="Configured; test connection in Settings" if telegram_configured() else "Not configured"),
        ],
        checked_at=datetime.now(UTC),
    )


@app.get("/api/ready", tags=["system"])
async def readiness() -> dict[str, bool]:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable") from error
    return {"ready": True}


@app.get("/api/releases", response_model=list[StoredReleaseResponse], tags=["releases"])
async def list_releases(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> list[StoredReleaseResponse]:
    """Return persisted release decisions, newest first."""
    releases = list((await session.scalars(select(StoredRelease).order_by(StoredRelease.created_at.desc(), StoredRelease.id.desc()))).all())
    feed_names = {feed.id: feed.name for feed in (await session.scalars(select(Feed))).all()}
    rule_names = {rule.id: rule.name for rule in (await session.scalars(select(Rule))).all()}
    return [StoredReleaseResponse(id=release.id, title=release.title, link=release.link, source=feed_names.get(release.feed_id, "Unknown feed"), rule_name=rule_names.get(release.matched_rule_id), status=release.status, category=release.category, seeds=release.seeds, created_at=release.created_at) for release in releases]


@app.get("/api/feeds", response_model=list[FeedResponse], tags=["feeds"])
async def list_feeds(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> list[Feed]:
    return list((await session.scalars(select(Feed).order_by(Feed.id))).all())


@app.post("/api/feeds", response_model=FeedResponse, status_code=status.HTTP_201_CREATED, tags=["feeds"])
async def create_feed(payload: FeedCreate, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Feed:
    feed = Feed(**payload.model_dump())
    session.add(feed)
    await session.commit()
    await session.refresh(feed)
    return feed


@app.post("/api/feeds/{feed_id}/check", response_model=FeedCheckResponse, tags=["feeds"])
async def check_feed(feed_id: int, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> FeedCheckResponse:
    feed = await session.get(Feed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    return await scan_feed(feed, session)


@app.patch("/api/feeds/{feed_id}", response_model=FeedResponse, tags=["feeds"])
async def update_feed(feed_id: int, payload: FeedUpdate, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Feed:
    feed = await session.get(Feed, feed_id)
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(feed, field, value)
    await session.commit()
    await session.refresh(feed)
    return feed


@app.delete("/api/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, tags=["feeds"])
async def delete_feed(feed_id: int, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Response:
    feed = await session.get(Feed, feed_id)
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    await session.execute(delete(StoredRelease).where(StoredRelease.feed_id == feed_id))
    await session.delete(feed)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/rules", response_model=list[RuleResponse], tags=["rules"])
async def list_rules(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> list[Rule]:
    return list((await session.scalars(select(Rule).order_by(Rule.priority, Rule.id))).all())


@app.post("/api/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED, tags=["rules"])
async def create_rule(payload: RuleCreate, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Rule:
    if await session.scalar(select(Category).where(Category.name == payload.category)) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Choose a configured category")
    rule = Rule(**payload.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@app.get("/api/categories", response_model=list[CategoryResponse], tags=["categories"])
async def list_categories(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> list[Category]:
    return list((await session.scalars(select(Category).order_by(Category.name))).all())


@app.post("/api/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, tags=["categories"])
async def create_category(payload: CategoryCreate, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Category:
    category = Category(**payload.model_dump())
    session.add(category)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists") from error
    await session.refresh(category)
    return category


@app.patch("/api/categories/{category_id}", response_model=CategoryResponse, tags=["categories"])
async def update_category(category_id: int, payload: CategoryUpdate, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Category:
    category = await session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await session.commit()
    await session.refresh(category)
    return category


@app.get("/api/integrations/status", response_model=IntegrationStatus, tags=["integrations"])
async def integration_status(_: None = Depends(require_admin)) -> IntegrationStatus:
    return IntegrationStatus(qbit_configured=qbit_configured(), telegram_configured=telegram_configured())


@app.post("/api/integrations/qbittorrent/test", tags=["integrations"])
async def test_qbittorrent(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> dict[str, bool]:
    await qbit_downloads()
    await audit(session, "qbit.tested", "qBittorrent connection test succeeded")
    await session.commit()
    return {"ok": True}


@app.get("/api/downloads", response_model=list[DownloadItem], tags=["downloads"])
async def list_downloads(_: None = Depends(require_admin)) -> list[DownloadItem]:
    torrents = await qbit_downloads()
    return [DownloadItem(name=str(item.get("name", "Untitled")), progress=float(item.get("progress", 0)), state=str(item.get("state", "unknown")), dlspeed=int(item.get("dlspeed", 0))) for item in torrents]


@app.post("/api/integrations/telegram/test", tags=["integrations"])
async def test_telegram(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> dict[str, bool]:
    await telegram_send("TorrentFlow: Telegram integration is connected.")
    await audit(session, "telegram.tested", "Telegram test message sent")
    await session.commit()
    return {"ok": True}


@app.get("/api/audit", response_model=list[AuditEventResponse], tags=["audit"])
async def list_audit(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> list[AuditEvent]:
    return list((await session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(200))).all())
