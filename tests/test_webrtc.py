from __future__ import annotations

import asyncio

import av
import numpy as np
from fractions import Fraction
import pytest

from screen_windows.media.quality import QUALITY_PROFILES, QualitySignal
from screen_windows.media.video_source import SyntheticFrameSource
from screen_windows.media.webrtc import (
    STATIC_EFFECTIVE_FPS,
    SourceVideoTrack,
    VIDEO_CLOCK_HZ,
    apply_video_bandwidth_to_sdp,
    prefer_h264_codecs,
    wait_for_ice_complete,
)
from screen_windows.media.encoder import EncoderSelection
from screen_windows.media.webrtc_encoder import RuntimeH264Encoder, WebRtcEncoderRuntime


def test_apply_video_bandwidth_to_sdp_updates_only_video_section() -> None:
    sdp = "\r\n".join(
        [
            "v=0",
            "m=audio 9 UDP/TLS/RTP/SAVPF 111",
            "c=IN IP4 0.0.0.0",
            "b=AS:64",
            "m=video 9 UDP/TLS/RTP/SAVPF 96",
            "c=IN IP4 0.0.0.0",
            "b=AS:500",
            "a=rtpmap:96 H264/90000",
            "",
        ]
    )

    updated = apply_video_bandwidth_to_sdp(sdp, 10.0)

    assert "m=audio 9 UDP/TLS/RTP/SAVPF 111\r\nc=IN IP4 0.0.0.0\r\nb=AS:64" in updated
    assert "m=video 9 UDP/TLS/RTP/SAVPF 96\r\nc=IN IP4 0.0.0.0\r\nb=AS:10000" in updated
    assert "b=AS:500" not in updated


def test_apply_video_bandwidth_to_sdp_inserts_after_late_ice_candidates() -> None:
    sdp = "\r\n".join(
        [
            "v=0",
            "m=video 5052 UDP/TLS/RTP/SAVPF 96",
            "c=IN IP4 192.168.0.10",
            "a=candidate:abc 1 udp 2130706431 192.168.0.10 5052 typ host",
            "a=ice-ufrag:test",
            "a=rtpmap:96 VP8/90000",
            "",
        ]
    )

    updated = apply_video_bandwidth_to_sdp(sdp, 0.5)

    assert "m=video 5052 UDP/TLS/RTP/SAVPF 96\r\nc=IN IP4 192.168.0.10\r\nb=AS:500" in updated


def test_source_video_track_downscales_to_quality_profile() -> None:
    asyncio.run(_test_source_video_track_downscales_to_quality_profile())


async def _test_source_video_track_downscales_to_quality_profile() -> None:
    source = SyntheticFrameSource(width=1920, height=1080, fps=60)
    signals: list[QualitySignal] = []
    track = SourceVideoTrack(
        source,
        quality_profile_provider=lambda: QUALITY_PROFILES["eco"],
        quality_signal_callback=signals.append,
    )

    frame = await track.recv()
    await track.recv()
    stats = track.stats

    assert frame.width == 1280
    assert frame.height == 720
    assert frame.time_base.denominator == VIDEO_CLOCK_HZ
    assert stats.frames_sent == 2
    assert stats.target_profile == "eco"
    assert stats.target_fps == 30
    assert stats.effective_fps == 30
    assert stats.target_bitrate_mbps == 2.0
    assert stats.last_width == 1280
    assert stats.last_height == 720
    assert stats.capture_ms >= 0
    assert stats.resize_ms >= 0
    assert 0 <= stats.motion_ratio <= 1
    assert len(signals) == 2
    assert signals[-1].motion_ratio == stats.motion_ratio


def test_source_video_track_throttles_static_frames() -> None:
    asyncio.run(_test_source_video_track_throttles_static_frames())


async def _test_source_video_track_throttles_static_frames() -> None:
    class StaticFrameSource:
        width = 640
        height = 360
        fps = 60
        source_name = "static-test"

        def render(self, frame_index: int) -> np.ndarray:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    track = SourceVideoTrack(
        StaticFrameSource(),
        quality_profile_provider=lambda: QUALITY_PROFILES["fast"],
    )

    await track.recv()
    await track.recv()
    frame = await track.recv()
    stats = track.stats

    assert frame.time_base.denominator == VIDEO_CLOCK_HZ
    assert stats.target_fps == 60
    assert stats.effective_fps == STATIC_EFFECTIVE_FPS
    assert stats.motion_ratio == 0.0


def test_wait_for_ice_complete_timeout_continues() -> None:
    asyncio.run(_test_wait_for_ice_complete_timeout_continues())


async def _test_wait_for_ice_complete_timeout_continues() -> None:
    class NeverCompletesPeerConnection:
        iceGatheringState = "gathering"

        def on(self, event_name: str):
            assert event_name == "icegatheringstatechange"

            def decorator(callback):
                return callback

            return decorator

    await wait_for_ice_complete(NeverCompletesPeerConnection(), timeout=0.01)  # type: ignore[arg-type]


def test_prefer_h264_codecs_moves_h264_before_vp8() -> None:
    asyncio.run(_test_prefer_h264_codecs_moves_h264_before_vp8())


async def _test_prefer_h264_codecs_moves_h264_before_vp8() -> None:
    from aiortc import RTCPeerConnection

    pc = RTCPeerConnection()
    try:
        pc.addTransceiver("video")
        prefer_h264_codecs(pc)
        codecs = pc.getTransceivers()[0]._preferred_codecs

        assert codecs
        assert codecs[0].mimeType.lower() == "video/h264"
        assert any(codec.mimeType.lower() == "video/vp8" for codec in codecs)
    finally:
        await pc.close()


def test_runtime_h264_encoder_can_use_qsv_when_available() -> None:
    if not _qsv_available_for_pyav():
        pytest.skip("h264_qsv is not available on this machine")

    runtime = WebRtcEncoderRuntime(
        EncoderSelection(
            backend="qsv",
            ffmpeg_encoder="h264_qsv",
            codec="h264",
            available=True,
            reason="test",
        )
    )
    assert runtime.status.active_encoder == "pending"
    assert runtime.status.hardware_active is False

    encoder = RuntimeH264Encoder(runtime)
    frame = _black_video_frame(width=640, height=360)

    payloads, timestamp = encoder.encode(frame)

    assert payloads
    assert timestamp == 0
    assert runtime.status.active_encoder == "h264_qsv"
    assert runtime.status.hardware_active is True


def test_runtime_h264_encoder_falls_back_to_libx264(monkeypatch) -> None:
    import screen_windows.media.webrtc_encoder as module

    runtime = WebRtcEncoderRuntime(
        EncoderSelection(
            backend="qsv",
            ffmpeg_encoder="h264_qsv",
            codec="h264",
            available=True,
            reason="test",
        )
    )
    original_create = module._create_h264_codec

    def flaky_create(encoder_name: str, **kwargs):
        if encoder_name == "h264_qsv":
            raise RuntimeError("qsv unavailable")
        return original_create(encoder_name, **kwargs)

    monkeypatch.setattr(module, "_create_h264_codec", flaky_create)
    encoder = RuntimeH264Encoder(runtime)

    payloads, _ = encoder.encode(_black_video_frame(width=320, height=180))

    assert payloads
    assert runtime.status.active_encoder == "libx264"
    assert runtime.status.hardware_active is False
    assert "qsv unavailable" in runtime.status.fallback_reason


def test_runtime_h264_encoder_keeps_codec_on_bitrate_change(monkeypatch) -> None:
    import screen_windows.media.webrtc_encoder as module

    created: list[object] = []

    class FakeCodec:
        width = 320
        height = 180
        bit_rate = 500_000

        def encode(self, frame):
            return [b"\x00\x00\x00\x01\x65test"]

    def fake_create(encoder_name: str, **kwargs):
        codec = FakeCodec()
        codec.width = kwargs["frame"].width
        codec.height = kwargs["frame"].height
        codec.bit_rate = kwargs["target_bitrate"]
        created.append(codec)
        return codec

    monkeypatch.setattr(module, "_create_h264_codec", fake_create)
    encoder = RuntimeH264Encoder(None)
    encoder.target_bitrate = 500_000

    encoder.encode(_black_video_frame(width=320, height=180))
    encoder.target_bitrate = 1_200_000
    encoder.encode(_black_video_frame(width=320, height=180))
    encoder.encode(_black_video_frame(width=640, height=360))

    assert len(created) == 2
    assert created[0].bit_rate == 1_200_000
    assert created[1].width == 640
    assert created[1].height == 360


def _black_video_frame(*, width: int, height: int) -> av.VideoFrame:
    frame = av.VideoFrame.from_ndarray(
        np.zeros((height, width, 3), dtype=np.uint8),
        format="rgb24",
    )
    frame.pts = 0
    frame.time_base = Fraction(1, 30)
    return frame


def _qsv_available_for_pyav() -> bool:
    runtime = WebRtcEncoderRuntime(
        EncoderSelection(
            backend="qsv",
            ffmpeg_encoder="h264_qsv",
            codec="h264",
            available=True,
            reason="test",
        )
    )
    try:
        RuntimeH264Encoder(runtime).encode(_black_video_frame(width=320, height=180))
    except Exception:
        return False
    return True
