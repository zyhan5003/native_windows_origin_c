from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


@dataclass(frozen=True, slots=True)
class ClientAuthRequest:
    kind: str
    version: str
    pin: str | None = None
    token: str | None = None
    timestamp: int | None = None
    signature: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClientAuthRequest":
        return cls(
            kind=str(payload["type"]),
            version=str(payload.get("version", "0.1.0")),
            pin=payload.get("pin"),
            token=payload.get("token"),
            timestamp=payload.get("timestamp"),
            signature=payload.get("signature"),
        )


def build_auth_ok(
    *,
    token: str,
    http_port: int,
    ws_port: int,
    width: int,
    height: int,
    monitors: list[dict[str, Any]] | None = None,
    selected_monitor: int | None = None,
    clipboard_enabled: bool = False,
    file_transfer_enabled: bool = False,
) -> dict[str, Any]:
    return {
        "type": "auth_ok",
        "token": token,
        "capabilities": {
            "clipboard": clipboard_enabled,
            "file_transfer": file_transfer_enabled,
            "stats": True,
            "quality": True,
            "webrtc": True,
        },
        "display_info": {
            "width": width,
            "height": height,
            "selected_monitor": selected_monitor,
            "monitors": monitors or [],
        },
        "ports": {
            "http": http_port,
            "ws": ws_port,
        },
    }


def build_auth_error(reason: str) -> dict[str, Any]:
    return {"type": "auth_error", "reason": reason}


def build_webrtc_answer(*, sdp: str, description_type: str) -> dict[str, Any]:
    return {
        "type": "webrtc_answer",
        "sdp": sdp,
        "description_type": description_type,
    }


def build_input_ack(*, seq: int, processed_events: int) -> dict[str, Any]:
    return {
        "type": "input_ack",
        "seq": seq,
        "processed_events": processed_events,
    }


def build_clipboard_text(*, text: str, source: str) -> dict[str, Any]:
    return {
        "type": "clipboard_text",
        "mime": "text/plain",
        "source": source,
        "text": text,
    }


def build_clipboard_ack(*, text_length: int) -> dict[str, Any]:
    return {
        "type": "clipboard_ack",
        "mime": "text/plain",
        "text_length": text_length,
    }


def build_clipboard_error(reason: str) -> dict[str, Any]:
    return {
        "type": "clipboard_error",
        "reason": reason,
    }


def build_file_ready(*, transfer_id: str, offset: int) -> dict[str, Any]:
    return {
        "type": "file_ready",
        "id": transfer_id,
        "offset": offset,
    }


def build_file_chunk_ack(*, transfer_id: str, offset: int) -> dict[str, Any]:
    return {
        "type": "file_chunk_ack",
        "id": transfer_id,
        "offset": offset,
    }


def build_file_complete(
    *,
    transfer_id: str,
    name: str,
    size: int,
    path: str,
) -> dict[str, Any]:
    return {
        "type": "file_complete",
        "id": transfer_id,
        "name": name,
        "size": size,
        "path": path,
    }


def build_file_error(*, transfer_id: str, reason: str) -> dict[str, Any]:
    return {
        "type": "file_error",
        "id": transfer_id,
        "reason": reason,
    }


def build_file_access(*, ticket: str, expires_in_seconds: int) -> dict[str, Any]:
    return {
        "type": "file_access",
        "ticket": ticket,
        "expires_in_seconds": expires_in_seconds,
    }


def build_quality_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "quality_state",
        "quality": state,
    }


def build_quality_error(reason: str) -> dict[str, Any]:
    return {
        "type": "quality_error",
        "reason": reason,
    }


def build_pong(timestamp: int | float | str | None) -> dict[str, Any]:
    return {
        "type": "pong",
        "t": timestamp,
        "server_time": int(time.time() * 1000),
    }


def build_stats(runtime: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "stats",
        "runtime": runtime,
    }


def build_display_state(display: dict[str, Any], *, stream: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "display_state",
        "display": display,
        "stream": stream,
    }


def build_display_error(reason: str) -> dict[str, Any]:
    return {
        "type": "display_error",
        "reason": reason,
    }
