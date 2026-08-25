import asyncio

import httpx
import pytest

from app import integrations


class FakeAsyncClient:
    """Small transport double that records httpx calls without network access."""

    responses: list[httpx.Response] = []
    instances: list["FakeAsyncClient"] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.calls: list[tuple[str, str, object]] = []
        self.__class__.instances.append(self)

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, *, data: object = None, json: object = None) -> httpx.Response:
        self.calls.append(("POST", url, data if data is not None else json))
        return self.__class__.responses.pop(0)

    async def request(self, method: str, url: str, *, data: object = None) -> httpx.Response:
        self.calls.append((method, url, data))
        return self.__class__.responses.pop(0)


def response(status_code: int, *, text: str = "", json: object = None) -> httpx.Response:
    request = httpx.Request("POST", "https://adapter.test/request")
    if json is not None:
        return httpx.Response(status_code, json=json, request=request)
    return httpx.Response(status_code, text=text, request=request)


@pytest.fixture(autouse=True)
def fake_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.responses = []
    FakeAsyncClient.instances = []
    monkeypatch.setattr(integrations.httpx, "AsyncClient", FakeAsyncClient)


def test_configuration_requires_all_required_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TORRENTFLOW_QBITTORRENT_URL", raising=False)
    monkeypatch.delenv("TORRENTFLOW_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TORRENTFLOW_TELEGRAM_CHAT_ID", raising=False)
    assert integrations.qbit_configured() is False
    assert integrations.telegram_configured() is False

    monkeypatch.setenv("TORRENTFLOW_QBITTORRENT_URL", "https://qbit.example")
    monkeypatch.setenv("TORRENTFLOW_TELEGRAM_BOT_TOKEN", "test-token")
    assert integrations.qbit_configured() is True
    assert integrations.telegram_configured() is False

    monkeypatch.setenv("TORRENTFLOW_TELEGRAM_CHAT_ID", "12345")
    assert integrations.telegram_configured() is True


def test_qbit_request_authenticates_then_uses_authenticated_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TORRENTFLOW_QBITTORRENT_URL", "https://qbit.example/")
    monkeypatch.setenv("TORRENTFLOW_QBITTORRENT_USERNAME", "operator")
    monkeypatch.setenv("TORRENTFLOW_QBITTORRENT_PASSWORD", "test-password")
    FakeAsyncClient.responses = [response(200, text="Ok."), response(200, json={"ok": True})]

    result = asyncio.run(integrations.qbit_request("/api/v2/torrents/add", method="POST", data={"urls": "https://feed.example/item"}))

    assert result.json() == {"ok": True}
    client = FakeAsyncClient.instances[0]
    assert client.kwargs == {"timeout": 15, "follow_redirects": True}
    assert client.calls == [
        ("POST", "https://qbit.example/api/v2/auth/login", {"username": "operator", "password": "test-password"}),
        ("POST", "https://qbit.example/api/v2/torrents/add", {"urls": "https://feed.example/item"}),
    ]


def test_qbit_request_rejects_missing_url_or_failed_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TORRENTFLOW_QBITTORRENT_URL", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        asyncio.run(integrations.qbit_request("/api/v2/torrents/info"))

    monkeypatch.setenv("TORRENTFLOW_QBITTORRENT_URL", "https://qbit.example")
    FakeAsyncClient.responses = [response(200, text="Fails.")]
    with pytest.raises(RuntimeError, match="authentication failed"):
        asyncio.run(integrations.qbit_request("/api/v2/torrents/info"))


def test_qbit_downloads_returns_adapter_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TORRENTFLOW_QBITTORRENT_URL", "https://qbit.example")
    downloads = [{"name": "Ubuntu", "progress": 0.5}]
    FakeAsyncClient.responses = [response(200, text="Ok."), response(200, json=downloads)]

    assert asyncio.run(integrations.qbit_downloads()) == downloads


def test_telegram_send_posts_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TORRENTFLOW_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TORRENTFLOW_TELEGRAM_CHAT_ID", "12345")
    FakeAsyncClient.responses = [response(200, json={"ok": True})]

    asyncio.run(integrations.telegram_send("TorrentFlow test"))

    client = FakeAsyncClient.instances[0]
    assert client.kwargs == {"timeout": 15}
    assert client.calls == [
        ("POST", "https://api.telegram.org/bottest-token/sendMessage", {"chat_id": "12345", "text": "TorrentFlow test", "disable_web_page_preview": True})
    ]


def test_telegram_send_requires_configuration_and_surfaces_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TORRENTFLOW_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TORRENTFLOW_TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        asyncio.run(integrations.telegram_send("ignored"))

    monkeypatch.setenv("TORRENTFLOW_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TORRENTFLOW_TELEGRAM_CHAT_ID", "12345")
    FakeAsyncClient.responses = [response(403, text="forbidden")]
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(integrations.telegram_send("denied"))
