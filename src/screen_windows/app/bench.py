from __future__ import annotations

import argparse
import json
from dataclasses import replace

from .config import AppConfig, load_config
from ..media.encoder import EncoderManager, FfmpegError
from ..media.video_source import SyntheticFrameSource


def run_encode_bench(
    *,
    config: AppConfig | None = None,
    frame_count: int = 24,
    width: int | None = None,
    height: int | None = None,
    fps: int | None = None,
) -> dict[str, object]:
    base_config = config or AppConfig()
    stream_config = replace(
        base_config.stream,
        source="synthetic",
        width=width or base_config.stream.width,
        height=height or base_config.stream.height,
        fps=fps or base_config.stream.fps,
    )
    encoder_manager = EncoderManager(base_config.encoder, stream_config)
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
        "bench": {
            "width": stream_config.width,
            "height": stream_config.height,
            "fps": stream_config.fps,
            "frames": frame_count,
        },
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行最小 FFmpeg 编码链路基准")
    parser.add_argument("--config", default=None, help="TOML 配置文件路径")
    parser.add_argument("--frames", type=int, default=24, help="写入帧数")
    parser.add_argument("--width", type=int, default=None, help="覆盖测试宽度")
    parser.add_argument("--height", type=int, default=None, help="覆盖测试高度")
    parser.add_argument("--fps", type=int, default=None, help="覆盖测试 FPS")
    parser.add_argument("--json", action="store_true", help="格式化 JSON 输出")
    args = parser.parse_args(argv)

    try:
        result = run_encode_bench(
            config=load_config(args.config),
            frame_count=max(args.frames, 1),
            width=args.width,
            height=args.height,
            fps=args.fps,
        )
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

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None))
    return 0
