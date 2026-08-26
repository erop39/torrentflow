"""Composable route groups for application configuration."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from .configuration import ConfigurationValidationError, canonical_configuration_json, canonical_configuration_yaml, export_configuration, get_disk_free_threshold_percent, import_configuration, set_disk_free_threshold_percent
from .database import get_session
from .schemas import DiskThresholdResponse, DiskThresholdUpdate, TrackerCredentialsStatus, TrackerCredentialsUpdate
from .secrets import SecretStorageUnavailable, delete_tracker_credentials, store_tracker_credentials, tracker_credentials_configured

RequireAdmin = Callable[[Request], Awaitable[None]]
Audit = Callable[[AsyncSession, str, str, int | None], Awaitable[None]]


def configuration_router(require_admin: RequireAdmin, audit: Audit) -> APIRouter:
    router = APIRouter(tags=["configuration"])

    @router.get("/api/config/export")
    async def download_configuration(format: str = "json", session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Response:
        """Download a versioned configuration document."""
        document = await export_configuration(session)
        if format == "json":
            return Response(content=canonical_configuration_json(document), media_type="application/json", headers={"Content-Disposition": "attachment; filename=torrentflow-config.json"})
        if format == "yaml":
            return Response(content=canonical_configuration_yaml(document), media_type="application/yaml", headers={"Content-Disposition": "attachment; filename=torrentflow-config.yaml"})
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="format must be json or yaml")

    @router.post("/api/config/import")
    async def upload_configuration(request: Request, mode: str = "merge", confirm_replace: bool = False, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> dict[str, object]:
        """Import validated JSON/YAML. Replacement requires an explicit confirmation."""
        if mode not in {"merge", "replace"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="mode must be merge or replace")
        if mode == "replace" and not confirm_replace:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="replace import requires confirm_replace=true")
        try:
            result = await import_configuration(session, await request.body(), mode=mode)
        except ConfigurationValidationError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Invalid configuration: {error}") from error
        await audit(session, "configuration.imported", f"Configuration {result.mode}: {result.feeds} feeds, {result.rules} rules, {result.categories} categories")
        await session.commit()
        return {"mode": result.mode, "feeds": result.feeds, "rules": result.rules, "categories": result.categories}

    @router.get("/api/feeds/{feed_id}/credentials", response_model=TrackerCredentialsStatus)
    async def tracker_credentials_status(feed_id: int, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> TrackerCredentialsStatus:
        return TrackerCredentialsStatus(configured=await tracker_credentials_configured(session, feed_id))

    @router.put("/api/feeds/{feed_id}/credentials", response_model=TrackerCredentialsStatus)
    async def save_tracker_credentials(feed_id: int, payload: TrackerCredentialsUpdate, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> TrackerCredentialsStatus:
        values: dict[str, str | None] = {}
        if "cookie" in payload.model_fields_set:
            values["cookie"] = payload.cookie
        if "passkey" in payload.model_fields_set:
            values["passkey"] = payload.passkey
        if not values:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Provide cookie or passkey")
        try:
            await store_tracker_credentials(session, feed_id, **values)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except SecretStorageUnavailable as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Encrypted credential storage is unavailable") from error
        await audit(session, "tracker_credentials.updated", f"Encrypted tracker credentials updated for feed {feed_id}")
        await session.commit()
        return TrackerCredentialsStatus(configured=await tracker_credentials_configured(session, feed_id))

    @router.delete("/api/feeds/{feed_id}/credentials", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
    async def remove_tracker_credentials(feed_id: int, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> Response:
        if await delete_tracker_credentials(session, feed_id):
            await audit(session, "tracker_credentials.deleted", f"Encrypted tracker credentials deleted for feed {feed_id}")
            await session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/api/settings/disk", response_model=DiskThresholdResponse)
    async def get_disk_threshold(session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> DiskThresholdResponse:
        return DiskThresholdResponse(disk_free_threshold_percent=await get_disk_free_threshold_percent(session))

    @router.put("/api/settings/disk", response_model=DiskThresholdResponse)
    async def update_disk_threshold(payload: DiskThresholdUpdate, session: AsyncSession = Depends(get_session), _: None = Depends(require_admin)) -> DiskThresholdResponse:
        await set_disk_free_threshold_percent(session, payload.disk_free_threshold_percent)
        await audit(session, "disk.threshold_updated", f"Disk threshold set to {payload.disk_free_threshold_percent:g}%")
        await session.commit()
        return DiskThresholdResponse(disk_free_threshold_percent=payload.disk_free_threshold_percent)

    return router
