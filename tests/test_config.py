from __future__ import annotations

from pathlib import Path

from screen_windows.config import apply_overrides, load_config


def test_load_config_defaults_when_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.toml")

    assert config.server.port == 8765
    assert config.server.http_port == 8766
    assert config.discovery.udp_port == 9876
    assert config.stream.source == "auto"
    assert config.stream.width == 1280
    assert config.stream.height == 720
    assert config.stream.fps == 24
    assert config.stream.monitor == 0
    assert config.encoder.backend == "auto"
    assert config.encoder.codec == "h264"
    assert config.encoder.bitrate == "10M"
    assert config.encoder.preset == "p1"
    assert config.auth.token_store_path == ""
    assert config.quality.mode == "auto"
    assert config.quality.profile == "standard"


def test_load_and_override_config(tmp_path: Path) -> None:
    config_file = tmp_path / "host_config.toml"
    config_file.write_text(
        """
[server]
bind = "127.0.0.1"
port = 9001
http_port = 9002

[auth]
mode = "always"
pin = "222333"
token_store_path = "D:/tmp/screen-token.json"

[discovery]
method = "both"
udp_port = 10086

[stream]
source = "mss"
width = 854
height = 480
fps = 30
monitor = 1

[encoder]
ffmpeg_path = "C:/ffmpeg/bin/ffmpeg.exe"
backend = "libx264"
codec = "h264"
bitrate = "6M"
preset = "p1"

[file_transfer]
receive_dir = "D:/tmp/screen-files"
max_file_size = 1024
chunk_size = 128

[quality]
mode = "manual"
profile = "fast"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_file)
    overridden = apply_overrides(
        config,
        host_override="0.0.0.0",
        port_override=9101,
        http_port_override=9102,
    )

    assert config.server.bind == "127.0.0.1"
    assert overridden.server.bind == "0.0.0.0"
    assert overridden.server.port == 9101
    assert overridden.server.http_port == 9102
    assert config.auth.pin == "222333"
    assert config.auth.token_store_path == "D:/tmp/screen-token.json"
    assert config.discovery.method == "both"
    assert config.stream.width == 854
    assert config.stream.height == 480
    assert config.stream.fps == 30
    assert config.stream.source == "mss"
    assert config.stream.monitor == 1
    assert config.encoder.ffmpeg_path == "C:/ffmpeg/bin/ffmpeg.exe"
    assert config.encoder.backend == "libx264"
    assert config.encoder.bitrate == "6M"
    assert config.file_transfer.receive_dir == "D:/tmp/screen-files"
    assert config.file_transfer.max_file_size == 1024
    assert config.file_transfer.chunk_size == 128
    assert config.quality.mode == "manual"
    assert config.quality.profile == "fast"
