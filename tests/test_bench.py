from __future__ import annotations

from datetime import UTC, datetime
import json

import numpy as np

from screen_windows.app.bench import main as bench_main
from screen_windows.app.bench import run_encode_bench
from screen_windows.app.config import EncoderConfig, StreamConfig
from screen_windows.media.encoder import EncodingStats, FfmpegPipelineError


def test_run_encode_bench_returns_expected_shape(monkeypatch) -> None:
    from screen_windows.app import bench as module

    class FakeRunner:
        stderr_output = ""

        def run_frames(self, frames):
            assert len(frames) == 12
            assert isinstance(frames[0], np.ndarray)
            return EncodingStats(
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                frames_written=len(frames),
                elapsed_seconds=1.0,
                average_fps=float(len(frames)),
                return_code=0,
            )

    class FakeManager:
        def __init__(self, encoder_config: EncoderConfig, stream_config: StreamConfig) -> None:
            self.stream_config = stream_config
            self.selection = type(
                "Selection",
                (),
                {
                    "available": True,
                    "ffmpeg_encoder": "libx264",
                    "backend": "libx264",
                    "reason": "selected by runtime probe fallback",
                },
            )()
            self.capabilities = type(
                "Capabilities",
                (),
                {"ffmpeg_path": "ffmpeg.exe"},
            )()
            self.pipeline_support = type(
                "Pipeline",
                (),
                {"ready": True, "reason": "ffmpeg rawvideo pipeline ready"},
            )()
            self.probe_results = ()

        def create_runner(self):
            return FakeRunner()

    monkeypatch.setattr(module, "EncoderManager", FakeManager)

    result = run_encode_bench(frame_count=12, width=320, height=180, fps=30)

    assert result["encoder"] == "libx264"
    assert result["frames_written"] == 12
    assert result["return_code"] == 0
    assert result["ok"] is True
    assert result["pipeline_ready"] is True
    assert result["selection_reason"] == "selected by runtime probe fallback"
    assert result["probe_results"] == []
    assert result["bench"] == {"width": 320, "height": 180, "fps": 30, "frames": 12}


def test_bench_main_reports_structured_pipeline_error(
    monkeypatch,
    capsys,
) -> None:
    from screen_windows.app import bench as module

    def fake_run_encode_bench(**kwargs) -> dict[str, object]:
        raise FfmpegPipelineError(
            "ffmpeg rawvideo pipeline unavailable (missing demuxers: rawvideo)"
        )

    monkeypatch.setattr(module, "run_encode_bench", fake_run_encode_bench)

    exit_code = bench_main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_type"] == "FfmpegPipelineError"
    assert "missing demuxers: rawvideo" in payload["error"]


def test_bench_main_forwards_cli_overrides(monkeypatch, capsys) -> None:
    from screen_windows.app import bench as module

    calls = []

    def fake_run_encode_bench(**kwargs) -> dict[str, object]:
        calls.append(("bench", kwargs))
        return {"ok": True, "bench": {"frames": kwargs["frame_count"]}}

    monkeypatch.setattr(module, "load_config", lambda path: None)
    monkeypatch.setattr(module, "run_encode_bench", fake_run_encode_bench)

    exit_code = bench_main(["--config", "host.toml", "--frames", "9", "--width", "800", "--height", "450", "--fps", "60", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert calls == [
        (
            "bench",
            {
                "config": None,
                "frame_count": 9,
                "width": 800,
                "height": 450,
                "fps": 60,
            },
        )
    ]
