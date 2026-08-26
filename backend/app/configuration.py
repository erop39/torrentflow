"""Portable, secret-free configuration export and import helpers.

This module intentionally only covers persisted feed, rule, and category settings.
Runtime credentials are environment-only and must never become part of an export.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
import yaml
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ApplicationSetting, Category, Feed, Rule, TrackerCredential
from .schemas import CategoryCreate, FeedCreate, RuleCreate

CONFIGURATION_FORMAT = "torrentflow/configuration"
CONFIGURATION_VERSION = 2
LEGACY_CONFIGURATION_VERSION = 1
DISK_FREE_THRESHOLD_SETTING = "disk_free_threshold_percent"


class ConfigurationValidationError(ValueError):
    """Raised before an invalid configuration can modify the database."""


class FeedConfiguration(FeedCreate):
    enabled: bool = True


class RuleConfiguration(RuleCreate):
    enabled: bool = True


class ApplicationSettingsConfiguration(BaseModel):
    """Portable settings whose values contain no credentials or filesystem paths."""

    model_config = ConfigDict(extra="forbid")

    disk_free_threshold_percent: float = Field(ge=0, le=100)


class ConfigurationDocument(BaseModel):
    """Versioned portable configuration with no database ids or credentials."""

    model_config = ConfigDict(extra="forbid")

    format: Literal[CONFIGURATION_FORMAT] = CONFIGURATION_FORMAT
    version: Literal[LEGACY_CONFIGURATION_VERSION, CONFIGURATION_VERSION] = CONFIGURATION_VERSION
    categories: list[CategoryCreate] = Field(default_factory=list)
    feeds: list[FeedConfiguration] = Field(default_factory=list)
    rules: list[RuleConfiguration] = Field(default_factory=list)
    settings: ApplicationSettingsConfiguration | None = None

    @model_validator(mode="after")
    def validate_references_and_names(self) -> "ConfigurationDocument":
        duplicates = {
            "category": _duplicate_names(item.name for item in self.categories),
            "feed": _duplicate_names(item.name for item in self.feeds),
            "rule": _duplicate_names(item.name for item in self.rules),
        }
        conflicts = [f"{kind}: {', '.join(names)}" for kind, names in duplicates.items() if names]
        if conflicts:
            raise ValueError("Duplicate names in configuration (" + "; ".join(conflicts) + ")")

        category_names = {category.name for category in self.categories}
        unknown_categories = sorted({rule.category for rule in self.rules} - category_names)
        if unknown_categories:
            raise ValueError("Rules reference categories absent from the import: " + ", ".join(unknown_categories))
        return self


@dataclass(frozen=True)
class ConfigurationImportResult:
    mode: Literal["replace", "merge"]
    categories: int
    feeds: int
    rules: int


def _duplicate_names(names: Any) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return sorted(duplicates)


def validate_configuration(value: str | bytes | Mapping[str, Any]) -> ConfigurationDocument:
    """Parse and fully validate JSON-compatible import data before database work."""

    try:
        if isinstance(value, (str, bytes)):
            raw = value.decode("utf-8") if isinstance(value, bytes) else value
            try:
                return ConfigurationDocument.model_validate_json(raw)
            except ValidationError:
                parsed = yaml.safe_load(raw)
                if not isinstance(parsed, Mapping):
                    raise ValueError("Configuration must be a JSON or YAML object")
                return ConfigurationDocument.model_validate(parsed)
        return ConfigurationDocument.model_validate(value)
    except (ValidationError, ValueError, TypeError, yaml.YAMLError) as error:
        raise ConfigurationValidationError(str(error)) from error


def canonical_configuration_json(configuration: ConfigurationDocument | Mapping[str, Any]) -> str:
    """Return a deterministic UTF-8-safe JSON representation for download or backup."""

    document = configuration if isinstance(configuration, ConfigurationDocument) else validate_configuration(configuration)
    return json.dumps(document.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_configuration_yaml(configuration: ConfigurationDocument | Mapping[str, Any]) -> str:
    """Return a safe, deterministic YAML representation for portable backup."""

    document = configuration if isinstance(configuration, ConfigurationDocument) else validate_configuration(configuration)
    return yaml.safe_dump(document.model_dump(mode="json"), allow_unicode=True, sort_keys=True)


async def export_configuration(session: AsyncSession) -> ConfigurationDocument:
    """Export persisted configuration in deterministic order and exclude secrets by design."""

    categories = list((await session.scalars(select(Category).order_by(Category.name))).all())
    feeds = list((await session.scalars(select(Feed).order_by(Feed.name))).all())
    rules = list((await session.scalars(select(Rule).order_by(Rule.priority, Rule.id))).all())
    settings = {
        item.key: item.value
        for item in (await session.scalars(select(ApplicationSetting).where(ApplicationSetting.key == DISK_FREE_THRESHOLD_SETTING))).all()
    }
    disk_threshold = _parse_disk_free_threshold(settings.get(DISK_FREE_THRESHOLD_SETTING))
    return ConfigurationDocument(
        categories=[CategoryCreate(name=item.name, color=item.color, is_interesting=item.is_interesting) for item in categories],
        feeds=[FeedConfiguration(name=item.name, url=item.url, adapter_type=item.adapter_type, proxy_url=item.proxy_url, interval_minutes=item.interval_minutes, enabled=item.enabled) for item in feeds],
        rules=[
            RuleConfiguration(
                name=item.name,
                include_keywords=item.include_keywords,
                min_seeds=item.min_seeds,
                action=item.action,
                priority=item.priority,
                category=item.category,
                freeleech_only=item.freeleech_only,
                double_upload_only=item.double_upload_only,
                max_size_bytes=item.max_size_bytes,
                uploader_whitelist=item.uploader_whitelist,
                uploader_blacklist=item.uploader_blacklist,
                qb_category=item.qb_category,
                save_path=item.save_path,
                enabled=item.enabled,
            )
            for item in rules
        ],
        settings=ApplicationSettingsConfiguration(disk_free_threshold_percent=disk_threshold) if disk_threshold is not None else None,
    )


async def import_configuration(
    session: AsyncSession,
    configuration: ConfigurationDocument | Mapping[str, Any] | str | bytes,
    *,
    mode: Literal["replace", "merge"] = "merge",
) -> ConfigurationImportResult:
    """Atomically apply validated configuration.

    ``replace`` makes persisted feeds, rules, and categories exactly match the
    document. ``merge`` updates records by name and leaves records not mentioned
    in the document untouched. The caller may wrap this in a wider transaction;
    otherwise this function commits its own transaction.
    """

    if mode not in {"replace", "merge"}:
        raise ConfigurationValidationError("Import mode must be 'replace' or 'merge'")
    document = configuration if isinstance(configuration, ConfigurationDocument) else validate_configuration(configuration)

    transaction = session.begin_nested() if session.in_transaction() else session.begin()
    async with transaction:
        if mode == "replace":
            # Rules refer to categories logically, and releases may refer to feeds.
            # Neither relation is an FK today, but deleting dependents first keeps
            # this safe if constraints are added later.
            await session.execute(delete(Rule))
            await session.execute(delete(TrackerCredential))
            await session.execute(delete(Feed))
            await session.execute(delete(Category))
            await session.execute(delete(ApplicationSetting))

        for category_data in document.categories:
            await _upsert_by_name(session, Category, category_data.model_dump(), mode)
        for feed_data in document.feeds:
            data = feed_data.model_dump()
            await _upsert_by_name(session, Feed, data, mode)
        for rule_data in document.rules:
            data = rule_data.model_dump()
            await _upsert_by_name(session, Rule, data, mode)
        if document.settings is not None:
            await set_disk_free_threshold_percent(session, document.settings.disk_free_threshold_percent)

    return ConfigurationImportResult(mode=mode, categories=len(document.categories), feeds=len(document.feeds), rules=len(document.rules))


async def _upsert_by_name(session: AsyncSession, model: type[Category] | type[Feed] | type[Rule], data: dict[str, Any], mode: Literal["replace", "merge"]) -> None:
    if mode == "replace":
        session.add(model(**data))
        return
    existing = await session.scalar(select(model).where(model.name == data["name"]))
    if existing is None:
        session.add(model(**data))
        return
    for field, value in data.items():
        setattr(existing, field, value)


def _parse_disk_free_threshold(value: str | None) -> float | None:
    """Return a stored threshold only when it is valid and safe to export."""

    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if 0 <= parsed <= 100 else None


async def get_disk_free_threshold_percent(session: AsyncSession, *, default: float = 10.0) -> float:
    """Read the persisted low-disk threshold, falling back to a safe default."""

    if not 0 <= default <= 100:
        raise ValueError("default disk threshold must be between 0 and 100")
    stored = await session.scalar(select(ApplicationSetting.value).where(ApplicationSetting.key == DISK_FREE_THRESHOLD_SETTING))
    parsed = _parse_disk_free_threshold(stored)
    return parsed if parsed is not None else default


async def set_disk_free_threshold_percent(session: AsyncSession, threshold: float) -> None:
    """Persist a validated non-secret disk threshold without committing the session."""

    if not 0 <= threshold <= 100:
        raise ValueError("disk threshold must be between 0 and 100")
    value = f"{threshold:g}"
    existing = await session.scalar(select(ApplicationSetting).where(ApplicationSetting.key == DISK_FREE_THRESHOLD_SETTING))
    if existing is None:
        session.add(ApplicationSetting(key=DISK_FREE_THRESHOLD_SETTING, value=value))
    else:
        existing.value = value
