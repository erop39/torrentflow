import asyncio

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
    assert len(body["services"]) == 4
    assert {item["status"] for item in body["services"]} <= {"healthy", "degraded", "unconfigured"}
    assert {item["name"] for item in body["services"] if item["status"] == "unconfigured"} == {"qBittorrent", "Telegram"}


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
