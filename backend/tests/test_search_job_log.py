from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def login(client: TestClient) -> None:
    assert client.post("/api/auth/login", json={"password": "change-me"}).status_code == 200


def test_release_and_audit_search_filters_are_bounded_and_joined(monkeypatch) -> None:
    marker = uuid4().hex
    feed_name = f"Search source {marker}"
    rule_name = f"Search rule {marker}"
    external_id = f"https://example.test/releases/{marker}"

    async def fake_fetch_entries(_: str) -> list[dict[str, object]]:
        return [{"external_id": external_id, "title": f"Wanted {marker}", "link": external_id, "seeds": 17}]

    monkeypatch.setattr("app.main.fetch_entries", fake_fetch_entries)
    with TestClient(app) as client:
        login(client)
        assert client.post("/api/rules", json={"name": rule_name, "include_keywords": marker, "category": "series", "priority": 0}).status_code == 201
        feed = client.post("/api/feeds", json={"name": feed_name, "url": "https://example.test/rss"})
        assert feed.status_code == 201
        assert client.post(f"/api/feeds/{feed.json()['id']}/check").status_code == 200

        by_title = client.get("/api/releases", params={"title": marker, "min_seeds": 10, "max_seeds": 20, "limit": 1})
        by_source = client.get("/api/releases", params={"source": feed_name})
        by_rule = client.get("/api/releases", params={"rule": rule_name, "category": "series", "status": "notify"})
        literal_wildcard = client.get("/api/releases", params={"title": f"{marker}%"})
        invalid_range = client.get("/api/releases", params={"min_seeds": 20, "max_seeds": 10})
        invalid_limit = client.get("/api/releases", params={"limit": 201})
        audit = client.get("/api/audit", params={"event_type": "release.discovered", "query": marker, "limit": 1, "offset": 0})

    assert by_title.status_code == 200
    assert by_title.json()[0]["title"] == f"Wanted {marker}"
    assert by_source.status_code == 200 and any(item["source"] == feed_name for item in by_source.json())
    assert by_rule.status_code == 200 and any(item["rule_name"] == rule_name for item in by_rule.json())
    assert literal_wildcard.json() == []
    assert invalid_range.status_code == 422
    assert invalid_limit.status_code == 422
    assert audit.status_code == 200 and any(marker in item["message"] for item in audit.json())


def test_feed_run_log_records_success_and_secret_safe_failure(monkeypatch) -> None:
    marker = uuid4().hex
    feed_name = f"Run log {marker}"
    external_id = f"https://example.test/runs/{marker}"

    async def successful_fetch(_: str) -> list[dict[str, object]]:
        return [{"external_id": external_id, "title": f"Run success {marker}", "link": external_id}]

    monkeypatch.setattr("app.main.fetch_entries", successful_fetch)
    with TestClient(app) as client:
        login(client)
        feed = client.post("/api/feeds", json={"name": feed_name, "url": "https://example.test/rss"})
        assert feed.status_code == 201
        feed_id = feed.json()["id"]
        assert client.post(f"/api/feeds/{feed_id}/check").status_code == 200
        successful_runs = client.get("/api/feed-runs", params={"feed_id": feed_id, "status": "succeeded", "limit": 1})

        secret = f"tracker-cookie-{uuid4()}"

        async def failed_fetch(_: str) -> list[dict[str, object]]:
            raise RuntimeError(secret)

        monkeypatch.setattr("app.main.fetch_entries", failed_fetch)
        with TestClient(app, raise_server_exceptions=False) as failing_client:
            login(failing_client)
            failed = failing_client.post(f"/api/feeds/{feed_id}/check")
            failed_runs = failing_client.get("/api/feed-runs", params={"feed_id": feed_id, "status": "failed", "limit": 1})

    assert successful_runs.status_code == 200
    assert successful_runs.json()[0]["discovered"] == 1
    assert successful_runs.json()[0]["new_releases"] == 1
    assert successful_runs.json()[0]["duration_ms"] >= 0
    assert failed.status_code == 500
    assert failed_runs.status_code == 200
    latest = failed_runs.json()[0]
    assert latest["error_summary"] == "Scan failed (RuntimeError)"
    assert secret not in failed_runs.text
