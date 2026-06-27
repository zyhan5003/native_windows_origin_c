from __future__ import annotations

import asyncio

from screen_windows.quality import QUALITY_PROFILES, QualitySignal
from screen_windows.video_source import SyntheticFrameSource
from screen_windows.webrtc import SourceVideoTrack, apply_video_bandwidth_to_sdp


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
    assert frame.time_base.denominator == 30
    assert stats.frames_sent == 2
    assert stats.target_profile == "eco"
    assert stats.target_fps == 30
    assert stats.target_bitrate_mbps == 2.0
    assert stats.last_width == 1280
    assert stats.last_height == 720
    assert stats.capture_ms >= 0
    assert stats.resize_ms >= 0
    assert 0 <= stats.motion_ratio <= 1
    assert len(signals) == 2
    assert signals[-1].motion_ratio == stats.motion_ratio
