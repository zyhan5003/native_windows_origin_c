from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
import asyncio
import socket
from typing import Any, Callable
import webbrowser

from aiohttp import web

from .config import (
    AppConfig,
    EncoderConfig,
    FileTransferConfig,
    QualityConfig,
    ServerConfig,
    StreamConfig,
    load_config,
)
from .process_guard import release_stale_host_processes_for_ports
from .server import HostServer
from ..web.webui import LAUNCHER_HTML


LAUNCHER_DEFAULT_HOST = "127.0.0.1"
LAUNCHER_DEFAULT_PORT = 8770

AUTH_MODES = {"pin_once", "always", "none"}
DISCOVERY_METHODS = {"udp", "mdns", "both", "none"}
STREAM_SOURCES = {"auto", "dxcam", "mss", "synthetic"}
ENCODER_BACKENDS = {"auto", "nvenc", "amf", "qsv", "libx264"}
QUALITY_MODES = {"auto", "manual"}
QUALITY_PROFILES = {"limit", "eco", "standard", "fast", "turbo"}


@dataclass(frozen=True, slots=True)
class HostLaunchStatus:
    running: bool
    started_at: str | None
    local_url: str | None
    access_url: str | None
    websocket_url: str | None
    pin: str | None
    config: dict[str, Any] | None


class LauncherState:
    def __init__(
        self,
        *,
        config_path: str | None,
        host_factory: Callable[[AppConfig], HostServer] = HostServer,
    ) -> None:
        self._config_path = config_path
        self._host_factory = host_factory
        self._host: HostServer | None = None
        self._config: AppConfig | None = None
        self._started_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def start_host(self, payload: dict[str, Any]) -> HostLaunchStatus:
        async with self._lock:
            if self._host is not None:
                old_host = self._host
                self._host = None
                self._config = None
                self._started_at = None
                await old_host.shutdown()

            base_config = load_config(self._config_path)
            config = build_config_from_launcher_payload(payload, base_config)
            release_stale_host_processes_for_ports(
                (config.server.port, config.server.http_port)
            )
            host = self._host_factory(config)
            try:
                await host.start()
            except Exception:
                await host.shutdown()
                raise

            self._host = host
            self._config = config
            self._started_at = datetime.now(UTC)
            return self.status()

    async def stop_host(self) -> HostLaunchStatus:
        async with self._lock:
            host = self._host
            self._host = None
            self._started_at = None
            if host is not None:
                await host.shutdown()
            return self.status()

    def status(self) -> HostLaunchStatus:
        if self._host is None or self._config is None:
            return HostLaunchStatus(
                running=False,
                started_at=None,
                local_url=None,
                access_url=None,
                websocket_url=None,
                pin=None,
                config=None,
            )

        return HostLaunchStatus(
            running=True,
            started_at=self._started_at.isoformat() if self._started_at else None,
            local_url=_local_http_url(self._host.http_url(), self._config.server.bind),
            access_url=_access_http_url(self._host.http_url(), self._config.server.bind),
            websocket_url=self._host.websocket_url(),
            pin=self._host.token_manager.pin,
            config=_config_payload(self._config),
        )

    def defaults(self) -> dict[str, Any]:
        return _config_payload(load_config(self._config_path))


def build_launcher_app(state: LauncherState) -> web.Application:
    app = web.Application()
    app["launcher_state"] = state
    app.router.add_get("/", _handle_index)
    app.router.add_get("/api/defaults", _handle_defaults)
    app.router.add_get("/api/status", _handle_status)
    app.router.add_post("/api/start", _handle_start)
    app.router.add_post("/api/stop", _handle_stop)
    app.router.add_get("/favicon.ico", _handle_favicon)
    return app


async def _handle_index(request: web.Request) -> web.Response:
    return web.Response(text=LAUNCHER_HTML, content_type="text/html")


async def _handle_defaults(request: web.Request) -> web.Response:
    state = _request_state(request)
    return web.json_response(state.defaults())


async def _handle_status(request: web.Request) -> web.Response:
    state = _request_state(request)
    return web.json_response(_status_payload(state.status()))


async def _handle_start(request: web.Request) -> web.Response:
    state = _request_state(request)
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        status = await state.start_host(payload)
    except RuntimeError as exc:
        return web.json_response({"error": str(exc)}, status=409)
    except (TypeError, ValueError) as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception as exc:
        return web.json_response({"error": f"failed to start host: {exc}"}, status=500)
    return web.json_response(_status_payload(status))


async def _handle_stop(request: web.Request) -> web.Response:
    state = _request_state(request)
    status = await state.stop_host()
    return web.json_response(_status_payload(status))


async def _handle_favicon(request: web.Request) -> web.Response:
    return web.Response(status=204)


def _request_state(request: web.Request) -> LauncherState:
    return request.app["launcher_state"]


def build_config_from_launcher_payload(
    payload: dict[str, Any],
    base_config: AppConfig,
) -> AppConfig:
    width, height = _resolution_from_payload(payload, base_config.stream)
    bitrate = _bitrate_from_payload(payload, base_config.encoder.bitrate)
    max_file_size_mb = _int_field(
        payload,
        "max_file_size_mb",
        max(1, base_config.file_transfer.max_file_size // (1024 * 1024)),
        1,
        4096,
    )

    server = ServerConfig(
        bind=_string_field(payload, "bind", base_config.server.bind).strip(),
        port=_int_field(payload, "ws_port", base_config.server.port, 1, 65535),
        http_port=_int_field(payload, "http_port", base_config.server.http_port, 1, 65535),
    )
    if not server.bind:
        raise ValueError("bind is required")
    if server.port == server.http_port:
        raise ValueError("HTTP port and WebSocket port must be different")

    auth_mode = _choice_field(payload, "auth_mode", base_config.auth.mode, AUTH_MODES)
    pin = _pin_from_payload(payload, base_config.auth.pin)
    auth = replace(base_config.auth, mode=auth_mode, pin=pin)

    discovery = replace(
        base_config.discovery,
        method=_choice_field(
            payload,
            "discovery_method",
            base_config.discovery.method,
            DISCOVERY_METHODS,
        ),
        udp_port=_int_field(payload, "udp_port", base_config.discovery.udp_port, 1, 65535),
    )

    stream = StreamConfig(
        source=_choice_field(payload, "source", base_config.stream.source, STREAM_SOURCES),
        width=width,
        height=height,
        fps=_int_field(payload, "fps", base_config.stream.fps, 5, 120),
        monitor=_int_field(payload, "monitor", base_config.stream.monitor, 0, 32),
    )

    encoder = EncoderConfig(
        ffmpeg_path=_string_field(payload, "ffmpeg_path", base_config.encoder.ffmpeg_path),
        backend=_choice_field(
            payload,
            "encoder_backend",
            base_config.encoder.backend,
            ENCODER_BACKENDS,
        ),
        codec=base_config.encoder.codec,
        bitrate=bitrate,
        preset=_string_field(payload, "encoder_preset", base_config.encoder.preset),
    )

    receive_dir = _string_field(
        payload,
        "receive_dir",
        base_config.file_transfer.receive_dir,
    ).strip()
    file_transfer = FileTransferConfig(
        receive_dir=receive_dir or base_config.file_transfer.receive_dir,
        max_file_size=max_file_size_mb * 1024 * 1024,
        chunk_size=base_config.file_transfer.chunk_size,
    )

    quality = QualityConfig(
        mode=_choice_field(payload, "quality_mode", base_config.quality.mode, QUALITY_MODES),
        profile=_choice_field(
            payload,
            "quality_profile",
            base_config.quality.profile,
            QUALITY_PROFILES,
        ),
    )

    return AppConfig(
        server=server,
        auth=auth,
        discovery=discovery,
        stream=stream,
        encoder=encoder,
        file_transfer=file_transfer,
        quality=quality,
    )


async def _run_launcher_async(
    *,
    host: str,
    port: int,
    config_path: str | None,
    open_browser: bool,
) -> None:
    state = LauncherState(config_path=config_path)
    app = build_launcher_app(state)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    url = f"http://{host}:{port}"
    print(f"screen_windows launcher started: {url}")
    if open_browser:
        # 启动页是给非命令行用户使用的，本地浏览器自动打开能少一步心智负担。
        webbrowser.open(url)

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        await state.stop_host()
        await runner.cleanup()


def run_launcher(
    *,
    host: str = LAUNCHER_DEFAULT_HOST,
    port: int = LAUNCHER_DEFAULT_PORT,
    config_path: str | None = None,
    open_browser: bool = True,
) -> int:
    try:
        asyncio.run(
            _run_launcher_async(
                host=host,
                port=port,
                config_path=config_path,
                open_browser=open_browser,
            )
        )
    except KeyboardInterrupt:
        print("screen_windows launcher stopped")
        return 0
    return 0


def _status_payload(status: HostLaunchStatus) -> dict[str, Any]:
    return asdict(status)


def _config_payload(config: AppConfig) -> dict[str, Any]:
    return {
        "server": asdict(config.server),
        "auth": {
            **asdict(config.auth),
            "pin": config.auth.pin,
        },
        "discovery": asdict(config.discovery),
        "stream": asdict(config.stream),
        "encoder": asdict(config.encoder),
        "file_transfer": {
            **asdict(config.file_transfer),
            "max_file_size_mb": max(
                1,
                config.file_transfer.max_file_size // (1024 * 1024),
            ),
        },
        "quality": asdict(config.quality),
    }


def _resolution_from_payload(
    payload: dict[str, Any],
    base_stream: StreamConfig,
) -> tuple[int, int]:
    resolution = _string_field(payload, "resolution", "").strip().lower()
    if resolution and resolution != "custom":
        parts = resolution.replace("*", "x").split("x", maxsplit=1)
        if len(parts) != 2:
            raise ValueError("resolution must look like 1920x1080")
        width_raw, height_raw = parts
        width = _bounded_int(width_raw, "width", 320, 3840)
        height = _bounded_int(height_raw, "height", 180, 2160)
        return width, height

    return (
        _int_field(payload, "width", base_stream.width, 320, 3840),
        _int_field(payload, "height", base_stream.height, 180, 2160),
    )


def _bitrate_from_payload(payload: dict[str, Any], default: str) -> str:
    raw = _string_field(payload, "bitrate_mbps", default).strip().upper()
    if raw.endswith("M"):
        number = raw[:-1]
    else:
        number = raw
    value = _bounded_float(number, "bitrate_mbps", 0.1, 100.0)
    return f"{value:g}M"


def _pin_from_payload(payload: dict[str, Any], default: str) -> str:
    pin = _string_field(payload, "pin", default).strip()
    if not pin:
        return ""
    if not pin.isdigit():
        raise ValueError("PIN must contain digits only")
    if len(pin) < 4 or len(pin) > 12:
        raise ValueError("PIN length must be between 4 and 12")
    return pin


def _choice_field(
    payload: dict[str, Any],
    field_name: str,
    default: str,
    allowed: set[str],
) -> str:
    value = _string_field(payload, field_name, default).strip().lower()
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return value


def _int_field(
    payload: dict[str, Any],
    field_name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    return _bounded_int(payload.get(field_name, default), field_name, minimum, maximum)


def _string_field(payload: dict[str, Any], field_name: str, default: str) -> str:
    value = payload.get(field_name, default)
    if value is None:
        return default
    return str(value)


def _bounded_int(value: Any, field_name: str, minimum: int, maximum: int) -> int:
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return parsed


def _bounded_float(value: Any, field_name: str, minimum: float, maximum: float) -> float:
    parsed = float(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return parsed


def _local_http_url(http_url: str, bind: str) -> str:
    if bind in {"0.0.0.0", "::", ""}:
        return http_url.replace(bind or "0.0.0.0", "127.0.0.1", 1)
    return http_url


def _access_http_url(http_url: str, bind: str) -> str:
    if bind in {"0.0.0.0", "::", ""}:
        return http_url.replace(bind or "0.0.0.0", _primary_ipv4_address(), 1)
    return http_url


def _primary_ipv4_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()
