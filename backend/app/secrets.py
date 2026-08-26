"""Encrypted-at-rest storage for tracker cookies and passkeys.

Only this module decrypts tracker credentials.  Configuration export/import
does not import this module and therefore cannot serialize plaintext secrets.
The encryption key is supplied exclusively through ``TORRENTFLOW_ENCRYPTION_KEY``
and must be a Fernet-compatible, URL-safe base64 32-byte key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Feed, TrackerCredential

ENCRYPTION_KEY_ENV = "TORRENTFLOW_ENCRYPTION_KEY"


class SecretStorageUnavailable(RuntimeError):
    """Raised when encrypted credential storage is not configured correctly."""


class SecretStorageCorrupted(RuntimeError):
    """Raised when ciphertext cannot be authenticated with the configured key."""


class _Unset:
    pass


UNSET = _Unset()


@dataclass(frozen=True, repr=False)
class TrackerCredentials:
    """Plaintext credentials for internal adapter use only; never serialize this."""

    cookie: str | None
    passkey: str | None


def _fernet() -> Fernet:
    raw_key = os.getenv(ENCRYPTION_KEY_ENV)
    if not raw_key:
        raise SecretStorageUnavailable(f"{ENCRYPTION_KEY_ENV} must be configured before storing tracker credentials")
    try:
        return Fernet(raw_key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        raise SecretStorageUnavailable(f"{ENCRYPTION_KEY_ENV} must be a valid Fernet key") from error


def _encrypt(value: str | None, cipher: Fernet) -> str | None:
    return cipher.encrypt(value.encode("utf-8")).decode("ascii") if value is not None else None


def _decrypt(value: str | None, cipher: Fernet) -> str | None:
    if value is None:
        return None
    try:
        return cipher.decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as error:
        raise SecretStorageCorrupted("Tracker credential ciphertext cannot be decrypted with the configured key") from error


async def store_tracker_credentials(
    session: AsyncSession,
    feed_id: int,
    *,
    cookie: str | None | _Unset = UNSET,
    passkey: str | None | _Unset = UNSET,
) -> None:
    """Encrypt and upsert credentials for an existing feed without committing.

    Passing ``None`` clears that credential; omitting it preserves its previous
    value.  This module intentionally has no public serialization API.
    """

    cipher = _fernet()
    if await session.scalar(select(Feed.id).where(Feed.id == feed_id)) is None:
        raise ValueError("Cannot store credentials for an unknown feed")
    credential = await session.scalar(select(TrackerCredential).where(TrackerCredential.feed_id == feed_id))
    if credential is None:
        if cookie is None and passkey is None:
            return
        session.add(
            TrackerCredential(
                feed_id=feed_id,
                encrypted_cookie=_encrypt(cookie, cipher) if not isinstance(cookie, _Unset) else None,
                encrypted_passkey=_encrypt(passkey, cipher) if not isinstance(passkey, _Unset) else None,
            )
        )
    else:
        if not isinstance(cookie, _Unset):
            credential.encrypted_cookie = _encrypt(cookie, cipher)
        if not isinstance(passkey, _Unset):
            credential.encrypted_passkey = _encrypt(passkey, cipher)
        if credential.encrypted_cookie is None and credential.encrypted_passkey is None:
            await session.delete(credential)


async def load_tracker_credentials(session: AsyncSession, feed_id: int) -> TrackerCredentials | None:
    """Decrypt credentials for an adapter; plaintext must stay in process memory."""

    credential = await session.scalar(select(TrackerCredential).where(TrackerCredential.feed_id == feed_id))
    if credential is None:
        return None
    cipher = _fernet()
    return TrackerCredentials(cookie=_decrypt(credential.encrypted_cookie, cipher), passkey=_decrypt(credential.encrypted_passkey, cipher))


async def delete_tracker_credentials(session: AsyncSession, feed_id: int) -> bool:
    """Delete credentials for a feed without committing and report whether any existed."""

    credential = await session.scalar(select(TrackerCredential).where(TrackerCredential.feed_id == feed_id))
    if credential is None:
        return False
    await session.delete(credential)
    return True


async def tracker_credentials_configured(session: AsyncSession, feed_id: int) -> bool:
    """Return only configuration state, never plaintext or ciphertext."""

    return await session.scalar(select(TrackerCredential.id).where(TrackerCredential.feed_id == feed_id)) is not None
