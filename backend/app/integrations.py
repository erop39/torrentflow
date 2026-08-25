import os
from urllib.parse import urlencode

import httpx


def qbit_configured() -> bool:
    return bool(os.getenv("TORRENTFLOW_QBITTORRENT_URL"))


def telegram_configured() -> bool:
    return bool(os.getenv("TORRENTFLOW_TELEGRAM_BOT_TOKEN") and os.getenv("TORRENTFLOW_TELEGRAM_CHAT_ID"))


async def qbit_request(path: str, *, method: str = "GET", data: dict[str, str] | None = None) -> httpx.Response:
    base_url = os.getenv("TORRENTFLOW_QBITTORRENT_URL", "").rstrip("/")
    if not base_url:
        raise RuntimeError("qBittorrent is not configured")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        login = await client.post(f"{base_url}/api/v2/auth/login", data={"username": os.getenv("TORRENTFLOW_QBITTORRENT_USERNAME", "admin"), "password": os.getenv("TORRENTFLOW_QBITTORRENT_PASSWORD", "")})
        login.raise_for_status()
        if login.text.strip() != "Ok.":
            raise RuntimeError("qBittorrent authentication failed")
        response = await client.request(method, f"{base_url}{path}", data=data)
        response.raise_for_status()
        return response


async def qbit_add(url: str) -> None:
    await qbit_request("/api/v2/torrents/add", method="POST", data={"urls": url})


async def qbit_downloads() -> list[dict[str, object]]:
    response = await qbit_request("/api/v2/torrents/info")
    return response.json()


async def telegram_send(message: str) -> None:
    token = os.getenv("TORRENTFLOW_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TORRENTFLOW_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Telegram is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True})
        response.raise_for_status()
