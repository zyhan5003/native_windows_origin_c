from __future__ import annotations

import json
import platform
import sys
from typing import Any

from .config import AppConfig, load_config
from .display import enumerate_displays
from .encoder import EncoderManager


def build_info_payload(config: AppConfig) -> dict[str, Any]:
    encoder_manager = EncoderManager(config.encoder, config.stream)
    display_info = enumerate_displays(config.stream)
    return {
        "status": "ready" if encoder_manager.pipeline_support.ready else "attention",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": sys.version.split()[0],
            "machine": platform.machine(),
        },
        "stream": {
            "source": config.stream.source,
            "width": config.stream.width,
            "height": config.stream.height,
            "fps": config.stream.fps,
            "monitor": config.stream.monitor,
            "display": display_info.to_dict(),
        },
        "encoder": {
            "ffmpeg_available": encoder_manager.capabilities.available,
            "ffmpeg_path": encoder_manager.capabilities.ffmpeg_path,
            "version": encoder_manager.capabilities.version,
            "requested_backend": config.encoder.backend,
            "selected_backend": encoder_manager.selection.backend,
            "ffmpeg_encoder": encoder_manager.selection.ffmpeg_encoder,
            "available": encoder_manager.selection.available,
            "reason": encoder_manager.selection.reason,
            "pipeline_ready": encoder_manager.pipeline_support.ready,
            "pipeline_reason": encoder_manager.pipeline_support.reason,
            "probe_results": [
                {
                    "backend": probe.backend,
                    "ffmpeg_encoder": probe.ffmpeg_encoder,
                    "success": probe.success,
                    "reason": probe.reason,
                }
                for probe in encoder_manager.probe_results
            ],
            "hwaccels": list(encoder_manager.capabilities.hwaccels),
            "command_preview": encoder_manager.build_command()
            if encoder_manager.pipeline_support.ready
            else [],
        },
        "auth": {
            "mode": config.auth.mode,
            "token_store_configured": bool(config.auth.token_store_path),
        },
        "discovery": {
            "method": config.discovery.method,
            "udp_port": config.discovery.udp_port,
        },
    }


def render_text_summary(payload: dict[str, Any]) -> str:
    encoder = payload["encoder"]
    stream = payload["stream"]
    display = stream["display"]
    lines = [
        f"status: {payload['status']}",
        (
            "platform: "
            f"{payload['platform']['system']} {payload['platform']['release']} "
            f"python={payload['platform']['python']}"
        ),
        (
            "stream: "
            f"{stream['source']} {stream['width']}x{stream['height']}@{stream['fps']} "
            f"monitor={stream['monitor']} display_source={display['source']}"
        ),
        (
            "encoder: "
            f"requested={encoder['requested_backend']} "
            f"selected={encoder['selected_backend']} "
            f"ffmpeg_encoder={encoder['ffmpeg_encoder'] or 'none'}"
        ),
        (
            "ffmpeg: "
            f"available={encoder['ffmpeg_available']} "
            f"pipeline_ready={encoder['pipeline_ready']} "
            f"path={encoder['ffmpeg_path'] or 'not-found'}"
        ),
        f"reason: {encoder['pipeline_reason'] or encoder['reason']}",
    ]
    if encoder["probe_results"]:
        # 这里保留最关键的探针结论，方便现场快速判断硬编是否真的可启动。
        probe_text = ", ".join(
            f"{probe['backend']}={'ok' if probe['success'] else 'fail'}"
            for probe in encoder["probe_results"]
        )
        lines.append(f"probes: {probe_text}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="输出 screen_windows 环境与编码摘要")
    parser.add_argument("--config", default=None, help="TOML 配置文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    payload = build_info_payload(load_config(args.config))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text_summary(payload))
    return 0 if payload["encoder"]["pipeline_ready"] else 1
