from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
import tomllib


DEFAULT_CONFIG_PATH = Path("host_config.toml")
APP_DIR_NAME = "screen_windows"
TOKEN_STORE_FILE_NAME = "tokens.json"
RECEIVE_DIR_NAME = "received_files"


@dataclass(frozen=True, slots=True)
class ServerConfig:
    bind: str = "0.0.0.0"
    port: int = 8765
    http_port: int = 8766


@dataclass(frozen=True, slots=True)
class AuthConfig:
    mode: str = "pin_once"
    pin: str = ""
    token_ttl_seconds: int = 3600
    token_store_path: str = ""


@dataclass(frozen=True, slots=True)
class DiscoveryConfig:
    method: str = "udp"
    udp_port: int = 9876
    announce_interval_seconds: float = 2.0


@dataclass(frozen=True, slots=True)
class StreamConfig:
    source: str = "auto"
    width: int = 1280
    height: int = 720
    fps: int = 24
    monitor: int = 0


@dataclass(frozen=True, slots=True)
class EncoderConfig:
    ffmpeg_path: str = ""
    backend: str = "auto"
    codec: str = "h264"
    bitrate: str = "10M"
    preset: str = "p1"


@dataclass(frozen=True, slots=True)
class FileTransferConfig:
    receive_dir: str = RECEIVE_DIR_NAME
    max_file_size: int = 512 * 1024 * 1024
    chunk_size: int = 64 * 1024


@dataclass(frozen=True, slots=True)
class QualityConfig:
    mode: str = "manual"
    profile: str = "eco"


@dataclass(frozen=True, slots=True)
class AppConfig:
    server: ServerConfig = ServerConfig()
    auth: AuthConfig = AuthConfig()
    discovery: DiscoveryConfig = DiscoveryConfig()
    stream: StreamConfig = StreamConfig()
    encoder: EncoderConfig = EncoderConfig()
    file_transfer: FileTransferConfig = FileTransferConfig()
    quality: QualityConfig = QualityConfig()


def default_token_store_path() -> str:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return str(Path(appdata) / APP_DIR_NAME / TOKEN_STORE_FILE_NAME)
    return str(Path.home() / f".{APP_DIR_NAME}" / TOKEN_STORE_FILE_NAME)


def default_receive_dir_path() -> str:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return str(Path(appdata) / APP_DIR_NAME / RECEIVE_DIR_NAME)
    return str(Path.home() / f".{APP_DIR_NAME}" / RECEIVE_DIR_NAME)


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return AppConfig(
            auth=AuthConfig(token_store_path=default_token_store_path()),
            file_transfer=FileTransferConfig(receive_dir=default_receive_dir_path()),
        )

    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    server_raw = raw.get("server", {})
    auth_raw = raw.get("auth", {})
    discovery_raw = raw.get("discovery", {})
    stream_raw = raw.get("stream", {})
    encoder_raw = raw.get("encoder", {})
    file_transfer_raw = raw.get("file_transfer", {})
    quality_raw = raw.get("quality", {})

    return AppConfig(
        server=ServerConfig(
            bind=server_raw.get("bind", "0.0.0.0"),
            port=int(server_raw.get("port", 8765)),
            http_port=int(server_raw.get("http_port", 8766)),
        ),
        auth=AuthConfig(
            mode=auth_raw.get("mode", "pin_once"),
            pin=str(auth_raw.get("pin", "")),
            token_ttl_seconds=int(auth_raw.get("token_ttl_seconds", 3600)),
            token_store_path=str(
                auth_raw.get("token_store_path") or default_token_store_path()
            ),
        ),
        discovery=DiscoveryConfig(
            method=discovery_raw.get("method", "udp"),
            udp_port=int(discovery_raw.get("udp_port", 9876)),
            announce_interval_seconds=float(
                discovery_raw.get("announce_interval_seconds", 2.0)
            ),
        ),
        stream=StreamConfig(
            source=stream_raw.get("source", "auto"),
            width=int(stream_raw.get("width", 1280)),
            height=int(stream_raw.get("height", 720)),
            fps=int(stream_raw.get("fps", 24)),
            monitor=int(stream_raw.get("monitor", 0)),
        ),
        encoder=EncoderConfig(
            ffmpeg_path=str(encoder_raw.get("ffmpeg_path", "")),
            backend=str(encoder_raw.get("backend", "auto")),
            codec=str(encoder_raw.get("codec", "h264")),
            bitrate=str(encoder_raw.get("bitrate", "10M")),
            preset=str(encoder_raw.get("preset", "p1")),
        ),
        file_transfer=FileTransferConfig(
            receive_dir=str(
                file_transfer_raw.get("receive_dir") or default_receive_dir_path()
            ),
            max_file_size=int(file_transfer_raw.get("max_file_size", 512 * 1024 * 1024)),
            chunk_size=int(file_transfer_raw.get("chunk_size", 64 * 1024)),
        ),
        quality=QualityConfig(
            mode=str(quality_raw.get("mode", "manual")),
            profile=str(quality_raw.get("profile", "eco")),
        ),
    )


def apply_overrides(
    config: AppConfig,
    *,
    host_override: str | None = None,
    port_override: int | None = None,
    http_port_override: int | None = None,
) -> AppConfig:
    server = config.server
    if host_override is not None:
        server = replace(server, bind=host_override)
    if port_override is not None:
        server = replace(server, port=port_override)
    if http_port_override is not None:
        server = replace(server, http_port=http_port_override)
    return replace(config, server=server)
