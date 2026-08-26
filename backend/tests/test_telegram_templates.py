import asyncio

from fastapi.testclient import TestClient
import pytest

from app.configuration import (
    ApplicationSettingsConfiguration,
    ConfigurationDocument,
    export_configuration,
    get_telegram_message_template,
    import_configuration,
)
from app.database import SessionLocal
from app.main import app
from app.telegram_templates import (
    DEFAULT_TELEGRAM_MESSAGE_TEMPLATE,
    TelegramTemplateValidationError,
    render_telegram_message,
    validate_telegram_message_template,
)


def login(client: TestClient) -> None:
    assert client.post("/api/auth/login", json={"password": "change-me"}).status_code == 200


def test_template_validation_is_strict_and_rendering_falls_back() -> None:
    template = "{feed}: {title} / {seeds}"
    assert validate_telegram_message_template(template) == template
    assert render_telegram_message(template, {"feed": "TL", "title": "Release", "seeds": 42}) == "TL: Release / 42"

    with pytest.raises(TelegramTemplateValidationError, match="Unsupported"):
        validate_telegram_message_template("{title.__class__}")
    with pytest.raises(TelegramTemplateValidationError, match="unmatched braces"):
        validate_telegram_message_template("{title")
    with pytest.raises(TelegramTemplateValidationError, match="format specifiers"):
        validate_telegram_message_template("{seeds:04}")

    fallback = render_telegram_message("{missing}", {"title": "Release", "rule": "Rule", "category": "series"})
    assert fallback == "TorrentFlow: Release\nRule: Rule\nCategory: series"


def test_template_setting_exports_imports_and_uses_safe_default() -> None:
    template = "[{category}] {title} — {link}"

    async def scenario() -> None:
        async with SessionLocal() as session:
            async with session.begin():
                await import_configuration(
                    session,
                    ConfigurationDocument(
                        settings=ApplicationSettingsConfiguration(telegram_message_template=template),
                    ),
                )
            assert await get_telegram_message_template(session) == template
            exported = await export_configuration(session)
            assert exported.settings is not None
            assert exported.settings.telegram_message_template == template

    asyncio.run(scenario())


def test_template_api_validates_persists_and_does_not_audit_full_content() -> None:
    template = "{feed}: {title} ({seeds})"
    with TestClient(app) as client:
        login(client)
        initial = client.get("/api/settings/telegram-template")
        updated = client.put("/api/settings/telegram-template", json={"message_template": template})
        invalid = client.put("/api/settings/telegram-template", json={"message_template": "{token}"})
        audit = client.get("/api/audit")

    assert initial.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["message_template"] == template
    assert updated.json()["supported_placeholders"] == ["category", "feed", "link", "rule", "seeds", "title"]
    assert invalid.status_code == 422
    assert all(template not in item["message"] for item in audit.json())
    assert DEFAULT_TELEGRAM_MESSAGE_TEMPLATE != ""
