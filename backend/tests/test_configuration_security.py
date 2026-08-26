import asyncio

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.configuration import (
    CONFIGURATION_VERSION,
    ConfigurationDocument,
    ApplicationSettingsConfiguration,
    export_configuration,
    get_disk_free_threshold_percent,
    import_configuration,
)
from app.database import SessionLocal
from app.migrations import upgrade_database
from app.models import Feed, TrackerCredential
from app.secrets import SecretStorageUnavailable, load_tracker_credentials, store_tracker_credentials


upgrade_database()


def test_tracker_credentials_are_encrypted_and_omitted_from_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TORRENTFLOW_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    async def scenario() -> None:
        async with SessionLocal() as session:
            async with session.begin():
                feed = Feed(name="encrypted-credentials-feed", url="https://example.test/rss")
                session.add(feed)
                await session.flush()
                await store_tracker_credentials(session, feed.id, cookie="session=very-secret", passkey="passkey-very-secret")
                await session.flush()

                ciphertext = await session.scalar(select(TrackerCredential).where(TrackerCredential.feed_id == feed.id))
                assert ciphertext is not None
                assert ciphertext.encrypted_cookie != "session=very-secret"
                assert ciphertext.encrypted_passkey != "passkey-very-secret"

                restored = await load_tracker_credentials(session, feed.id)
                assert restored is not None
                assert restored.cookie == "session=very-secret"
                assert restored.passkey == "passkey-very-secret"

                document = await export_configuration(session)
                serialized = document.model_dump_json()
                assert "very-secret" not in serialized
                assert "encrypted_cookie" not in serialized

    asyncio.run(scenario())


def test_tracker_credentials_require_an_explicit_valid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TORRENTFLOW_ENCRYPTION_KEY", raising=False)

    async def scenario() -> None:
        async with SessionLocal() as session:
            async with session.begin():
                feed = Feed(name="missing-key-feed", url="https://example.test/rss")
                session.add(feed)
                await session.flush()
                with pytest.raises(SecretStorageUnavailable, match="TORRENTFLOW_ENCRYPTION_KEY"):
                    await store_tracker_credentials(session, feed.id, cookie="not persisted")

    asyncio.run(scenario())


def test_configuration_exports_persisted_disk_threshold_and_merge_is_default() -> None:
    async def scenario() -> None:
        async with SessionLocal() as session:
            async with session.begin():
                existing = Feed(name="configuration-merge-existing", url="https://example.test/existing")
                session.add(existing)
                await import_configuration(
                    session,
                    ConfigurationDocument(
                        settings=ApplicationSettingsConfiguration(disk_free_threshold_percent=17.5),
                    ),
                )

            assert await session.scalar(select(Feed).where(Feed.name == "configuration-merge-existing")) is not None
            assert await get_disk_free_threshold_percent(session) == 17.5
            exported = await export_configuration(session)
            assert exported.version == CONFIGURATION_VERSION
            assert exported.settings is not None
            assert exported.settings.disk_free_threshold_percent == 17.5

    asyncio.run(scenario())
