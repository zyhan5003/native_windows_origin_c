from __future__ import annotations

from screen_windows.config import EncoderConfig, StreamConfig
from screen_windows.encoder import (
    EncoderManager,
    EncoderProbeResult,
    EncoderSelection,
    FfmpegCapabilities,
    FfmpegEncodeRunner,
    FfmpegPipelineError,
    ENV_FFMPEG_PATH,
    build_ffmpeg_candidates,
    dedupe_candidates,
    discover_windows_ffmpeg_candidates,
    build_selection_candidates,
    evaluate_pipeline_support,
    build_backend_encoder_args,
    probe_encoder_backend,
    resolve_working_selection,
    build_ffmpeg_command,
    parse_encoders,
    parse_formats,
    parse_hwaccels,
    resolve_ffmpeg_path,
    select_encoder,
)


def test_parse_encoders_extracts_encoder_names() -> None:
    output = """
Encoders:
 V....D h264_nvenc           NVIDIA NVENC H.264 encoder
 V....D libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
"""

    encoders = parse_encoders(output)

    assert "h264_nvenc" in encoders
    assert "libx264" in encoders


def test_parse_hwaccels_extracts_methods() -> None:
    output = """
Hardware acceleration methods:
cuda
qsv
"""

    hwaccels = parse_hwaccels(output)

    assert hwaccels == ["cuda", "qsv"]


def test_parse_formats_extracts_demuxers_and_muxers() -> None:
    output = """
File formats:
 D  matroska,webm    Matroska / WebM
 DE rawvideo         raw video
  E null             raw null video
"""

    demuxers, muxers = parse_formats(output)

    assert "matroska" in demuxers
    assert "webm" in demuxers
    assert "rawvideo" in demuxers
    assert "rawvideo" in muxers
    assert "null" in muxers


def test_dedupe_candidates_preserves_order() -> None:
    candidates = dedupe_candidates(
        [
            "C:/ffmpeg/bin/ffmpeg.exe",
            "c:/ffmpeg/bin/ffmpeg.exe",
            "D:/tools/ffmpeg.exe",
        ]
    )

    assert candidates == [
        "C:/ffmpeg/bin/ffmpeg.exe",
        "D:/tools/ffmpeg.exe",
    ]


def test_build_ffmpeg_candidates_prefers_explicit_env_and_path(monkeypatch) -> None:
    from screen_windows import encoder as module

    monkeypatch.setenv(ENV_FFMPEG_PATH, "D:/env/ffmpeg.exe")
    monkeypatch.setattr(module.shutil, "which", lambda name: "E:/path/ffmpeg.exe")
    monkeypatch.setattr(
        module,
        "discover_windows_ffmpeg_candidates",
        lambda: ["F:/winget/ffmpeg.exe"],
    )

    candidates = build_ffmpeg_candidates("C:/explicit/ffmpeg.exe")

    assert candidates[:4] == [
        "C:/explicit/ffmpeg.exe",
        "D:/env/ffmpeg.exe",
        "E:/path/ffmpeg.exe",
        "F:/winget/ffmpeg.exe",
    ]


def test_resolve_ffmpeg_path_uses_env_before_internal_candidates(monkeypatch) -> None:
    from screen_windows import encoder as module

    monkeypatch.setenv(ENV_FFMPEG_PATH, "C:/env/ffmpeg.exe")
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    monkeypatch.setattr(module, "discover_windows_ffmpeg_candidates", lambda: [])
    monkeypatch.setattr(
        module.Path,
        "exists",
        lambda path_self: str(path_self).replace("\\", "/").lower()
        == "c:/env/ffmpeg.exe",
    )

    resolved = resolve_ffmpeg_path("")

    assert resolved.replace("\\", "/").lower() == "c:/env/ffmpeg.exe"


def test_discover_windows_ffmpeg_candidates_uses_winget_roots(monkeypatch, tmp_path) -> None:
    local_appdata = tmp_path / "LocalAppData"
    links_dir = local_appdata / "Microsoft" / "WinGet" / "Links"
    packages_dir = local_appdata / "Microsoft" / "WinGet" / "Packages"
    links_dir.mkdir(parents=True)
    package_root = packages_dir / "Gyan.FFmpeg.Essentials_test"
    (package_root / "bin").mkdir(parents=True)
    (package_root / "bin" / "ffmpeg.exe").write_bytes(b"")

    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    candidates = discover_windows_ffmpeg_candidates()
    normalized = [candidate.replace("\\", "/") for candidate in candidates]

    assert any(candidate.endswith("/Microsoft/WinGet/Links/ffmpeg.exe") for candidate in normalized)
    assert any(candidate.endswith("/Gyan.FFmpeg.Essentials_test/bin/ffmpeg.exe") for candidate in normalized)


def test_select_encoder_uses_priority_chain() -> None:
    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264", "h264_nvenc"}),
        hwaccels=("cuda",),
        demuxers=frozenset({"rawvideo"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 6.1.1",
    )

    selection = select_encoder(EncoderConfig(backend="auto"), capabilities)

    assert selection.backend == "nvenc"
    assert selection.ffmpeg_encoder == "h264_nvenc"
    assert selection.available is True


def test_build_selection_candidates_returns_priority_chain() -> None:
    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264", "h264_nvenc", "h264_qsv"}),
        hwaccels=("cuda", "qsv"),
        demuxers=frozenset({"rawvideo"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 6.1.1",
    )

    candidates = build_selection_candidates(EncoderConfig(backend="auto"), capabilities)

    assert [candidate.backend for candidate in candidates] == ["nvenc", "qsv", "libx264"]


def test_select_encoder_reports_unavailable_requested_backend() -> None:
    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264"}),
        hwaccels=(),
        demuxers=frozenset({"rawvideo"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 6.1.1",
    )

    selection = select_encoder(EncoderConfig(backend="nvenc"), capabilities)

    assert selection.backend == "nvenc"
    assert selection.available is False


def test_build_ffmpeg_command_for_libx264() -> None:
    command = build_ffmpeg_command(
        EncoderSelection(
            backend="libx264",
            ffmpeg_encoder="libx264",
            codec="h264",
            available=True,
            reason="selected by priority chain",
        ),
        EncoderConfig(backend="auto", bitrate="8M"),
        StreamConfig(width=1280, height=720, fps=24),
        "ffmpeg.exe",
    )

    assert command[:2] == ["ffmpeg.exe", "-hide_banner"]
    assert "libx264" in command
    assert "ultrafast" in command
    assert "zerolatency" in command


def test_build_backend_encoder_args_for_amf_and_qsv() -> None:
    amf_args = build_backend_encoder_args("amf", EncoderConfig(preset="p1"))
    qsv_args = build_backend_encoder_args("qsv", EncoderConfig(preset="p1"))

    assert amf_args == [
        "-usage",
        "ultralowlatency",
        "-preset",
        "speed",
        "-quality",
        "speed",
        "-rc",
        "cbr",
        "-latency",
        "1",
    ]
    assert qsv_args == [
        "-preset",
        "veryfast",
        "-scenario",
        "displayremoting",
        "-low_power",
        "1",
        "-async_depth",
        "1",
    ]


def test_encoder_manager_uses_detected_ffmpeg(monkeypatch) -> None:
    from screen_windows import encoder as module

    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264"}),
        hwaccels=(),
        demuxers=frozenset({"rawvideo"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 6.1.1",
    )

    monkeypatch.setattr(module, "detect_ffmpeg_capabilities", lambda _: capabilities)
    monkeypatch.setattr(
        module,
        "probe_encoder_backend",
        lambda selection, encoder_config, stream_config, ffmpeg_path: EncoderProbeResult(
            backend=selection.backend,
            ffmpeg_encoder=selection.ffmpeg_encoder,
            success=True,
            reason="encoder startup probe passed",
        ),
    )

    manager = EncoderManager(EncoderConfig(backend="auto"), StreamConfig())

    assert manager.selection.backend == "libx264"
    assert manager.capabilities.available is True
    assert manager.pipeline_support.ready is True


def test_resolve_working_selection_falls_back_after_probe_failure(monkeypatch) -> None:
    from screen_windows import encoder as module

    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264", "h264_nvenc"}),
        hwaccels=("cuda",),
        demuxers=frozenset({"rawvideo"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 8.1.1",
    )

    def fake_probe(selection, encoder_config, stream_config, ffmpeg_path):
        if selection.backend == "nvenc":
            return EncoderProbeResult(
                backend="nvenc",
                ffmpeg_encoder="h264_nvenc",
                success=False,
                reason="Cannot load nvcuda.dll",
            )
        return EncoderProbeResult(
            backend=selection.backend,
            ffmpeg_encoder=selection.ffmpeg_encoder,
            success=True,
            reason="encoder startup probe passed",
        )

    monkeypatch.setattr(module, "probe_encoder_backend", fake_probe)

    selection, probe_results = resolve_working_selection(
        EncoderConfig(backend="auto"),
        StreamConfig(width=640, height=360, fps=24),
        capabilities,
    )

    assert selection.backend == "libx264"
    assert selection.reason == "selected by runtime probe fallback"
    assert [result.backend for result in probe_results] == ["nvenc", "libx264"]
    assert probe_results[0].success is False
    assert probe_results[1].success is True


def test_resolve_working_selection_preserves_requested_backend_failure(monkeypatch) -> None:
    from screen_windows import encoder as module

    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264", "h264_nvenc"}),
        hwaccels=("cuda",),
        demuxers=frozenset({"rawvideo"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 8.1.1",
    )

    monkeypatch.setattr(
        module,
        "probe_encoder_backend",
        lambda selection, encoder_config, stream_config, ffmpeg_path: EncoderProbeResult(
            backend=selection.backend,
            ffmpeg_encoder=selection.ffmpeg_encoder,
            success=False,
            reason="Cannot load nvcuda.dll",
        ),
    )

    selection, probe_results = resolve_working_selection(
        EncoderConfig(backend="nvenc"),
        StreamConfig(width=640, height=360, fps=24),
        capabilities,
    )

    assert selection.backend == "nvenc"
    assert selection.available is False
    assert "Cannot load nvcuda.dll" in selection.reason
    assert len(probe_results) == 1


def test_evaluate_pipeline_support_reports_missing_rawvideo() -> None:
    selection = EncoderSelection(
        backend="libx264",
        ffmpeg_encoder="libx264",
        codec="h264",
        available=True,
        reason="selected by priority chain",
    )
    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264"}),
        hwaccels=(),
        demuxers=frozenset({"matroska"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 6.1.1",
    )

    support = evaluate_pipeline_support(selection, capabilities)

    assert support.ready is False
    assert support.missing_demuxers == ("rawvideo",)
    assert "rawvideo pipeline unavailable" in support.reason


def test_encoder_manager_build_command_requires_pipeline_ready(monkeypatch) -> None:
    from screen_windows import encoder as module

    capabilities = FfmpegCapabilities(
        ffmpeg_path="ffmpeg.exe",
        available=True,
        encoders=frozenset({"libx264"}),
        hwaccels=(),
        demuxers=frozenset({"matroska"}),
        muxers=frozenset({"null"}),
        version="ffmpeg version 6.1.1",
    )

    monkeypatch.setattr(module, "detect_ffmpeg_capabilities", lambda _: capabilities)

    manager = EncoderManager(EncoderConfig(backend="auto"), StreamConfig())

    try:
        manager.build_command()
    except FfmpegPipelineError as exc:
        assert "missing demuxers: rawvideo" in str(exc)
    else:
        raise AssertionError("build_command should reject unavailable rawvideo pipeline")


def test_probe_encoder_backend_reports_timeout(monkeypatch) -> None:
    from screen_windows import encoder as module

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            module.subprocess.TimeoutExpired(cmd="ffmpeg", timeout=8.0)
        ),
    )

    result = probe_encoder_backend(
        EncoderSelection(
            backend="libx264",
            ffmpeg_encoder="libx264",
            codec="h264",
            available=True,
            reason="selected by priority chain",
        ),
        EncoderConfig(),
        StreamConfig(width=320, height=180, fps=24),
        "ffmpeg.exe",
    )

    assert result.success is False
    assert result.reason == "encoder startup probe timed out"


def test_ffmpeg_encode_runner_rejects_invalid_frame_shape() -> None:
    runner = FfmpegEncodeRunner(["ffmpeg.exe"])

    try:
        runner.write_frame.__wrapped__  # type: ignore[attr-defined]
    except AttributeError:
        pass

    try:
        runner.write_frame(None)  # type: ignore[arg-type]
    except RuntimeError:
        pass
    else:
        raise AssertionError("runner should require start before write")
