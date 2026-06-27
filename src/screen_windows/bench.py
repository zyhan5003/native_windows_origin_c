from __future__ import annotations

import json

from .config import EncoderConfig, StreamConfig
from .encoder import EncoderManager, FfmpegError
from .video_source import SyntheticFrameSource


def run_encode_bench(frame_count: int = 24) -> dict[str, object]:
    stream_config = StreamConfig(source="synthetic", width=640, height=360, fps=24)
    encoder_manager = EncoderManager(EncoderConfig(), stream_config)
    if not encoder_manager.pipeline_support.ready:
        raise RuntimeError(encoder_manager.pipeline_support.reason)

    source = SyntheticFrameSource.from_config(stream_config)
    frames = [source.render(index) for index in range(frame_count)]
    runner = encoder_manager.create_runner()
    stats = runner.run_frames(frames)
    return {
        "ok": True,
        "encoder": encoder_manager.selection.ffmpeg_encoder,
        "backend": encoder_manager.selection.backend,
        "selection_reason": encoder_manager.selection.reason,
        "ffmpeg_path": encoder_manager.capabilities.ffmpeg_path,
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
        "frames_written": stats.frames_written,
        "elapsed_seconds": round(stats.elapsed_seconds, 4),
        "average_fps": round(stats.average_fps, 2),
        "return_code": stats.return_code,
        "stderr_empty": runner.stderr_output.strip() == "",
    }


def main() -> int:
    try:
        result = run_encode_bench()
    except FfmpegError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 1
    except RuntimeError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": "RuntimeError",
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0
