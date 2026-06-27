from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import asyncio
import json
from pathlib import Path
import platform
import secrets
import time
from typing import Any

from aiohttp import web
from websockets.asyncio.server import Server, ServerConnection, serve

from .auth import TokenManager, TokenStore
from .clipboard import ClipboardService, WindowsClipboardBackend
from .config import AppConfig
from .display import DisplayMonitor, enumerate_displays
from .discovery import DiscoveryAnnouncement, DiscoveryManager
from .encoder import EncoderManager
from .filetransfer import FileTransferError, FileTransferService
from .input import InputBatch, InputExecutor, WindowsInputExecutor
from .protocol import (
    ClientAuthRequest,
    build_auth_error,
    build_auth_ok,
    build_clipboard_ack,
    build_clipboard_error,
    build_clipboard_text,
    build_display_error,
    build_display_state,
    build_file_access,
    build_file_chunk_ack,
    build_file_complete,
    build_file_error,
    build_file_ready,
    build_input_ack,
    build_pong,
    build_quality_error,
    build_quality_state,
    build_stats,
    build_webrtc_answer,
)
from .quality import QualityController, QualitySignal
from .stats import SystemStatsCollector
from .video_source import build_frame_source
from .webrtc import WebRtcSession
from .webui import INDEX_HTML


@dataclass(slots=True)
class HostRuntimeState:
    started_at: datetime
    authenticated_clients: int = 0
    active_webrtc_sessions: int = 0
    input_batches: int = 0
    input_events: int = 0


@dataclass(slots=True)
class ClientSessionContext:
    authenticated: bool = False
    peer_session: WebRtcSession | None = None
    file_transfer_ids: set[str] = field(default_factory=set)


FILE_ACCESS_TTL_SECONDS = 300


class HostServer:
    def __init__(
        self,
        config: AppConfig,
        *,
        input_executor: InputExecutor | None = None,
        clipboard_service: ClipboardService | None = None,
        file_transfer_service: FileTransferService | None = None,
    ) -> None:
        self._config = config
        self._auth_mode = config.auth.mode.strip().lower()
        token_store = (
            TokenStore(config.auth.token_store_path)
            if config.auth.token_store_path
            else None
        )
        self._token_manager = TokenManager(
            config.auth.pin,
            ttl_seconds=config.auth.token_ttl_seconds,
            token_store=token_store,
        )
        self._state = HostRuntimeState(started_at=datetime.now(UTC))
        self._app = web.Application()
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/api/health", self._handle_health)
        self._app.router.add_get("/api/files", self._handle_file_list)
        self._app.router.add_get("/api/files/{name}", self._handle_file_download)
        self._app.router.add_get("/favicon.ico", self._handle_favicon)
        self._web_runner: web.AppRunner | None = None
        self._http_site: web.TCPSite | None = None
        self._ws_server: Server | None = None
        self._frame_source = build_frame_source(config.stream)
        self._display_info = enumerate_displays(config.stream)
        self._discovery_manager = DiscoveryManager(
            method=config.discovery.method,
            udp_port=config.discovery.udp_port,
            interval_seconds=config.discovery.announce_interval_seconds,
        )
        self._encoder_manager = EncoderManager(config.encoder, config.stream)
        self._system_stats = SystemStatsCollector()
        self._quality_controller = QualityController(
            mode=config.quality.mode,
            profile=config.quality.profile,
        )
        self._peer_sessions: set[WebRtcSession] = set()
        self._input_executor_injected = input_executor is not None
        input_bounds = self._build_input_bounds()
        self._input_executor = input_executor or WindowsInputExecutor(**input_bounds)
        self._clipboard_service = clipboard_service or ClipboardService(
            backend=WindowsClipboardBackend(),
            backend_name="win32",
        )
        self._file_transfer_service = file_transfer_service or FileTransferService(
            receive_dir=Path(config.file_transfer.receive_dir),
            max_file_size=config.file_transfer.max_file_size,
            chunk_size=config.file_transfer.chunk_size,
        )
        self._file_access_tickets: dict[str, float] = {}

    @property
    def token_manager(self) -> TokenManager:
        return self._token_manager

    @property
    def app(self) -> web.Application:
        return self._app

    async def _handle_index(self, request: web.Request) -> web.Response:
        return web.Response(text=INDEX_HTML, content_type="text/html")

    async def _handle_health(self, request: web.Request) -> web.Response:
        payload = self._build_health_payload()
        return web.json_response(payload)

    async def _handle_file_list(self, request: web.Request) -> web.Response:
        if not self._is_file_http_authorized(request):
            return web.json_response({"error": "file access ticket required"}, status=401)
        files = await asyncio.to_thread(self._file_transfer_service.list_files)
        return web.json_response(
            {
                "files": [file_info.to_dict() for file_info in files],
            }
        )

    async def _handle_file_download(self, request: web.Request) -> web.StreamResponse:
        if not self._is_file_http_authorized(request):
            return web.json_response({"error": "file access ticket required"}, status=401)
        name = str(request.match_info.get("name", ""))
        try:
            path = await asyncio.to_thread(
                self._file_transfer_service.resolve_download_path,
                name,
            )
        except FileTransferError as exc:
            return web.json_response({"error": str(exc)}, status=404)
        return web.FileResponse(
            path,
            headers={
                "Content-Disposition": f'attachment; filename="{path.name}"',
            },
        )

    def _is_file_http_authorized(self, request: web.Request) -> bool:
        if self._auth_mode == "none":
            return True
        return self._verify_file_access_ticket(str(request.query.get("ticket", "")))

    def _issue_file_access_ticket(self) -> tuple[str, int]:
        self._prune_file_access_tickets()
        ticket = secrets.token_urlsafe(24)
        self._file_access_tickets[ticket] = time.monotonic() + FILE_ACCESS_TTL_SECONDS
        return ticket, FILE_ACCESS_TTL_SECONDS

    def _verify_file_access_ticket(self, ticket: str) -> bool:
        self._prune_file_access_tickets()
        if not ticket:
            return False
        return ticket in self._file_access_tickets

    def _prune_file_access_tickets(self) -> None:
        now = time.monotonic()
        expired = [
            ticket
            for ticket, expires_at in self._file_access_tickets.items()
            if expires_at < now
        ]
        for ticket in expired:
            del self._file_access_tickets[ticket]

    def _build_runtime_stats_payload(self) -> dict[str, Any]:
        uptime_seconds = int((datetime.now(UTC) - self._state.started_at).total_seconds())
        return {
            "uptime_seconds": uptime_seconds,
            "authenticated_clients": self._state.authenticated_clients,
            "active_webrtc_sessions": self._state.active_webrtc_sessions,
            "system": self._system_stats.snapshot().to_dict(),
            "webrtc": {
                "sessions": [peer_session.stats for peer_session in self._peer_sessions],
            },
            "input": {
                "batches": self._state.input_batches,
                "events": self._state.input_events,
            },
            "file_transfer": {
                "active": self._file_transfer_service.active_count,
                "completed_files": self._file_transfer_service.completed_files,
                "completed_bytes": self._file_transfer_service.completed_bytes,
                "canceled_files": self._file_transfer_service.canceled_files,
                "canceled_bytes": self._file_transfer_service.canceled_bytes,
            },
            "quality": self._quality_controller.state.to_dict(),
        }

    def _build_health_payload(self) -> dict[str, Any]:
        runtime = self._build_runtime_stats_payload()
        payload = {
            "status": "ok",
            "service": "screen_windows_host",
            "auth_mode": self._config.auth.mode,
            "device_name": platform.node(),
            "uptime_seconds": runtime["uptime_seconds"],
            "authenticated_clients": runtime["authenticated_clients"],
            "active_webrtc_sessions": runtime["active_webrtc_sessions"],
            "ports": {
                "http": self._config.server.http_port,
                "ws": self._config.server.port,
            },
            "discovery": self._discovery_manager.status,
            "system": runtime["system"],
            "runtime": runtime,
            "stream": {
                "source": self._frame_source.source_name,
                "requested_source": self._config.stream.source,
                "width": self._config.stream.width,
                "height": self._config.stream.height,
                "fps": self._config.stream.fps,
                "monitor": self._config.stream.monitor,
                "display": self._display_info.to_dict(),
            },
            "webrtc": runtime["webrtc"],
            "input": {
                "enabled": True,
                "batches": runtime["input"]["batches"],
                "events": runtime["input"]["events"],
            },
            "clipboard": {
                "enabled": True,
                "backend": self._clipboard_service.backend_name,
                "mime_types": list(self._clipboard_service.mime_types),
                "reads": self._clipboard_service.read_count,
                "writes": self._clipboard_service.write_count,
            },
            "file_transfer": {
                "enabled": True,
                "receive_dir": str(self._file_transfer_service.receive_dir),
                "chunk_size": self._file_transfer_service.chunk_size,
                "max_file_size": self._file_transfer_service.max_file_size,
                "active": runtime["file_transfer"]["active"],
                "completed_files": runtime["file_transfer"]["completed_files"],
                "completed_bytes": runtime["file_transfer"]["completed_bytes"],
                "canceled_files": runtime["file_transfer"]["canceled_files"],
                "canceled_bytes": runtime["file_transfer"]["canceled_bytes"],
            },
            "quality": runtime["quality"],
            "encoder": {
                "ffmpeg_available": self._encoder_manager.capabilities.available,
                "ffmpeg_path": self._encoder_manager.capabilities.ffmpeg_path,
                "version": self._encoder_manager.capabilities.version,
                "requested_backend": self._config.encoder.backend,
                "selected_backend": self._encoder_manager.selection.backend,
                "ffmpeg_encoder": self._encoder_manager.selection.ffmpeg_encoder,
                "available": self._encoder_manager.selection.available,
                "reason": self._encoder_manager.selection.reason,
                "probe_results": [
                    {
                        "backend": probe.backend,
                        "ffmpeg_encoder": probe.ffmpeg_encoder,
                        "success": probe.success,
                        "reason": probe.reason,
                    }
                    for probe in self._encoder_manager.probe_results
                ],
                "hwaccels": list(self._encoder_manager.capabilities.hwaccels),
                "demuxers": sorted(self._encoder_manager.capabilities.demuxers),
                "muxers": sorted(self._encoder_manager.capabilities.muxers),
                "pipeline_ready": self._encoder_manager.pipeline_support.ready,
                "pipeline_reason": self._encoder_manager.pipeline_support.reason,
                "pipeline_missing_demuxers": list(
                    self._encoder_manager.pipeline_support.missing_demuxers
                ),
                "pipeline_missing_muxers": list(
                    self._encoder_manager.pipeline_support.missing_muxers
                ),
                "command_preview": self._encoder_manager.build_command()
                if self._encoder_manager.pipeline_support.ready
                else [],
            },
        }
        return payload

    async def _handle_favicon(self, request: web.Request) -> web.Response:
        return web.Response(status=204)

    async def _handle_websocket_connection(self, ws: ServerConnection) -> None:
        session = ClientSessionContext()
        try:
            async for raw_message in ws:
                if not isinstance(raw_message, str):
                    await ws.send(json.dumps(build_auth_error("text message required")))
                    continue

                try:
                    payload = json.loads(raw_message)
                except json.JSONDecodeError:
                    await ws.send(json.dumps(build_auth_error("invalid json payload")))
                    continue

                if not session.authenticated:
                    session.authenticated = await self._process_auth_message(ws, payload)
                    if session.authenticated:
                        self._state.authenticated_clients += 1
                    continue

                await self._process_control_message(ws, session, payload)
        finally:
            if session.peer_session is not None:
                await self._close_peer_session(session.peer_session)
                session.peer_session = None
            if session.file_transfer_ids:
                await asyncio.to_thread(
                    self._file_transfer_service.cancel_many,
                    session.file_transfer_ids,
                )
                session.file_transfer_ids.clear()
            if session.authenticated and self._state.authenticated_clients > 0:
                self._state.authenticated_clients -= 1

    async def _process_auth_message(
        self,
        ws: ServerConnection,
        payload: dict[str, Any],
    ) -> bool:
        try:
            request = ClientAuthRequest.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            await ws.send(json.dumps(build_auth_error("invalid auth payload")))
            return False

        if request.kind != "auth":
            await ws.send(json.dumps(build_auth_error("auth required")))
            return False

        if self._auth_mode == "none":
            await ws.send(json.dumps(self._build_auth_ok_payload(token=request.token or "auth-none")))
            return True

        if request.pin:
            try:
                session = self._token_manager.issue_token(request.pin)
            except ValueError:
                await ws.send(json.dumps(build_auth_error("invalid pin")))
                return False

            await ws.send(json.dumps(self._build_auth_ok_payload(token=session.token)))
            return True

        if request.token and request.timestamp and request.signature:
            if self._auth_mode == "always":
                await ws.send(json.dumps(build_auth_error("pin required")))
                return False
            is_valid = self._token_manager.verify_token(
                request.token,
                request.timestamp,
                request.signature,
            )
            if not is_valid:
                await ws.send(json.dumps(build_auth_error("invalid token")))
                return False

            await ws.send(json.dumps(self._build_auth_ok_payload(token=request.token)))
            return True

        await ws.send(json.dumps(build_auth_error("missing credentials")))
        return False

    def _build_auth_ok_payload(self, *, token: str) -> dict[str, Any]:
        return build_auth_ok(
            token=token,
            http_port=self._config.server.http_port,
            ws_port=self._config.server.port,
            width=self._config.stream.width,
            height=self._config.stream.height,
            monitors=[
                monitor.to_dict()
                for monitor in self._display_info.monitors
            ],
            selected_monitor=self._display_info.selected_monitor,
            clipboard_enabled=True,
            file_transfer_enabled=True,
            file_transfer_limits={
                "chunk_size": self._file_transfer_service.chunk_size,
                "max_file_size": self._file_transfer_service.max_file_size,
            },
        )

    async def _process_control_message(
        self,
        ws: ServerConnection,
        session: ClientSessionContext,
        payload: dict[str, Any],
    ) -> None:
        message_type = str(payload.get("type", ""))

        if message_type == "webrtc_offer":
            if session.peer_session is not None:
                await self._close_peer_session(session.peer_session)
            session.peer_session = WebRtcSession(
                self._frame_source,
                quality_profile_provider=lambda: self._quality_controller.state.profile,
                quality_signal_callback=lambda signal: self._quality_controller.update(signal),
                closed_callback=self._schedule_peer_session_cleanup,
            )
            self._peer_sessions.add(session.peer_session)
            self._state.active_webrtc_sessions = len(self._peer_sessions)

            description = await session.peer_session.create_answer(
                offer_sdp=str(payload["sdp"]),
                offer_type=str(payload.get("description_type", "offer")),
            )
            await ws.send(
                json.dumps(
                    build_webrtc_answer(
                        sdp=description.sdp,
                        description_type=description.type,
                    )
                )
            )
            return

        if message_type == "webrtc_close":
            if session.peer_session is not None:
                await self._close_peer_session(session.peer_session)
                session.peer_session = None
            await ws.send(json.dumps({"type": "webrtc_closed"}))
            return

        if message_type == "input":
            batch = InputBatch.from_dict(payload)
            await asyncio.to_thread(self._input_executor.execute_batch, batch)
            self._state.input_batches += 1
            self._state.input_events += len(batch.events)
            await ws.send(
                json.dumps(
                    build_input_ack(
                        seq=batch.seq,
                        processed_events=len(batch.events),
                    )
                )
            )
            return

        if message_type == "clipboard_read":
            try:
                text = await asyncio.to_thread(self._clipboard_service.read_text)
            except OSError as exc:
                await ws.send(json.dumps(build_clipboard_error(str(exc))))
                return
            await ws.send(json.dumps(build_clipboard_text(text=text, source="host")))
            return

        if message_type == "clipboard_write":
            mime = str(payload.get("mime", "text/plain"))
            text = payload.get("text", "")
            if mime != "text/plain" or not isinstance(text, str):
                await ws.send(json.dumps(build_clipboard_error("invalid clipboard payload")))
                return
            try:
                await asyncio.to_thread(self._clipboard_service.write_text, text)
            except OSError as exc:
                await ws.send(json.dumps(build_clipboard_error(str(exc))))
                return
            await ws.send(json.dumps(build_clipboard_ack(text_length=len(text))))
            return

        if message_type == "file_req":
            await self._process_file_request(ws, session, payload)
            return

        if message_type == "file_access":
            ticket, expires_in_seconds = self._issue_file_access_ticket()
            await ws.send(
                json.dumps(
                    build_file_access(
                        ticket=ticket,
                        expires_in_seconds=expires_in_seconds,
                    )
                )
            )
            return

        if message_type == "file_chunk":
            await self._process_file_chunk(ws, payload)
            return

        if message_type == "quality":
            await self._process_quality_message(ws, payload)
            return

        if message_type == "ping":
            await ws.send(json.dumps(build_pong(payload.get("t"))))
            return

        if message_type == "stats":
            await ws.send(json.dumps(build_stats(self._build_runtime_stats_payload())))
            return

        if message_type == "display_switch":
            await self._process_display_switch(ws, session, payload)
            return

        await ws.send(
            json.dumps(
                {
                    "type": "echo",
                    "message": payload,
                }
            )
        )

    async def _process_quality_message(
        self,
        ws: ServerConnection,
        payload: dict[str, Any],
    ) -> None:
        if str(payload.get("action", "")).lower() == "state":
            await ws.send(json.dumps(build_quality_state(self._quality_controller.state.to_dict())))
            return
        if str(payload.get("action", "")).lower() == "signals":
            try:
                state = self._quality_controller.update(
                    QualitySignal.from_dict(payload.get("signals")),
                )
            except (TypeError, ValueError) as exc:
                await ws.send(json.dumps(build_quality_error(str(exc))))
                return
            await ws.send(json.dumps(build_quality_state(state.to_dict())))
            return

        mode = str(payload.get("mode", "auto")).lower()
        try:
            if mode == "manual":
                state = self._quality_controller.set_manual(str(payload.get("profile", "")))
            elif mode == "auto":
                if "signals" in payload:
                    signal = QualitySignal.from_dict(payload.get("signals"))
                else:
                    signal = None
                state = self._quality_controller.set_auto(signal)
            else:
                await ws.send(json.dumps(build_quality_error("quality mode must be auto or manual")))
                return
        except (TypeError, ValueError) as exc:
            await ws.send(json.dumps(build_quality_error(str(exc))))
            return

        await ws.send(json.dumps(build_quality_state(state.to_dict())))

    async def _process_display_switch(
        self,
        ws: ServerConnection,
        session: ClientSessionContext,
        payload: dict[str, Any],
    ) -> None:
        try:
            monitor = int(payload.get("monitor", -1))
            display_state = await self._set_monitor(monitor)
        except (TypeError, ValueError) as exc:
            await ws.send(json.dumps(build_display_error(str(exc))))
            return

        if session.peer_session is not None:
            await self._close_peer_session(session.peer_session)
            session.peer_session = None
        await ws.send(json.dumps(display_state))

    async def _set_monitor(self, monitor: int) -> dict[str, Any]:
        if monitor < 0 or monitor >= len(self._display_info.monitors):
            raise ValueError("invalid monitor")

        self._config = replace(
            self._config,
            stream=replace(self._config.stream, monitor=monitor),
        )
        self._frame_source = await asyncio.to_thread(build_frame_source, self._config.stream)
        self._display_info = enumerate_displays(self._config.stream)
        self._update_input_display_bounds()
        return build_display_state(
            self._display_info.to_dict(),
            stream={
                "source": self._frame_source.source_name,
                "width": self._config.stream.width,
                "height": self._config.stream.height,
                "fps": self._config.stream.fps,
                "monitor": self._config.stream.monitor,
            },
        )

    def _update_input_display_bounds(self) -> None:
        input_bounds = self._build_input_bounds()
        if self._input_executor_injected:
            for key, value in input_bounds.items():
                setattr(self._input_executor, key, value)
            return
        self._input_executor = WindowsInputExecutor(**input_bounds)

    def _build_input_bounds(self) -> dict[str, int]:
        monitor = self._selected_monitor()
        virtual_left, virtual_top, virtual_width, virtual_height = _virtual_desktop_bounds(
            self._display_info.monitors,
        )
        return {
            "display_width": self._frame_source.width,
            "display_height": self._frame_source.height,
            "display_left": monitor.left,
            "display_top": monitor.top,
            "virtual_left": virtual_left,
            "virtual_top": virtual_top,
            "virtual_width": virtual_width,
            "virtual_height": virtual_height,
        }

    def _selected_monitor(self) -> DisplayMonitor:
        selected = self._display_info.selected_monitor
        if 0 <= selected < len(self._display_info.monitors):
            return self._display_info.monitors[selected]
        return self._display_info.monitors[0]

    async def _process_file_request(
        self,
        ws: ServerConnection,
        session: ClientSessionContext,
        payload: dict[str, Any],
    ) -> None:
        transfer_id = str(payload.get("id", ""))
        action = str(payload.get("action", "send"))
        try:
            if action == "send":
                transfer = await asyncio.to_thread(
                    self._file_transfer_service.start_upload,
                    transfer_id=transfer_id,
                    name=str(payload.get("name", "")),
                    size=int(payload.get("size", -1)),
                )
                session.file_transfer_ids.add(transfer.transfer_id)
                await ws.send(
                    json.dumps(
                        build_file_ready(
                            transfer_id=transfer.transfer_id,
                            offset=transfer.bytes_received,
                        )
                    )
                )
                return

            if action == "complete":
                transfer = await asyncio.to_thread(
                    self._file_transfer_service.complete_upload,
                    transfer_id=transfer_id,
                )
                session.file_transfer_ids.discard(transfer.transfer_id)
                await ws.send(
                    json.dumps(
                        build_file_complete(
                            transfer_id=transfer.transfer_id,
                            name=transfer.safe_name,
                            size=transfer.expected_size,
                            path=str(transfer.target_path),
                        )
                    )
                )
                return
        except (FileTransferError, ValueError) as exc:
            await ws.send(json.dumps(build_file_error(transfer_id=transfer_id, reason=str(exc))))
            return

        await ws.send(
            json.dumps(
                build_file_error(
                    transfer_id=transfer_id,
                    reason="unsupported file action",
                )
            )
        )

    async def _process_file_chunk(
        self,
        ws: ServerConnection,
        payload: dict[str, Any],
    ) -> None:
        transfer_id = str(payload.get("id", ""))
        try:
            transfer = await asyncio.to_thread(
                self._file_transfer_service.write_chunk,
                transfer_id=transfer_id,
                offset=int(payload.get("offset", -1)),
                data_base64=str(payload.get("data", "")),
            )
        except (FileTransferError, ValueError) as exc:
            await ws.send(json.dumps(build_file_error(transfer_id=transfer_id, reason=str(exc))))
            return

        await ws.send(
            json.dumps(
                build_file_chunk_ack(
                    transfer_id=transfer.transfer_id,
                    offset=transfer.bytes_received,
                )
            )
        )

    async def _close_peer_session(self, peer_session: WebRtcSession) -> None:
        if peer_session in self._peer_sessions:
            self._peer_sessions.remove(peer_session)
        self._state.active_webrtc_sessions = len(self._peer_sessions)
        await peer_session.close_without_notify()

    def _schedule_peer_session_cleanup(self, peer_session: WebRtcSession) -> None:
        # aiortc 可能因网络断开自行进入 failed/closed，必须同步清理 Host 侧统计。
        asyncio.create_task(self._close_peer_session(peer_session))

    async def start(self) -> None:
        self._web_runner = web.AppRunner(self._app)
        await self._web_runner.setup()
        self._http_site = web.TCPSite(
            self._web_runner,
            host=self._config.server.bind,
            port=self._config.server.http_port,
        )
        await self._http_site.start()
        self._ws_server = await serve(
            self._handle_websocket_connection,
            self._config.server.bind,
            self._config.server.port,
        )
        await self._discovery_manager.start(
            DiscoveryAnnouncement(
                device_name=platform.node() or "screen-windows",
                ws_port=self._config.server.port,
                http_port=self._config.server.http_port,
                auth_mode=self._config.auth.mode,
            )
        )

        print(
            f"screen_windows host started: "
            f"http://{self._config.server.bind}:{self._config.server.http_port} "
            f"ws://{self._config.server.bind}:{self._config.server.port} "
            f"pin={self._token_manager.pin} "
            f"stream={self._frame_source.source_name}:{self._config.stream.width}x{self._config.stream.height}@{self._config.stream.fps} "
            f"encoder={self._encoder_manager.selection.backend or 'none'}"
        )

    async def run_forever(self) -> None:
        await self.start()
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        for peer_session in list(self._peer_sessions):
            await self._close_peer_session(peer_session)

        await self._discovery_manager.stop()

        if self._ws_server is not None:
            self._ws_server.close()
            await self._ws_server.wait_closed()
            self._ws_server = None

        if self._web_runner is not None:
            await self._web_runner.cleanup()
            self._web_runner = None
            self._http_site = None


def _virtual_desktop_bounds(monitors: list[DisplayMonitor]) -> tuple[int, int, int, int]:
    left = min(monitor.left for monitor in monitors)
    top = min(monitor.top for monitor in monitors)
    right = max(monitor.left + monitor.width for monitor in monitors)
    bottom = max(monitor.top + monitor.height for monitor in monitors)
    return left, top, max(right - left, 1), max(bottom - top, 1)
