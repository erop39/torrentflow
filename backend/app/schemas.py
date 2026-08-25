from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"


class ServiceHealth(BaseModel):
    name: str
    status: ServiceStatus
    detail: str


class HealthResponse(BaseModel):
    services: list[ServiceHealth]
    checked_at: datetime


class ReleaseOutcome(StrEnum):
    ADDED = "added"
    NOTIFY = "notify"


class Release(BaseModel):
    id: str
    title: str
    source: str
    rule: str
    category: str
    size: str
    seeds: int = Field(ge=0)
    outcome: ReleaseOutcome


class FeedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1)
    adapter_type: str = "generic_rss"
    interval_minutes: int = Field(default=30, ge=10, le=1440)


class FeedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=10, le=1440)


class FeedResponse(BaseModel):
    id: int
    name: str
    url: str
    adapter_type: str
    enabled: bool
    interval_minutes: int
    last_checked_at: datetime | None = None

    model_config = {"from_attributes": True}


class FeedCheckItem(BaseModel):
    title: str
    status: str
    rule_name: str | None = None
    category: str
    seeds: int


class FeedCheckResponse(BaseModel):
    discovered: int
    new: int
    items: list[FeedCheckItem]


class StoredReleaseResponse(BaseModel):
    id: int
    title: str
    link: str
    source: str
    rule_name: str | None = None
    status: str
    category: str
    seeds: int
    created_at: datetime


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


class SessionResponse(BaseModel):
    authenticated: bool


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    include_keywords: str = ""
    min_seeds: int = Field(default=0, ge=0)
    action: str = "notify"
    priority: int = Field(default=100, ge=0)
    category: str = Field(default="series", min_length=1, max_length=32)


class RuleResponse(RuleCreate):
    id: int
    enabled: bool

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    color: str = Field(default="#ad8cff", pattern=r"^#[0-9a-fA-F]{6}$")
    is_interesting: bool = True


class CategoryUpdate(BaseModel):
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    is_interesting: bool | None = None


class CategoryResponse(CategoryCreate):
    id: int

    model_config = {"from_attributes": True}


class IntegrationStatus(BaseModel):
    qbit_configured: bool
    telegram_configured: bool


class DownloadItem(BaseModel):
    name: str
    progress: float
    state: str
    dlspeed: int


class AuditEventResponse(BaseModel):
    id: int
    event_type: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
