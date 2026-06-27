from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from aiohttp.test_utils import TestClient, TestServer
import base64
import json
from aiortc import RTCPeerConnection, RTCSessionDescription
from websockets.asyncio.client import connect

from screen_windows.control.clipboard import ClipboardService, RecordingClipboardBackend
from screen_windows.app.config import (
    AppConfig,
    AuthConfig,
    QualityConfig,
    ServerConfig,
    StreamConfig,
    load_config,
)
from screen_windows.control.display import DisplayInfo, DisplayMonitor
from screen_windows.network.filetransfer import FileTransferService
from screen_windows.control.input import RecordingInputExecutor
from screen_windows.app.server import HostServer
from screen_windows.media.video_source import SyntheticFrameSource
from screen_windows.media.webrtc import wait_for_ice_complete


def build_recording_clipboard(text: str = "") -> ClipboardService:
    return ClipboardService(
        backend=RecordingClipboardBackend(text=text),
        backend_name="recording",
    )


def build_file_transfer(tmp_path) -> FileTransferService:
    return FileTransferService(receive_dir=tmp_path, chunk_size=64)


def test_health_endpoint_returns_runtime_info() -> None:
    asyncio.run(_test_health_endpoint_returns_runtime_info())


async def _test_health_endpoint_returns_runtime_info() -> None:
    host = HostServer(AppConfig(), clipboard_service=build_recording_clipboard())
    server = TestServer(host.app)
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get("/api/health")
        payload = await response.json()
        assert response.status == 200
        assert payload["status"] == "ok"
        assert payload["service"] == "screen_windows_host"
        assert payload["discovery"]["method"] == "udp"
        assert payload["stream"]["source"] == host._frame_source.source_name
        assert payload["stream"]["requested_source"] == "auto"
        assert payload["stream"]["display"]["monitors"]
        assert payload["webrtc"]["sessions"] == []
        assert payload["runtime"]["webrtc"] == payload["webrtc"]
        assert payload["runtime"]["quality"] == payload["quality"]
        assert payload["runtime"]["system"]["pid"] == payload["system"]["pid"]
        assert payload["system"]["pid"] > 0
        assert "cpu_percent" in payload["system"]
        assert "memory_rss_mb" in payload["system"]
        assert "encoder" in payload
        assert payload["clipboard"]["enabled"] is True
        assert payload["clipboard"]["backend"] == "recording"
        favicon_response = await client.get("/favicon.ico")
        assert favicon_response.status == 204
    finally:
        await client.close()


def test_closed_webrtc_session_is_removed_from_runtime_stats() -> None:
    asyncio.run(_test_closed_webrtc_session_is_removed_from_runtime_stats())


async def _test_closed_webrtc_session_is_removed_from_runtime_stats() -> None:
    class FakePeerSession:
        stats = {"connection_state": "failed", "video": None}
        closed = False

        async def close_without_notify(self) -> None:
            self.closed = True

    host = HostServer(AppConfig(), clipboard_service=build_recording_clipboard())
    peer_session = FakePeerSession()
    host._peer_sessions.add(peer_session)  # type: ignore[arg-type]
    host._state.active_webrtc_sessions = 1

    host._schedule_peer_session_cleanup(peer_session)  # type: ignore[arg-type]
    await asyncio.sleep(0)
    runtime = host._build_runtime_stats_payload()

    assert peer_session.closed is True
    assert runtime["active_webrtc_sessions"] == 0
    assert runtime["webrtc"]["sessions"] == []


def test_http_file_list_and_download(tmp_path) -> None:
    asyncio.run(_test_http_file_list_and_download(tmp_path))


async def _test_http_file_list_and_download(tmp_path) -> None:
    file_transfer = build_file_transfer(tmp_path)
    (tmp_path / "host-note.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "hidden.txt.part").write_text("partial", encoding="utf-8")
    host = HostServer(
        AppConfig(),
        clipboard_service=build_recording_clipboard(),
        file_transfer_service=file_transfer,
    )
    server = TestServer(host.app)
    client = TestClient(server)
    await client.start_server()
    try:
        unauthorized_list = await client.get("/api/files")
        assert unauthorized_list.status == 401

        unauthorized_download = await client.get("/api/files/host-note.txt")
        assert unauthorized_download.status == 401

        ticket, _ = host._issue_file_access_ticket()
        list_response = await client.get(f"/api/files?ticket={ticket}")
        payload = await list_response.json()
        assert list_response.status == 200
        assert payload == {"files": [{"name": "host-note.txt", "size": 5}]}

        download_response = await client.get(f"/api/files/host-note.txt?ticket={ticket}")
        assert download_response.status == 200
        assert await download_response.text() == "hello"

        missing_response = await client.get(f"/api/files/hidden.txt.part?ticket={ticket}")
        assert missing_response.status == 404
    finally:
        await client.close()


def test_http_file_list_open_when_auth_none(tmp_path) -> None:
    asyncio.run(_test_http_file_list_open_when_auth_none(tmp_path))


async def _test_http_file_list_open_when_auth_none(tmp_path) -> None:
    file_transfer = build_file_transfer(tmp_path)
    (tmp_path / "host-note.txt").write_text("hello", encoding="utf-8")
    host = HostServer(
        AppConfig(auth=AuthConfig(mode="none")),
        clipboard_service=build_recording_clipboard(),
        file_transfer_service=file_transfer,
    )
    server = TestServer(host.app)
    client = TestClient(server)
    await client.start_server()
    try:
        list_response = await client.get("/api/files")
        payload = await list_response.json()
        assert list_response.status == 200
        assert payload == {"files": [{"name": "host-note.txt", "size": 5}]}

        download_response = await client.get("/api/files/host-note.txt")
        assert download_response.status == 200
        assert await download_response.text() == "hello"
    finally:
        await client.close()


def test_websocket_auth_with_pin() -> None:
    asyncio.run(_test_websocket_auth_with_pin())


async def _test_websocket_auth_with_pin() -> None:
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            message = json.loads(await ws.recv())
            assert message["type"] == "auth_ok"
            assert "token" in message
            assert message["display_info"]["monitors"]
            assert message["capabilities"]["clipboard"] is True
    finally:
        await host.shutdown()


def test_websocket_auth_none_allows_control_without_pin() -> None:
    asyncio.run(_test_websocket_auth_none_allows_control_without_pin())


async def _test_websocket_auth_none_allows_control_without_pin() -> None:
    executor = RecordingInputExecutor(display_width=1280, display_height=720)
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
            auth=AuthConfig(mode="none"),
        ),
        input_executor=executor,
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(json.dumps({"type": "auth", "version": "0.1.0"}))
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"
            assert auth_message["token"] == "auth-none"

            await ws.send(
                json.dumps(
                    {
                        "type": "input",
                        "seq": 11,
                        "events": [{"type": "key", "code": "KeyB", "pressed": True}],
                    }
                )
            )
            ack_message = json.loads(await ws.recv())
            assert ack_message["type"] == "input_ack"
            assert ack_message["processed_events"] == 1
            assert len(executor.applied_batches) == 1
    finally:
        await host.shutdown()


def test_websocket_auth_always_rejects_token_reuse() -> None:
    asyncio.run(_test_websocket_auth_always_rejects_token_reuse())


async def _test_websocket_auth_always_rejects_token_reuse() -> None:
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
            auth=AuthConfig(mode="always", pin="123456"),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(json.dumps({"type": "auth", "version": "0.1.0", "pin": "123456"}))
            pin_auth = json.loads(await ws.recv())
            assert pin_auth["type"] == "auth_ok"
            token = pin_auth["token"]

        timestamp = int(datetime.now(UTC).timestamp())
        signature = host.token_manager.build_hmac(token, timestamp)
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "token": token,
                        "timestamp": timestamp,
                        "signature": signature,
                    }
                )
            )
            token_auth = json.loads(await ws.recv())
            assert token_auth == {"type": "auth_error", "reason": "pin required"}

        async with connect(host.websocket_url()) as ws:
            await ws.send(json.dumps({"type": "auth", "version": "0.1.0", "pin": "123456"}))
            second_pin_auth = json.loads(await ws.recv())
            assert second_pin_auth["type"] == "auth_ok"
    finally:
        await host.shutdown()


def test_websocket_auth_token_survives_host_restart(tmp_path) -> None:
    asyncio.run(_test_websocket_auth_token_survives_host_restart(tmp_path))


async def _test_websocket_auth_token_survives_host_restart(tmp_path) -> None:
    store_path = tmp_path / "tokens.json"
    first_host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
            auth=AuthConfig(pin="123456", token_store_path=str(store_path)),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await first_host.start()
    try:
        async with connect(first_host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": "123456",
                    }
                )
            )
            message = json.loads(await ws.recv())
            assert message["type"] == "auth_ok"
            token = message["token"]
    finally:
        await first_host.shutdown()

    second_host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
            auth=AuthConfig(pin="123456", token_store_path=str(store_path)),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await second_host.start()
    try:
        timestamp = int(datetime.now(UTC).timestamp())
        signature = second_host.token_manager.build_hmac(token, timestamp)
        async with connect(second_host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "token": token,
                        "timestamp": timestamp,
                        "signature": signature,
                    }
                )
            )
            message = json.loads(await ws.recv())
            assert message["type"] == "auth_ok"
            assert message["token"] == token
    finally:
        await second_host.shutdown()


def test_websocket_auth_token_survives_default_config_restart(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    config_file = tmp_path / "host_config.toml"
    config_file.write_text(
        """
[server]
bind = "127.0.0.1"
port = 0
http_port = 0

[auth]
pin = "123456"
""".strip(),
        encoding="utf-8",
    )

    asyncio.run(_test_websocket_auth_token_survives_default_config_restart(config_file))


async def _test_websocket_auth_token_survives_default_config_restart(config_file) -> None:
    first_host = HostServer(load_config(config_file), clipboard_service=build_recording_clipboard())
    await first_host.start()
    try:
        async with connect(first_host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": "123456",
                    }
                )
            )
            message = json.loads(await ws.recv())
            assert message["type"] == "auth_ok"
            token = message["token"]
    finally:
        await first_host.shutdown()

    second_host = HostServer(load_config(config_file), clipboard_service=build_recording_clipboard())
    await second_host.start()
    try:
        timestamp = int(datetime.now(UTC).timestamp())
        signature = second_host.token_manager.build_hmac(token, timestamp)
        async with connect(second_host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "token": token,
                        "timestamp": timestamp,
                        "signature": signature,
                    }
                )
            )
            message = json.loads(await ws.recv())
            assert message["type"] == "auth_ok"
            assert message["token"] == token
    finally:
        await second_host.shutdown()


def test_input_batch_is_executed_and_acknowledged() -> None:
    asyncio.run(_test_input_batch_is_executed_and_acknowledged())


async def _test_input_batch_is_executed_and_acknowledged() -> None:
    executor = RecordingInputExecutor(display_width=1280, display_height=720)
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        input_executor=executor,
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"

            await ws.send(
                json.dumps(
                    {
                        "type": "input",
                        "seq": 7,
                        "events": [
                            {"type": "mouse_move", "x": 100, "y": 50},
                            {"type": "key", "code": "KeyA", "pressed": True},
                        ],
                    }
                )
            )
            ack_message = json.loads(await ws.recv())
            assert ack_message["type"] == "input_ack"
            assert ack_message["seq"] == 7
            assert ack_message["processed_events"] == 2
            assert len(executor.applied_batches) == 1
            assert executor.applied_batches[0].events[0].kind == "mouse_move"
    finally:
        await host.shutdown()


def test_websocket_ping_returns_pong() -> None:
    asyncio.run(_test_websocket_ping_returns_pong())


async def _test_websocket_ping_returns_pong() -> None:
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"

            await ws.send(json.dumps({"type": "ping", "t": 123456}))
            pong = json.loads(await ws.recv())
            assert pong["type"] == "pong"
            assert pong["t"] == 123456
            assert pong["server_time"] > 0
    finally:
        await host.shutdown()


def test_websocket_stats_returns_runtime_snapshot() -> None:
    asyncio.run(_test_websocket_stats_returns_runtime_snapshot())


async def _test_websocket_stats_returns_runtime_snapshot() -> None:
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"
            assert auth_message["capabilities"]["stats"] is True

            await ws.send(json.dumps({"type": "stats"}))
            stats_message = json.loads(await ws.recv())
            assert stats_message["type"] == "stats"
            assert stats_message["runtime"]["system"]["pid"] > 0
            assert stats_message["runtime"]["webrtc"]["sessions"] == []
            assert stats_message["runtime"]["quality"]["profile"]["key"] == "standard"
            assert "input" in stats_message["runtime"]
            assert "file_transfer" in stats_message["runtime"]
    finally:
        await host.shutdown()


def test_display_switch_updates_monitor_and_input_size(monkeypatch) -> None:
    asyncio.run(_test_display_switch_updates_monitor_and_input_size(monkeypatch))


async def _test_display_switch_updates_monitor_and_input_size(monkeypatch) -> None:
    import screen_windows.app.server as server_module

    def fake_enumerate_displays(config: StreamConfig) -> DisplayInfo:
        return DisplayInfo(
            selected_monitor=config.monitor,
            source="test",
            reason="ok",
            monitors=[
                DisplayMonitor(id=0, left=0, top=0, width=640, height=360, primary=True),
                DisplayMonitor(id=1, left=640, top=0, width=800, height=450),
            ],
        )

    def fake_build_frame_source(config: StreamConfig) -> SyntheticFrameSource:
        if config.monitor == 1:
            return SyntheticFrameSource(width=800, height=450, fps=config.fps)
        return SyntheticFrameSource(width=640, height=360, fps=config.fps)

    monkeypatch.setattr(server_module, "enumerate_displays", fake_enumerate_displays)
    monkeypatch.setattr(server_module, "build_frame_source", fake_build_frame_source)
    executor = RecordingInputExecutor(display_width=640, display_height=360)
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        input_executor=executor,
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"

            await ws.send(json.dumps({"type": "display_switch", "monitor": 1}))
            display_message = json.loads(await ws.recv())

            assert display_message["type"] == "display_state"
            assert display_message["display"]["selected_monitor"] == 1
            assert display_message["stream"]["monitor"] == 1
            assert executor.display_width == 800
            assert executor.display_height == 450
            assert executor.display_left == 640
            assert executor.display_top == 0
            assert executor.virtual_left == 0
            assert executor.virtual_top == 0
            assert executor.virtual_width == 1440
            assert executor.virtual_height == 450
    finally:
        await host.shutdown()


def test_clipboard_read_and_write_are_acknowledged() -> None:
    asyncio.run(_test_clipboard_read_and_write_are_acknowledged())


async def _test_clipboard_read_and_write_are_acknowledged() -> None:
    clipboard = build_recording_clipboard("host text")
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=clipboard,
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"

            await ws.send(json.dumps({"type": "clipboard_read"}))
            read_message = json.loads(await ws.recv())
            assert read_message == {
                "type": "clipboard_text",
                "mime": "text/plain",
                "source": "host",
                "text": "host text",
            }

            await ws.send(
                json.dumps(
                    {
                        "type": "clipboard_write",
                        "mime": "text/plain",
                        "text": "viewer text",
                    }
                )
            )
            write_message = json.loads(await ws.recv())
            assert write_message == {
                "type": "clipboard_ack",
                "mime": "text/plain",
                "text_length": len("viewer text"),
            }
            assert clipboard.read_count == 1
            assert clipboard.write_count == 1
            assert clipboard.backend.text == "viewer text"
    finally:
        await host.shutdown()


def test_file_upload_chunks_are_written_and_acknowledged(tmp_path) -> None:
    asyncio.run(_test_file_upload_chunks_are_written_and_acknowledged(tmp_path))


async def _test_file_upload_chunks_are_written_and_acknowledged(tmp_path) -> None:
    file_transfer = build_file_transfer(tmp_path)
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=build_recording_clipboard(),
        file_transfer_service=file_transfer,
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"
            assert auth_message["capabilities"]["file_transfer"] is True
            assert auth_message["file_transfer"] == {
                "chunk_size": file_transfer.chunk_size,
                "max_file_size": file_transfer.max_file_size,
            }

            await ws.send(
                json.dumps(
                    {
                        "type": "file_req",
                        "id": "file-1",
                        "action": "send",
                        "name": "../note.txt",
                        "size": 11,
                    }
                )
            )
            ready = json.loads(await ws.recv())
            assert ready == {"type": "file_ready", "id": "file-1", "offset": 0}

            await ws.send(
                json.dumps(
                    {
                        "type": "file_chunk",
                        "id": "file-1",
                        "offset": 0,
                        "data": base64.b64encode(b"hello ").decode("ascii"),
                    }
                )
            )
            first_ack = json.loads(await ws.recv())
            assert first_ack == {"type": "file_chunk_ack", "id": "file-1", "offset": 6}

            await ws.send(
                json.dumps(
                    {
                        "type": "file_chunk",
                        "id": "file-1",
                        "offset": 6,
                        "data": base64.b64encode(b"world").decode("ascii"),
                    }
                )
            )
            second_ack = json.loads(await ws.recv())
            assert second_ack == {"type": "file_chunk_ack", "id": "file-1", "offset": 11}

            await ws.send(
                json.dumps(
                    {
                        "type": "file_req",
                        "id": "file-1",
                        "action": "complete",
                    }
                )
            )
            complete = json.loads(await ws.recv())
            assert complete["type"] == "file_complete"
            assert complete["name"] == "note.txt"
            assert complete["size"] == 11
            assert (tmp_path / "note.txt").read_bytes() == b"hello world"
            assert file_transfer.completed_files == 1
    finally:
        await host.shutdown()


def test_file_upload_zero_byte_file_completes_without_chunks(tmp_path) -> None:
    asyncio.run(_test_file_upload_zero_byte_file_completes_without_chunks(tmp_path))


async def _test_file_upload_zero_byte_file_completes_without_chunks(tmp_path) -> None:
    file_transfer = build_file_transfer(tmp_path)
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=build_recording_clipboard(),
        file_transfer_service=file_transfer,
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"

            await ws.send(
                json.dumps(
                    {
                        "type": "file_req",
                        "id": "empty-file",
                        "action": "send",
                        "name": "empty.txt",
                        "size": 0,
                    }
                )
            )
            ready = json.loads(await ws.recv())
            assert ready == {"type": "file_ready", "id": "empty-file", "offset": 0}

            await ws.send(
                json.dumps(
                    {
                        "type": "file_req",
                        "id": "empty-file",
                        "action": "complete",
                    }
                )
            )
            complete = json.loads(await ws.recv())
            assert complete["type"] == "file_complete"
            assert complete["name"] == "empty.txt"
            assert complete["size"] == 0
            assert (tmp_path / "empty.txt").read_bytes() == b""
            assert not list(tmp_path.glob("*.part"))
    finally:
        await host.shutdown()


def test_file_upload_partial_is_canceled_on_disconnect(tmp_path) -> None:
    asyncio.run(_test_file_upload_partial_is_canceled_on_disconnect(tmp_path))


async def _test_file_upload_partial_is_canceled_on_disconnect(tmp_path) -> None:
    file_transfer = build_file_transfer(tmp_path)
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=build_recording_clipboard(),
        file_transfer_service=file_transfer,
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"

            await ws.send(
                json.dumps(
                    {
                        "type": "file_req",
                        "id": "file-cancel",
                        "action": "send",
                        "name": "cancel.txt",
                        "size": 5,
                    }
                )
            )
            ready = json.loads(await ws.recv())
            assert ready["type"] == "file_ready"

            await ws.send(
                json.dumps(
                    {
                        "type": "file_chunk",
                        "id": "file-cancel",
                        "offset": 0,
                        "data": base64.b64encode(b"abc").decode("ascii"),
                    }
                )
            )
            ack = json.loads(await ws.recv())
            assert ack["type"] == "file_chunk_ack"
            assert file_transfer.active_count == 1

        await asyncio.sleep(0.05)
        assert file_transfer.active_count == 0
        assert file_transfer.canceled_files == 1
        assert not list(tmp_path.glob("*.part"))
    finally:
        await host.shutdown()


def test_quality_state_can_be_read_and_locked() -> None:
    asyncio.run(_test_quality_state_can_be_read_and_locked())


async def _test_quality_state_can_be_read_and_locked() -> None:
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
            quality=QualityConfig(mode="auto", profile="standard"),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"
            assert auth_message["capabilities"]["quality"] is True

            await ws.send(json.dumps({"type": "quality", "action": "state"}))
            state_message = json.loads(await ws.recv())
            assert state_message["type"] == "quality_state"
            assert state_message["quality"]["profile"]["key"] == "standard"

            await ws.send(
                json.dumps(
                    {
                        "type": "quality",
                        "mode": "manual",
                        "profile": "fast",
                    }
                )
            )
            locked_message = json.loads(await ws.recv())
            assert locked_message["type"] == "quality_state"
            assert locked_message["quality"]["mode"] == "manual"
            assert locked_message["quality"]["locked"] is True
            assert locked_message["quality"]["profile"]["key"] == "fast"

            await ws.send(
                json.dumps(
                    {
                        "type": "quality",
                        "mode": "manual",
                        "profile": "standard",
                        "width": 1600,
                        "height": 900,
                        "fps": 45,
                        "bitrate_mbps": 7.5,
                    }
                )
            )
            custom_message = json.loads(await ws.recv())
            assert custom_message["type"] == "quality_state"
            assert custom_message["quality"]["profile"]["key"] == "custom"
            assert custom_message["quality"]["profile"]["width"] == 1600
            assert custom_message["quality"]["profile"]["height"] == 900
            assert custom_message["quality"]["profile"]["fps"] == 45
            assert custom_message["quality"]["profile"]["bitrate_mbps"] == 7.5

            await ws.send(
                json.dumps(
                    {
                        "type": "quality",
                        "action": "signals",
                        "signals": {
                            "rtt_ms": 90,
                            "packet_loss": 8,
                            "bandwidth_mbps": 0.2,
                        },
                    }
                )
            )
            signal_message = json.loads(await ws.recv())
            assert signal_message["type"] == "quality_state"
            assert signal_message["quality"]["mode"] == "manual"
            assert signal_message["quality"]["profile"]["key"] == "custom"
            assert signal_message["quality"]["last_signal"]["rtt_ms"] == 90.0
    finally:
        await host.shutdown()


def test_webrtc_offer_answer_streams_video() -> None:
    asyncio.run(_test_webrtc_offer_answer_streams_video())


async def _test_webrtc_offer_answer_streams_video() -> None:
    host = HostServer(
        AppConfig(
            server=ServerConfig(bind="127.0.0.1", port=0, http_port=0),
        ),
        clipboard_service=build_recording_clipboard(),
    )
    await host.start()
    client_pc = RTCPeerConnection()
    remote_track_ready = asyncio.Event()
    received_track = None

    @client_pc.on("track")
    def on_track(track) -> None:
        nonlocal received_track
        received_track = track
        remote_track_ready.set()

    try:
        async with connect(host.websocket_url()) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "version": "0.1.0",
                        "pin": host.token_manager.pin,
                    }
                )
            )
            auth_message = json.loads(await ws.recv())
            assert auth_message["type"] == "auth_ok"

            client_pc.addTransceiver("video", direction="recvonly")
            offer = await client_pc.createOffer()
            await client_pc.setLocalDescription(offer)
            await wait_for_ice_complete(client_pc)

            assert client_pc.localDescription is not None
            await ws.send(
                json.dumps(
                    {
                        "type": "webrtc_offer",
                        "description_type": client_pc.localDescription.type,
                        "sdp": client_pc.localDescription.sdp,
                    }
                )
            )
            answer_message = json.loads(await ws.recv())
            assert answer_message["type"] == "webrtc_answer"

            await client_pc.setRemoteDescription(
                RTCSessionDescription(
                    sdp=answer_message["sdp"],
                    type=answer_message["description_type"],
                )
            )

            await asyncio.wait_for(remote_track_ready.wait(), timeout=10)
            assert received_track is not None
            frame = await asyncio.wait_for(received_track.recv(), timeout=10)
            assert frame.width == host._config.stream.width
            assert frame.height == host._config.stream.height
    finally:
        await client_pc.close()
        await host.shutdown()
