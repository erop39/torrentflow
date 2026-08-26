from app.release_parsing import parse_release_title
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


def test_parses_episode_into_normalized_display_and_show_group() -> None:
    parsed = parse_release_title("The.Example.Show.S03E05.1080p.WEB-DL.x265-GROUP")

    assert parsed.display_title == "The Example Show S03E05"
    assert parsed.group_key == "series:the-example-show"
    assert parsed.media_type == "series"
    assert parsed.series_title == "The Example Show"
    assert parsed.season == 3
    assert parsed.episode == 5


def test_parses_movie_with_year_and_stable_group() -> None:
    parsed = parse_release_title("Some Movie 2024 2160p BluRay REMUX")

    assert parsed.display_title == "Some Movie (2024)"
    assert parsed.group_key == "movie:some-movie:2024"
    assert parsed.media_type == "movie"
    assert parsed.year == 2024


def test_unknown_or_broken_title_never_blocks_ingestion(monkeypatch) -> None:
    parsed = parse_release_title("Unusual [release] name")
    assert parsed.display_title == "Unusual [release] name"
    assert parsed.group_key == "unknown:unusual-release-name"
    assert parsed.media_type == "unknown"

    monkeypatch.setattr("app.release_parsing.guessit", lambda _: (_ for _ in ()).throw(RuntimeError("parser error")))
    fallback = parse_release_title("Still Here")
    assert fallback.display_title == "Still Here"
    assert fallback.group_key == "unknown:still-here"


def test_scan_persists_parsed_release_fields(monkeypatch) -> None:
    external_id = f"https://example.test/releases/{uuid4()}"

    async def fake_fetch_entries(_: str) -> list[dict[str, str]]:
        return [{"external_id": external_id, "title": "The.Example.Show.S03E05.1080p.WEB-DL", "link": external_id}]

    monkeypatch.setattr("app.main.fetch_entries", fake_fetch_entries)
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"password": "change-me"}).status_code == 200
        feed = client.post("/api/feeds", json={"name": f"Parsing {uuid4()}", "url": "https://example.test/rss"})
        assert client.post(f"/api/feeds/{feed.json()['id']}/check").status_code == 200
        releases = client.get("/api/releases").json()

    release = next(item for item in releases if item["link"] == external_id)
    assert release["display_title"] == "The Example Show S03E05"
    assert release["group_key"] == "series:the-example-show"
    assert release["media_type"] == "series"
