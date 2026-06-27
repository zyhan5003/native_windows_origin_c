from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time

import numpy as np

from .config import EncoderConfig, StreamConfig


DEFAULT_FFMPEG_CANDIDATES = (
    r"C:\Users\lenovo\.marscode\ai-chat\binary\1.7.0\modules\ai-agent\ffmpeg.exe",
    r"C:\Users\lenovo\.marscode\ai-chat\binary\1.6.38\modules\ai-agent\ffmpeg.exe",
)

ENV_FFMPEG_PATH = "SCREEN_WINDOWS_FFMPEG"

BACKEND_TO_ENCODER = {
    "nvenc": "h264_nvenc",
    "amf": "h264_amf",
    "qsv": "h264_qsv",
    "libx264": "libx264",
}

BACKEND_PRIORITY = ("nvenc", "amf", "qsv", "libx264")

LOW_LATENCY_PRESET_MAP = {
    "nvenc": "p1",
    "amf": "speed",
    "qsv": "veryfast",
}


@dataclass(frozen=True, slots=True)
class FfmpegCapabilities:
    ffmpeg_path: str
    available: bool
    encoders: frozenset[str]
    hwaccels: tuple[str, ...]
    demuxers: frozenset[str]
    muxers: frozenset[str]
    version: str


@dataclass(frozen=True, slots=True)
class EncoderSelection:
    backend: str
    ffmpeg_encoder: str
    codec: str
    available: bool
    reason: str


@dataclass(frozen=True, slots=True)
class FfmpegPipelineSupport:
    ready: bool
    reason: str
    missing_demuxers: tuple[str, ...]
    missing_muxers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EncoderProbeResult:
    backend: str
    ffmpeg_encoder: str
    success: bool
    reason: str


@dataclass(frozen=True, slots=True)
class EncodingStats:
    started_at: datetime
    ended_at: datetime
    frames_written: int
    elapsed_seconds: float
    average_fps: float
    return_code: int


class FfmpegError(RuntimeError):
    """FFmpeg 相关错误基类。"""


class FfmpegPipelineError(FfmpegError):
    """FFmpeg 能力不足，无法建立当前编码管线。"""


class FfmpegProcessError(FfmpegError):
    """FFmpeg 进程在编码过程中异常退出。"""


class EncoderManager:
    def __init__(self, encoder_config: EncoderConfig, stream_config: StreamConfig) -> None:
        self._encoder_config = encoder_config
        self._stream_config = stream_config
        self._capabilities = detect_ffmpeg_capabilities(encoder_config.ffmpeg_path)
        self._selection, self._probe_results = resolve_working_selection(
            encoder_config,
            stream_config,
            self._capabilities,
        )
        self._pipeline_support = evaluate_pipeline_support(
            self._selection,
            self._capabilities,
        )

    @property
    def capabilities(self) -> FfmpegCapabilities:
        return self._capabilities

    @property
    def selection(self) -> EncoderSelection:
        return self._selection

    @property
    def pipeline_support(self) -> FfmpegPipelineSupport:
        return self._pipeline_support

    @property
    def probe_results(self) -> tuple[EncoderProbeResult, ...]:
        return self._probe_results

    def build_command(self) -> list[str]:
        ensure_pipeline_ready(self._pipeline_support)
        return build_ffmpeg_command(
            self._selection,
            self._encoder_config,
            self._stream_config,
            self._capabilities.ffmpeg_path,
        )

    def create_runner(self) -> "FfmpegEncodeRunner":
        return FfmpegEncodeRunner(self.build_command())


def detect_ffmpeg_capabilities(ffmpeg_path: str) -> FfmpegCapabilities:
    resolved = resolve_ffmpeg_path(ffmpeg_path)
    if not resolved:
        return FfmpegCapabilities(
            ffmpeg_path="",
            available=False,
            encoders=frozenset(),
            hwaccels=(),
            demuxers=frozenset(),
            muxers=frozenset(),
            version="",
        )

    version_output = run_ffmpeg_command([resolved, "-version"])
    encoders_output = run_ffmpeg_command([resolved, "-hide_banner", "-encoders"])
    hwaccels_output = run_ffmpeg_command([resolved, "-hide_banner", "-hwaccels"])
    formats_output = run_ffmpeg_command([resolved, "-hide_banner", "-formats"])

    encoders = parse_encoders(encoders_output)
    hwaccels = parse_hwaccels(hwaccels_output)
    demuxers, muxers = parse_formats(formats_output)
    version = version_output.splitlines()[0] if version_output else ""

    return FfmpegCapabilities(
        ffmpeg_path=resolved,
        available=True,
        encoders=frozenset(encoders),
        hwaccels=tuple(hwaccels),
        demuxers=frozenset(demuxers),
        muxers=frozenset(muxers),
        version=version,
    )


def resolve_ffmpeg_path(explicit_path: str) -> str:
    candidates = build_ffmpeg_candidates(explicit_path)
    for candidate in candidates:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            return str(candidate_path)
    return ""


def build_ffmpeg_candidates(explicit_path: str) -> list[str]:
    candidates: list[str] = []
    if explicit_path:
        candidates.append(explicit_path)

    env_path = os.environ.get(ENV_FFMPEG_PATH, "").strip()
    if env_path:
        candidates.append(env_path)

    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        candidates.append(path_ffmpeg)

    candidates.extend(discover_windows_ffmpeg_candidates())
    candidates.extend(DEFAULT_FFMPEG_CANDIDATES)
    return dedupe_candidates(candidates)


def discover_windows_ffmpeg_candidates() -> list[str]:
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_appdata:
        return []

    candidates: list[str] = []
    winget_links = Path(local_appdata) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
    candidates.append(str(winget_links))

    packages_root = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
    if packages_root.exists():
        # 标准 WinGet 安装目录里优先找官方/常见 FFmpeg 包。
        for package_dir in sorted(packages_root.glob("*FFmpeg*")):
            for candidate in (
                package_dir / "ffmpeg.exe",
                package_dir / "bin" / "ffmpeg.exe",
            ):
                candidates.append(str(candidate))
            for nested in sorted(package_dir.glob("**/ffmpeg.exe")):
                candidates.append(str(nested))
    return candidates


def dedupe_candidates(candidates: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def run_ffmpeg_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    return (result.stdout or "") + (result.stderr or "")


def parse_encoders(output: str) -> set[str]:
    encoders: set[str] = set()
    for line in output.splitlines():
        match = re.match(r"^\s*[VAS]\S*\s+([a-z0-9_]+)\s+", line, flags=re.IGNORECASE)
        if match:
            encoders.add(match.group(1))
    return encoders


def parse_hwaccels(output: str) -> list[str]:
    hwaccels: list[str] = []
    seen_header = False
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("hardware acceleration methods"):
            seen_header = True
            continue
        if seen_header:
            hwaccels.append(line)
    return hwaccels


def parse_formats(output: str) -> tuple[set[str], set[str]]:
    demuxers: set[str] = set()
    muxers: set[str] = set()
    for line in output.splitlines():
        match = re.match(
            r"^\s([D ])([E ])\s+([a-z0-9_,]+)\s+",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        can_demux, can_mux, raw_names = match.groups()
        names = [name.strip().lower() for name in raw_names.split(",") if name.strip()]
        if can_demux.upper() == "D":
            demuxers.update(names)
        if can_mux.upper() == "E":
            muxers.update(names)
    return demuxers, muxers


def select_encoder(
    encoder_config: EncoderConfig,
    capabilities: FfmpegCapabilities,
) -> EncoderSelection:
    if not capabilities.available:
        return EncoderSelection(
            backend="none",
            ffmpeg_encoder="",
            codec=encoder_config.codec,
            available=False,
            reason="ffmpeg unavailable",
        )

    requested = encoder_config.backend.lower()
    if requested != "auto":
        ffmpeg_encoder = BACKEND_TO_ENCODER.get(requested, requested)
        if ffmpeg_encoder in capabilities.encoders:
            return EncoderSelection(
                backend=requested,
                ffmpeg_encoder=ffmpeg_encoder,
                codec=encoder_config.codec,
                available=True,
                reason="requested backend available",
            )
        return EncoderSelection(
            backend=requested,
            ffmpeg_encoder=ffmpeg_encoder,
            codec=encoder_config.codec,
            available=False,
            reason="requested backend unavailable",
        )

    for backend in BACKEND_PRIORITY:
        ffmpeg_encoder = BACKEND_TO_ENCODER[backend]
        if ffmpeg_encoder in capabilities.encoders:
            return EncoderSelection(
                backend=backend,
                ffmpeg_encoder=ffmpeg_encoder,
                codec=encoder_config.codec,
                available=True,
                reason="selected by priority chain",
            )

    return EncoderSelection(
        backend="none",
        ffmpeg_encoder="",
        codec=encoder_config.codec,
        available=False,
        reason="no supported encoder found",
    )


def build_selection_candidates(
    encoder_config: EncoderConfig,
    capabilities: FfmpegCapabilities,
) -> list[EncoderSelection]:
    requested = encoder_config.backend.lower()
    if not capabilities.available:
        return [
            EncoderSelection(
                backend="none",
                ffmpeg_encoder="",
                codec=encoder_config.codec,
                available=False,
                reason="ffmpeg unavailable",
            )
        ]

    if requested != "auto":
        return [select_encoder(encoder_config, capabilities)]

    candidates: list[EncoderSelection] = []
    for backend in BACKEND_PRIORITY:
        ffmpeg_encoder = BACKEND_TO_ENCODER[backend]
        if ffmpeg_encoder in capabilities.encoders:
            candidates.append(
                EncoderSelection(
                    backend=backend,
                    ffmpeg_encoder=ffmpeg_encoder,
                    codec=encoder_config.codec,
                    available=True,
                    reason="selected by priority chain",
                )
            )
    if candidates:
        return candidates

    return [
        EncoderSelection(
            backend="none",
            ffmpeg_encoder="",
            codec=encoder_config.codec,
            available=False,
            reason="no supported encoder found",
        )
    ]


def evaluate_pipeline_support(
    selection: EncoderSelection,
    capabilities: FfmpegCapabilities,
) -> FfmpegPipelineSupport:
    if not capabilities.available:
        return FfmpegPipelineSupport(
            ready=False,
            reason="ffmpeg unavailable",
            missing_demuxers=(),
            missing_muxers=(),
        )
    if not selection.available:
        return FfmpegPipelineSupport(
            ready=False,
            reason=selection.reason,
            missing_demuxers=(),
            missing_muxers=(),
        )

    required_demuxers = ("rawvideo",)
    required_muxers = ("null",)
    missing_demuxers = tuple(
        name for name in required_demuxers if name not in capabilities.demuxers
    )
    missing_muxers = tuple(name for name in required_muxers if name not in capabilities.muxers)
    if missing_demuxers or missing_muxers:
        details: list[str] = []
        if missing_demuxers:
            details.append(f"missing demuxers: {', '.join(missing_demuxers)}")
        if missing_muxers:
            details.append(f"missing muxers: {', '.join(missing_muxers)}")
        return FfmpegPipelineSupport(
            ready=False,
            reason=f"ffmpeg rawvideo pipeline unavailable ({'; '.join(details)})",
            missing_demuxers=missing_demuxers,
            missing_muxers=missing_muxers,
        )

    return FfmpegPipelineSupport(
        ready=True,
        reason="ffmpeg rawvideo pipeline ready",
        missing_demuxers=(),
        missing_muxers=(),
    )


def resolve_working_selection(
    encoder_config: EncoderConfig,
    stream_config: StreamConfig,
    capabilities: FfmpegCapabilities,
) -> tuple[EncoderSelection, tuple[EncoderProbeResult, ...]]:
    candidates = build_selection_candidates(encoder_config, capabilities)
    probe_results: list[EncoderProbeResult] = []
    requested = encoder_config.backend.lower()

    for index, candidate in enumerate(candidates):
        if not candidate.available:
            probe_results.append(
                EncoderProbeResult(
                    backend=candidate.backend,
                    ffmpeg_encoder=candidate.ffmpeg_encoder,
                    success=False,
                    reason=candidate.reason,
                )
            )
            continue

        pipeline_support = evaluate_pipeline_support(candidate, capabilities)
        if not pipeline_support.ready:
            probe_results.append(
                EncoderProbeResult(
                    backend=candidate.backend,
                    ffmpeg_encoder=candidate.ffmpeg_encoder,
                    success=False,
                    reason=pipeline_support.reason,
                )
            )
            continue

        probe_result = probe_encoder_backend(
            candidate,
            encoder_config,
            stream_config,
            capabilities.ffmpeg_path,
        )
        probe_results.append(probe_result)
        if probe_result.success:
            if requested == "auto" and index > 0:
                candidate = EncoderSelection(
                    backend=candidate.backend,
                    ffmpeg_encoder=candidate.ffmpeg_encoder,
                    codec=candidate.codec,
                    available=True,
                    reason="selected by runtime probe fallback",
                )
            return candidate, tuple(probe_results)

    if requested != "auto" and candidates:
        failed = candidates[0]
        final_reason = probe_results[-1].reason if probe_results else failed.reason
        return (
            EncoderSelection(
                backend=failed.backend,
                ffmpeg_encoder=failed.ffmpeg_encoder,
                codec=failed.codec,
                available=False,
                reason=final_reason,
            ),
            tuple(probe_results),
        )

    final_reason = (
        probe_results[-1].reason if probe_results else "no supported encoder found"
    )
    return (
        EncoderSelection(
            backend="none",
            ffmpeg_encoder="",
            codec=encoder_config.codec,
            available=False,
            reason=final_reason,
        ),
        tuple(probe_results),
    )


def ensure_pipeline_ready(pipeline_support: FfmpegPipelineSupport) -> None:
    if not pipeline_support.ready:
        raise FfmpegPipelineError(pipeline_support.reason)


def probe_encoder_backend(
    selection: EncoderSelection,
    encoder_config: EncoderConfig,
    stream_config: StreamConfig,
    ffmpeg_path: str,
    *,
    timeout: float = 8.0,
) -> EncoderProbeResult:
    try:
        command = build_ffmpeg_command(
            selection,
            encoder_config,
            stream_config,
            ffmpeg_path,
        )
    except RuntimeError as exc:
        return EncoderProbeResult(
            backend=selection.backend,
            ffmpeg_encoder=selection.ffmpeg_encoder,
            success=False,
            reason=str(exc),
        )

    frame = np.zeros((stream_config.height, stream_config.width, 3), dtype=np.uint8)
    try:
        result = subprocess.run(
            command,
            input=frame.tobytes(),
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return EncoderProbeResult(
            backend=selection.backend,
            ffmpeg_encoder=selection.ffmpeg_encoder,
            success=False,
            reason="encoder startup probe timed out",
        )
    except OSError as exc:
        return EncoderProbeResult(
            backend=selection.backend,
            ffmpeg_encoder=selection.ffmpeg_encoder,
            success=False,
            reason=f"encoder startup probe failed: {exc}",
        )

    stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
    if result.returncode == 0:
        return EncoderProbeResult(
            backend=selection.backend,
            ffmpeg_encoder=selection.ffmpeg_encoder,
            success=True,
            reason="encoder startup probe passed",
        )

    return EncoderProbeResult(
        backend=selection.backend,
        ffmpeg_encoder=selection.ffmpeg_encoder,
        success=False,
        reason=stderr_text or f"encoder startup probe failed with code {result.returncode}",
    )


def build_ffmpeg_command(
    selection: EncoderSelection,
    encoder_config: EncoderConfig,
    stream_config: StreamConfig,
    ffmpeg_path: str,
) -> list[str]:
    if not selection.available or not ffmpeg_path:
        raise RuntimeError("ffmpeg encoder is not available")

    command = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{stream_config.width}x{stream_config.height}",
        "-r",
        str(stream_config.fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        selection.ffmpeg_encoder,
        "-b:v",
        encoder_config.bitrate,
        "-bf",
        "0",
        "-g",
        str(stream_config.fps * 2),
    ]

    command.extend(
        build_backend_encoder_args(
            selection.backend,
            encoder_config,
        )
    )

    command.extend(
        [
            "-f",
            "null",
            "-",
        ]
    )
    return command


def build_backend_encoder_args(
    backend: str,
    encoder_config: EncoderConfig,
) -> list[str]:
    if backend == "libx264":
        return [
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
        ]

    if backend == "nvenc":
        return [
            "-preset",
            encoder_config.preset,
            "-tune",
            "ll",
            "-rc",
            "cbr",
            "-delay",
            "0",
            "-refs",
            "1",
        ]

    if backend == "amf":
        return [
            "-usage",
            "ultralowlatency",
            "-preset",
            LOW_LATENCY_PRESET_MAP["amf"],
            "-quality",
            "speed",
            "-rc",
            "cbr",
            "-latency",
            "1",
        ]

    if backend == "qsv":
        return [
            "-preset",
            LOW_LATENCY_PRESET_MAP["qsv"],
            "-scenario",
            "displayremoting",
            "-low_power",
            "1",
            "-async_depth",
            "1",
        ]

    return [
        "-preset",
        encoder_config.preset,
    ]


class FfmpegEncodeRunner:
    def __init__(self, command: list[str]) -> None:
        self._command = command
        self._process: subprocess.Popen[bytes] | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stderr_lines: list[str] = []
        self._frames_written = 0

    @property
    def command(self) -> list[str]:
        return list(self._command)

    @property
    def stderr_output(self) -> str:
        return "".join(self._stderr_lines)

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("ffmpeg runner already started")
        self._process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def write_frame(self, frame: np.ndarray) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("ffmpeg runner is not started")
        if frame.dtype != np.uint8:
            raise ValueError("frame must be uint8")
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("frame must be HxWx3")
        if self._process.poll() is not None:
            raise RuntimeError("ffmpeg runner already exited")
        try:
            self._process.stdin.write(frame.tobytes())
        except BrokenPipeError as exc:
            raise self._build_process_error("ffmpeg stdin broken pipe") from exc
        self._frames_written += 1

    def finish(self, timeout: float = 10.0) -> int:
        if self._process is None:
            raise RuntimeError("ffmpeg runner is not started")
        if self._process.stdin is not None:
            try:
                self._process.stdin.flush()
            except BrokenPipeError as exc:
                raise self._build_process_error("ffmpeg stdin flush failed") from exc
            self._process.stdin.close()
        return_code = self._process.wait(timeout=timeout)
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=timeout)
        return return_code

    def run_frames(self, frames: list[np.ndarray]) -> EncodingStats:
        started_at = datetime.now(UTC)
        started_perf = time.perf_counter()
        self.start()
        try:
            for frame in frames:
                self.write_frame(frame)
            return_code = self.finish()
        finally:
            ended_at = datetime.now(UTC)
        elapsed_seconds = max(time.perf_counter() - started_perf, 1e-9)
        return EncodingStats(
            started_at=started_at,
            ended_at=ended_at,
            frames_written=self._frames_written,
            elapsed_seconds=elapsed_seconds,
            average_fps=self._frames_written / elapsed_seconds,
            return_code=return_code,
        )

    def _drain_stderr(self) -> None:
        if self._process is None or self._process.stderr is None:
            return
        while True:
            chunk = self._process.stderr.readline()
            if not chunk:
                break
            self._stderr_lines.append(chunk.decode("utf-8", errors="replace"))

    def _build_process_error(self, prefix: str) -> FfmpegProcessError:
        if self._process is None:
            return FfmpegProcessError(prefix)

        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=1.0)

        return_code = self._process.poll()
        stderr_text = self.stderr_output.strip()
        details = [prefix]
        if return_code is not None:
            details.append(f"return_code={return_code}")
        if stderr_text:
            details.append(f"stderr={stderr_text}")
        details.append(f"command={' '.join(self._command)}")
        return FfmpegProcessError("; ".join(details))
