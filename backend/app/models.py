from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    url: Mapped[str] = mapped_column(Text)
    adapter_type: Mapped[str] = mapped_column(String(32), default="generic_rss")
    proxy_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    include_keywords: Mapped[str] = mapped_column(Text, default="")
    min_seeds: Mapped[int] = mapped_column(Integer, default=0)
    action: Mapped[str] = mapped_column(String(16), default="notify")
    priority: Mapped[int] = mapped_column(Integer, default=100)
    category: Mapped[str] = mapped_column(String(32), default="series")
    freeleech_only: Mapped[bool] = mapped_column(Boolean, default=False)
    double_upload_only: Mapped[bool] = mapped_column(Boolean, default=False)
    max_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploader_whitelist: Mapped[str] = mapped_column(Text, default="")
    uploader_blacklist: Mapped[str] = mapped_column(Text, default="")
    qb_category: Mapped[str] = mapped_column(String(255), default="")
    save_path: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#ad8cff")
    is_interesting: Mapped[bool] = mapped_column(Boolean, default=True)


class ApplicationSetting(Base):
    """A non-secret, user-configurable application setting.

    Secrets deliberately have their own encrypted storage below so generic
    configuration export can never accidentally include them.
    """

    __tablename__ = "application_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TrackerCredential(Base):
    """Encrypted tracker authentication material, one record per feed.

    The ciphertext is encrypted with the explicitly configured application
    encryption key.  It is intentionally not part of ``Feed`` nor any export
    model, which prevents accidental serialization of cookies or passkeys.
    """

    __tablename__ = "tracker_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(Integer, unique=True)
    encrypted_cookie: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_passkey: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StoredRelease(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(Integer, index=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True)
    title: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(Text, default="")
    matched_rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new")
    category: Mapped[str] = mapped_column(String(32), default="series")
    seeds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    release_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
