from __future__ import annotations

import asyncio
from pathlib import Path

from screen_windows.app.config import AppConfig
from screen_windows.app.launcher import (
    LauncherState,
    build_config_from_launcher_payload,
)


def test_launcher_payload_builds_host_config() -> None:
    config = build_config_from_launcher_payload(
        {
            "bind": "0.0.0.0",
            "http_port": "9002",
            "ws_port": "9001",
            "auth_mode": "always",
            "pin": "123456",
            "discovery_method": "none",
            "resolution": "1920x1080",
            "fps": "30",
            "source": "mss",
            "monitor": "1",
            "encoder_backend": "libx264",
            "bitrate_mbps": "8",
            "quality_mode": "manual",
            "quality_profile": "fast",
            "receive_dir": "D:/tmp/screen-files",
            "max_file_size_mb": "128",
        },
        AppConfig(),
    )

    assert config.server.bind == "0.0.0.0"
    assert config.server.http_port == 9002
    assert config.server.port == 9001
    assert config.auth.mode == "always"
    assert config.auth.pin == "123456"
    assert config.discovery.method == "none"
    assert config.stream.width == 1920
    assert config.stream.height == 1080
    assert config.stream.fps == 30
    assert config.stream.source == "mss"
    assert config.stream.monitor == 1
    assert config.encoder.backend == "libx264"
    assert config.encoder.bitrate == "8M"
    assert config.quality.mode == "manual"
    assert config.quality.profile == "fast"
    assert config.file_transfer.receive_dir == "D:/tmp/screen-files"
    assert config.file_transfer.max_file_size == 128 * 1024 * 1024


def test_launcher_payload_rejects_same_http_and_ws_port() -> None:
    try:
        build_config_from_launcher_payload(
            {"http_port": "8766", "ws_port": "8766"},
            AppConfig(),
        )
    except ValueError as exc:
        assert "must be different" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_launcher_state_starts_and_stops_host(tmp_path: Path) -> None:
    asyncio.run(_test_launcher_state_starts_and_stops_host(tmp_path))


async def _test_launcher_state_starts_and_stops_host(tmp_path: Path) -> None:
    created: list[FakeHostServer] = []

    def host_factory(config: AppConfig) -> "FakeHostServer":
        host = FakeHostServer(config)
        created.append(host)
        return host

    state = LauncherState(config_path=str(tmp_path / "missing.toml"), host_factory=host_factory)

    started = await state.start_host(
        {
            "bind": "127.0.0.1",
            "http_port": "8766",
            "ws_port": "8765",
            "pin": "654321",
        }
    )

    assert started.running is True
    assert started.local_url == "http://127.0.0.1:8766"
    assert started.pin == "654321"
    assert created[0].started is True

    stopped = await state.stop_host()

    assert stopped.running is False
    assert created[0].stopped is True


class FakeTokenManager:
    def __init__(self, pin: str) -> None:
        self.pin = pin or "111222"


class FakeHostServer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.token_manager = FakeTokenManager(config.auth.pin)
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        # 启动页只需要 HostServer 的生命周期和 URL 合约。
        self.started = True

    async def shutdown(self) -> None:
        self.stopped = True

    def http_url(self) -> str:
        return f"http://{self.config.server.bind}:{self.config.server.http_port}"

    def websocket_url(self) -> str:
        return f"ws://{self.config.server.bind}:{self.config.server.port}"
