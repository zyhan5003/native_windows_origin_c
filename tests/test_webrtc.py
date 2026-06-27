from __future__ import annotations

import asyncio

import numpy as np

from screen_windows.media.quality import QUALITY_PROFILES, QualitySignal
from screen_windows.media.video_source import SyntheticFrameSource
from screen_windows.media.webrtc import (
    STATIC_EFFECTIVE_FPS,
    SourceVideoTrack,
    VIDEO_CLOCK_HZ,
    apply_video_bandwidth_to_sdp,
    wait_for_ice_complete,
)


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
