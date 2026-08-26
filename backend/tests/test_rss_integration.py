import asyncio
from contextlib import asynccontextmanager, contextmanager
import socket
import socketserver
import struct
import time
from threading import Thread
from typing import AsyncIterator, Iterator

from app.rss import fetch_entries


RSS_BODY = b'''<?xml version="1.0"?><rss xmlns:torrent="https://torrentleech.example/rss" version="2.0"><channel><item><guid>release-1</guid><title>Trusted release</title><link>https://tracker.example/download/1</link><torrent:seeds>17</torrent:seeds><torrent:uploader>Trusted</torrent:uploader><torrent:freeleech>yes</torrent:freeleech><torrent:doubleupload>1</torrent:doubleupload><torrent:size>1.5 GB</torrent:size></item></channel></rss>'''


@asynccontextmanager
async def local_rss_server() -> AsyncIterator[tuple[str, list[str]]]:
    received_cookies: list[str] = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        request = await reader.readuntil(b"\r\n\r\n")
        received_cookies.append(next((line[7:].decode("latin-1").strip() for line in request.split(b"\r\n") if line.lower().startswith(b"cookie: ")), ""))
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/rss+xml\r\nContent-Length: " + str(len(RSS_BODY)).encode() + b"\r\nConnection: close\r\n\r\n" + RSS_BODY)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}/rss", received_cookies
    finally:
        server.close()
        await server.wait_closed()


def _receive_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("SOCKS peer closed during handshake")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class Socks5Handler(socketserver.BaseRequestHandler):
    """Tiny CONNECT-only SOCKS5 proxy used to exercise the real socks transport."""

    def handle(self) -> None:
        client: socket.socket = self.request
        version, method_count = _receive_exact(client, 2)
        assert version == 5
        _receive_exact(client, method_count)
        client.sendall(b"\x05\x00")
        version, command, _, address_type = _receive_exact(client, 4)
        assert version == 5 and command == 1
        if address_type == 1:
            host = socket.inet_ntoa(_receive_exact(client, 4))
        elif address_type == 3:
            host = _receive_exact(client, _receive_exact(client, 1)[0]).decode("idna")
        else:
            raise AssertionError(f"Unsupported SOCKS address type {address_type}")
        _ = struct.unpack("!H", _receive_exact(client, 2))[0]
        # This is a real SOCKS5 CONNECT handshake, followed by a deterministic
        # HTTP origin fixture. It avoids a second local TCP relay, which is
        # flaky on Windows yet still proves that httpx used SOCKS transport.
        assert host == "127.0.0.1"
        client.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        request = b""
        while b"\r\n\r\n" not in request:
            request += client.recv(4096)
        assert request.startswith(b"GET /rss HTTP/")
        client.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/rss+xml\r\nContent-Length: " + str(len(RSS_BODY)).encode() + b"\r\nConnection: close\r\n\r\n" + RSS_BODY)
        # Give the asynchronous client a scheduling turn before socketserver
        # closes the connection on Windows.
        time.sleep(0.05)


class Socks5Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@contextmanager
def local_socks5_server() -> Iterator[str]:
    server = Socks5Server(("127.0.0.1", 0), Socks5Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"socks5://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_torrentleech_adapter_fetches_local_http_rss_and_uses_encrypted_cookie_shape() -> None:
    async def scenario() -> tuple[list[dict[str, str | int | bool]], list[str]]:
        async with local_rss_server() as (url, received_cookies):
            return await fetch_entries(url, adapter_type="torrentleech", cookie="tracker_session=opaque"), received_cookies

    entries, received_cookies = asyncio.run(scenario())

    assert received_cookies == ["tracker_session=opaque"]
    assert entries == [{"external_id": "release-1", "title": "Trusted release", "link": "https://tracker.example/download/1", "seeds": 17, "uploader": "Trusted", "freeleech": True, "double_upload": True, "size_bytes": 1610612736}]


def test_adapter_fetches_through_a_real_local_socks5_proxy() -> None:
    async def scenario() -> list[dict[str, str | int | bool]]:
        with local_socks5_server() as proxy_url:
            return await fetch_entries("http://127.0.0.1:18080/rss", adapter_type="torrentleech", proxy_url=proxy_url)

    entries = asyncio.run(scenario())

    assert entries[0]["external_id"] == "release-1"
