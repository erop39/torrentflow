import asyncio

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import pytest
from uuid import uuid4

from app.main import app, scan_due_feeds_once, validate_runtime_configuration
from app.backup import backup_retention


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"password": "change-me"})
    assert response.status_code == 200

def test_health_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert len(body["services"]) == 5
    assert {item["status"] for item in body["services"]} <= {"healthy", "degraded", "unconfigured"}
    assert {item["name"] for item in body["services"] if item["status"] == "unconfigured"} == {"qBittorrent", "Telegram"}
    assert next(item for item in body["services"] if item["name"] == "Disk")["status"] in {"healthy", "degraded"}


def test_readiness_checks_database() -> None:
    with TestClient(app) as client:
        response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True}


def test_production_rejects_placeholder_secrets(monkeypatch) -> None:
    monkeypatch.setattr("app.main.IS_PRODUCTION", True)
    monkeypatch.setattr("app.main.ADMIN_PASSWORD", "change-me")
    monkeypatch.setattr("app.main.SESSION_SECRET", "replace-this-dev-session-secret")
    with pytest.raises(RuntimeError, match="Production requires"):
        validate_runtime_configuration()


def test_backup_retention_requires_at_least_one_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("TORRENTFLOW_BACKUP_RETENTION", "0")
    with pytest.raises(ValueError, match="at least 1"):
        backup_retention()


def test_recent_releases_contract() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/releases")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_feed_crud_contract() -> None:
    name = f"Test RSS {uuid4()}"
    with TestClient(app) as client:
        login(client)
        created = client.post("/api/feeds", json={"name": name, "url": "https://example.test/rss", "interval_minutes": 20})
        assert created.status_code == 201
        feed_id = created.json()["id"]

        listed = client.get("/api/feeds")
        assert any(feed["id"] == feed_id for feed in listed.json())

        updated = client.patch(f"/api/feeds/{feed_id}", json={"enabled": False})
        deleted = client.delete(f"/api/feeds/{feed_id}")
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert deleted.status_code == 204


def test_tracker_credentials_api_encrypts_without_serializing_or_orphaning(monkeypatch) -> None:
    monkeypatch.setenv("TORRENTFLOW_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    marker = f"secret-{uuid4()}"
    with TestClient(app) as client:
        login(client)
        feed = client.post("/api/feeds", json={"name": f"Credential {uuid4()}", "url": "https://example.test/rss"})
        feed_id = feed.json()["id"]
        stored = client.put(f"/api/feeds/{feed_id}/credentials", json={"cookie": marker, "passkey": marker})
        status = client.get(f"/api/feeds/{feed_id}/credentials")
        exported = client.get("/api/config/export")
        deleted = client.delete(f"/api/feeds/{feed_id}")
        after_delete = client.get(f"/api/feeds/{feed_id}/credentials")
    assert stored.json() == {"configured": True}
    assert status.json() == {"configured": True}
    assert marker not in exported.text
    assert deleted.status_code == 204
    assert after_delete.json() == {"configured": False}


def test_protected_endpoint_requires_login() -> None:
    with TestClient(app) as client:
        response = client.get("/api/feeds")
    assert response.status_code == 401


def test_create_rule_contract() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.post("/api/rules", json={"name": f"Linux {uuid4()}", "include_keywords": "ubuntu,debian", "min_seeds": 5, "action": "notify", "priority": 10})
    assert response.status_code == 201
    assert response.json()["min_seeds"] == 5


def test_smart_rule_and_per_feed_proxy_contract() -> None:
    with TestClient(app) as client:
        login(client)
        feed = client.post("/api/feeds", json={"name": f"TL {uuid4()}", "url": "https://example.test/rss", "adapter_type": "torrentleech", "proxy_url": "socks5://127.0.0.1:1080"})
        rule = client.post("/api/rules", json={"name": f"Smart {uuid4()}", "freeleech_only": True, "double_upload_only": True, "max_size_bytes": 5_000_000_000, "uploader_whitelist": "Trusted,Other", "uploader_blacklist": "Blocked", "qb_category": "movies", "save_path": "/downloads/movies"})
    assert feed.status_code == 201
    assert feed.json()["proxy_url"] == "socks5://127.0.0.1:1080"
    assert rule.status_code == 201
    assert rule.json()["freeleech_only"] is True
    assert rule.json()["qb_category"] == "movies"


def test_rule_rejects_unknown_action() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.post("/api/rules", json={"name": f"Invalid {uuid4()}", "action": "autoad"})
    assert response.status_code == 422


def test_feed_rejects_local_or_non_http_url() -> None:
    with TestClient(app) as client:
        login(client)
        localhost = client.post("/api/feeds", json={"name": f"Local {uuid4()}", "url": "http://127.0.0.1:8000/rss"})
        wrong_scheme = client.post("/api/feeds", json={"name": f"File {uuid4()}", "url": "file:///etc/passwd"})
    assert localhost.status_code == 422
    assert wrong_scheme.status_code == 422


def test_feed_rejects_unknown_adapter_and_proxy_credentials() -> None:
    with TestClient(app) as client:
        login(client)
        unknown_adapter = client.post("/api/feeds", json={"name": f"Unknown adapter {uuid4()}", "url": "https://example.test/rss", "adapter_type": "unsupported"})
        credential_proxy = client.post("/api/feeds", json={"name": f"Credential proxy {uuid4()}", "url": "https://example.test/rss", "proxy_url": "socks5://user:password@proxy.example:1080"})
    assert unknown_adapter.status_code == 422
    assert credential_proxy.status_code == 422


def test_categories_control_rule_validation_and_default_visibility() -> None:
    with TestClient(app) as client:
        login(client)
        categories = client.get("/api/categories")
        assert {category["name"] for category in categories.json()} >= {"series", "linux"}
        created = client.post("/api/categories", json={"name": "movies", "color": "#f97316", "is_interesting": False})
        assert created.status_code == 201
        updated = client.patch(f"/api/categories/{created.json()['id']}", json={"is_interesting": True})
        rule = client.post("/api/rules", json={"name": f"Movies {uuid4()}", "category": "movies"})
        invalid_rule = client.post("/api/rules", json={"name": f"Unknown {uuid4()}", "category": "unknown"})
    assert updated.json()["is_interesting"] is True
    assert rule.status_code == 201
    assert invalid_rule.status_code == 422


def test_feed_check_returns_persisted_release_results(monkeypatch) -> None:
    external_id = f"https://example.test/release/{uuid4()}"
    keyword = f"release-{uuid4()}"

    async def fake_fetch_entries(_: str) -> list[dict[str, str]]:
        return [{"external_id": external_id, "title": f"Test {keyword}", "link": external_id}]

    monkeypatch.setattr("app.main.fetch_entries", fake_fetch_entries)
    with TestClient(app) as client:
        login(client)
        rule = client.post("/api/rules", json={"name": f"Rule {uuid4()}", "include_keywords": keyword, "min_seeds": 0, "action": "notify", "priority": 1})
        assert rule.status_code == 201
        feed = client.post("/api/feeds", json={"name": f"Feed {uuid4()}", "url": "https://example.test/rss", "interval_minutes": 30})
        assert feed.status_code == 201

        checked = client.post(f"/api/feeds/{feed.json()['id']}/check")

    assert checked.status_code == 200
    assert checked.json() == {"discovered": 1, "new": 1, "items": [{"title": f"Test {keyword}", "status": "notify", "rule_name": rule.json()["name"], "category": "series", "seeds": 0}]}
    with TestClient(app) as client:
        login(client)
        releases = client.get("/api/releases")
    assert any(item["title"] == f"Test {keyword}" and item["source"] == feed.json()["name"] for item in releases.json())


def test_auto_add_and_telegram_events_are_audited(monkeypatch) -> None:
    external_id = f"https://example.test/release/{uuid4()}"
    keyword = f"release-{uuid4()}"
    calls: list[tuple[str, str]] = []

    async def fake_fetch_entries(_: str) -> list[dict[str, str]]:
        return [{"external_id": external_id, "title": f"Test {keyword}", "link": external_id}]

    async def fake_qbit_add(url: str) -> None:
        calls.append(("qbit", url))

    async def fake_telegram_send(message: str) -> None:
        calls.append(("telegram", message))

    monkeypatch.setattr("app.main.fetch_entries", fake_fetch_entries)
    monkeypatch.setattr("app.main.qbit_add", fake_qbit_add)
    monkeypatch.setattr("app.main.telegram_send", fake_telegram_send)
    monkeypatch.setattr("app.main.qbit_configured", lambda: True)
    monkeypatch.setattr("app.main.telegram_configured", lambda: True)
    with TestClient(app) as client:
        login(client)
        client.post("/api/rules", json={"name": f"Rule {uuid4()}", "include_keywords": keyword, "action": "both", "priority": 1})
        feed = client.post("/api/feeds", json={"name": f"Feed {uuid4()}", "url": "https://example.test/rss"})
        checked = client.post(f"/api/feeds/{feed.json()['id']}/check")
        audit = client.get("/api/audit")

    assert checked.status_code == 200
    assert calls[0] == ("qbit", external_id)
    assert calls[1][0] == "telegram"
    event_types = {event["event_type"] for event in audit.json()}
    assert {"release.discovered", "qbit.added", "telegram.sent"} <= event_types


def test_smart_auto_add_filters_metadata_and_maps_qb_target(monkeypatch) -> None:
    external_id = f"https://example.test/smart/{uuid4()}"
    calls: list[tuple[str, dict[str, str]]] = []

    async def fake_fetch_entries(_: str) -> list[dict[str, str | int | bool]]:
        return [{"external_id": external_id, "title": "Trusted release", "link": external_id, "seeds": 25, "freeleech": True, "double_upload": True, "size_bytes": 1000, "uploader": "Trusted"}]

    async def fake_qbit_add(url: str, **kwargs: str) -> None:
        calls.append((url, kwargs))

    monkeypatch.setattr("app.main.fetch_entries", fake_fetch_entries)
    monkeypatch.setattr("app.main.qbit_add", fake_qbit_add)
    monkeypatch.setattr("app.main.qbit_configured", lambda: True)
    with TestClient(app) as client:
        login(client)
        created = client.post("/api/rules", json={"name": f"Smart {uuid4()}", "action": "auto_add", "priority": 0, "freeleech_only": True, "double_upload_only": True, "max_size_bytes": 2000, "uploader_whitelist": "trusted", "uploader_blacklist": "blocked", "qb_category": "movies", "save_path": "/downloads/movies"})
        feed = client.post("/api/feeds", json={"name": f"Feed {uuid4()}", "url": "https://example.test/rss"})
        checked = client.post(f"/api/feeds/{feed.json()['id']}/check")
    assert created.status_code == 201
    assert checked.json()["new"] == 1
    assert calls == [(external_id, {"category": "movies", "save_path": "/downloads/movies"})]


def test_configuration_export_and_yaml_merge_import_are_secret_free() -> None:
    category_name = f"export-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        login(client)
        assert client.post("/api/categories", json={"name": category_name, "color": "#112233", "is_interesting": True}).status_code == 201
        assert client.post("/api/rules", json={"name": f"Export {uuid4()}", "category": category_name, "freeleech_only": True, "qb_category": "archive"}).status_code == 201
        exported = client.get("/api/config/export")
        exported_yaml = client.get("/api/config/export?format=yaml")
        assert client.post("/api/config/import", content=f"format: torrentflow/configuration\nversion: 1\ncategories:\n  - name: imported\n    color: '#445566'\n    is_interesting: false\nfeeds: []\nrules: []\n", headers={"content-type": "application/yaml"}).status_code == 200
        categories = client.get("/api/categories")
    assert exported.status_code == 200
    assert exported_yaml.status_code == 200
    document = exported.json()
    assert document["format"] == "torrentflow/configuration"
    assert any(rule["freeleech_only"] and rule["qb_category"] == "archive" for rule in document["rules"])
    assert "TORRENTFLOW_" not in exported.text
    assert "format: torrentflow/configuration" in exported_yaml.text
    assert any(category["name"] == "imported" for category in categories.json())


def test_integration_status_and_connection_tests(monkeypatch) -> None:
    async def fake_downloads() -> list[dict[str, object]]:
        return [{"name": "Ubuntu", "progress": 0.5, "state": "downloading", "dlspeed": 1_000_000}]

    async def fake_telegram_send(_: str) -> None:
        return None

    monkeypatch.setattr("app.main.qbit_configured", lambda: True)
    monkeypatch.setattr("app.main.telegram_configured", lambda: True)
    monkeypatch.setattr("app.main.qbit_downloads", fake_downloads)
    monkeypatch.setattr("app.main.telegram_send", fake_telegram_send)
    with TestClient(app) as client:
        login(client)
        status = client.get("/api/integrations/status")
        downloads = client.get("/api/downloads")
        qbit_test = client.post("/api/integrations/qbittorrent/test")
        telegram_test = client.post("/api/integrations/telegram/test")
        audit = client.get("/api/audit")

    assert status.json() == {"qbit_configured": True, "telegram_configured": True}
    assert downloads.json() == [{"name": "Ubuntu", "progress": 0.5, "state": "downloading", "dlspeed": 1_000_000}]
    assert qbit_test.json() == {"ok": True}
    assert telegram_test.json() == {"ok": True}
    event_types = {event["event_type"] for event in audit.json()}
    assert {"qbit.tested", "telegram.tested"} <= event_types


def test_scheduler_scans_due_feed(monkeypatch) -> None:
    external_id = f"https://example.test/scheduled/{uuid4()}"

    async def fake_fetch_entries(_: str) -> list[dict[str, str]]:
        return [{"external_id": external_id, "title": "Scheduled release", "link": external_id}]

    monkeypatch.setattr("app.main.fetch_entries", fake_fetch_entries)
    with TestClient(app) as client:
        login(client)
        feed = client.post("/api/feeds", json={"name": f"Scheduled {uuid4()}", "url": "https://example.test/rss", "interval_minutes": 10})
        assert feed.status_code == 201
        asyncio.run(scan_due_feeds_once())
        releases = client.get("/api/releases")

    assert any(release["link"] == external_id for release in releases.json())


def test_failed_auto_add_is_audited(monkeypatch) -> None:
    external_id = f"https://example.test/failure/{uuid4()}"
    keyword = f"failure-{uuid4()}"

    async def fake_fetch_entries(_: str) -> list[dict[str, str]]:
        return [{"external_id": external_id, "title": keyword, "link": external_id}]

    async def failed_add(_: str) -> None:
        raise RuntimeError("connection refused")

    monkeypatch.setattr("app.main.fetch_entries", fake_fetch_entries)
    monkeypatch.setattr("app.main.qbit_add", failed_add)
    monkeypatch.setattr("app.main.qbit_configured", lambda: True)
    with TestClient(app) as client:
        login(client)
        client.post("/api/rules", json={"name": f"Rule {uuid4()}", "include_keywords": keyword, "action": "auto_add", "priority": 1})
        feed = client.post("/api/feeds", json={"name": f"Feed {uuid4()}", "url": "https://example.test/rss"})
        client.post(f"/api/feeds/{feed.json()['id']}/check")
        audit = client.get("/api/audit")

    assert any(event["event_type"] == "qbit.failed" and "connection refused" in event["message"] for event in audit.json())
