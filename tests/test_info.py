from __future__ import annotations

import json

from screen_windows.config import AppConfig, EncoderConfig, StreamConfig
from screen_windows.encoder import (
    EncoderProbeResult,
    EncoderSelection,
    FfmpegCapabilities,
    FfmpegPipelineSupport,
)
from screen_windows.info import build_info_payload, main as info_main, render_text_summary


class FakeEncoderManager:
    def __init__(self, encoder_config: EncoderConfig, stream_config: StreamConfig) -> None:
        self.capabilities = FfmpegCapabilities(
            ffmpeg_path="ffmpeg.exe",
            available=True,
            encoders=frozenset({"libx264"}),
            hwaccels=("cuda",),
            demuxers=frozenset({"rawvideo"}),
            muxers=frozenset({"null"}),
            version="ffmpeg version 8.1.1",
        )
        self.selection = EncoderSelection(
            backend="libx264",
            ffmpeg_encoder="libx264",
            codec="h264",
            available=True,
            reason="selected by runtime probe fallback",
        )
        self.pipeline_support = FfmpegPipelineSupport(
            ready=True,
            reason="ffmpeg rawvideo pipeline ready",
            missing_demuxers=(),
            missing_muxers=(),
        )
        self.probe_results = (
            EncoderProbeResult(
                backend="libx264",
                ffmpeg_encoder="libx264",
                success=True,
                reason="encoder startup probe passed",
            ),
        )

    def build_command(self) -> list[str]:
        return ["ffmpeg.exe", "-f", "rawvideo", "-c:v", "libx264"]


def test_build_info_payload_contains_encoder_gate(monkeypatch) -> None:
    from screen_windows import info as module

    monkeypatch.setattr(module, "EncoderManager", FakeEncoderManager)

    payload = build_info_payload(
        AppConfig(
            stream=StreamConfig(source="synthetic", width=640, height=360, fps=24),
        )
    )

    assert payload["status"] == "ready"
    assert payload["encoder"]["pipeline_ready"] is True
    assert payload["encoder"]["selected_backend"] == "libx264"
    assert payload["encoder"]["probe_results"][0]["success"] is True
    assert payload["stream"]["display"]["monitors"]


def test_render_text_summary_mentions_probe_result(monkeypatch) -> None:
    from screen_windows import info as module

    monkeypatch.setattr(module, "EncoderManager", FakeEncoderManager)
    payload = build_info_payload(AppConfig())

    summary = render_text_summary(payload)

    assert "status: ready" in summary
    assert "encoder: requested=auto selected=libx264" in summary
    assert "probes: libx264=ok" in summary


def test_info_main_json_uses_config_and_exit_code(monkeypatch, capsys) -> None:
    from screen_windows import info as module

    monkeypatch.setattr(module, "EncoderManager", FakeEncoderManager)

    exit_code = info_main(["--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["encoder"]["pipeline_ready"] is True
