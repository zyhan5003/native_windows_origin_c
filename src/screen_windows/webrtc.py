from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import cv2
import numpy as np

from .quality import QualityProfile, QualitySignal
from .video_source import FrameSource


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VideoTrackStats:
    frames_sent: int
    target_profile: str
    target_fps: int
    target_bitrate_mbps: float
    last_width: int
    last_height: int
    capture_ms: float
    resize_ms: float
    motion_ratio: float
    measured_fps: float
    running_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames_sent": self.frames_sent,
            "target_profile": self.target_profile,
            "target_fps": self.target_fps,
            "target_bitrate_mbps": self.target_bitrate_mbps,
            "last_width": self.last_width,
            "last_height": self.last_height,
            "capture_ms": self.capture_ms,
            "resize_ms": self.resize_ms,
            "motion_ratio": self.motion_ratio,
            "measured_fps": self.measured_fps,
            "running_seconds": self.running_seconds,
        }


class SourceVideoTrack(VideoStreamTrack):
    """把可替换视频源包装成 aiortc VideoTrack。"""

    def __init__(
        self,
        source: FrameSource,
        *,
        quality_profile_provider: Callable[[], QualityProfile] | None = None,
        quality_signal_callback: Callable[[QualitySignal], None] | None = None,
    ) -> None:
        super().__init__()
        self._source = source
        self._quality_profile_provider = quality_profile_provider
        self._quality_signal_callback = quality_signal_callback
        self._frame_index = 0
        self._started_at: float | None = None
        self._last_frame_at: float | None = None
        self._last_width = 0
        self._last_height = 0
        self._last_profile_key = "standard"
        self._last_target_fps = 0
        self._last_target_bitrate_mbps = 0.0
        self._last_capture_ms = 0.0
        self._last_resize_ms = 0.0
        self._last_motion_ratio = 0.0
        self._previous_motion_sample: np.ndarray | None = None

    @property
    def stats(self) -> VideoTrackStats:
        now = time.perf_counter()
        running_seconds = 0.0 if self._started_at is None else max(now - self._started_at, 0.0)
        measured_fps = self._frame_index / running_seconds if running_seconds > 0 else 0.0
        return VideoTrackStats(
            frames_sent=self._frame_index,
            target_profile=self._last_profile_key,
            target_fps=self._last_target_fps,
            target_bitrate_mbps=self._last_target_bitrate_mbps,
            last_width=self._last_width,
            last_height=self._last_height,
            capture_ms=self._last_capture_ms,
            resize_ms=self._last_resize_ms,
            motion_ratio=self._last_motion_ratio,
            measured_fps=round(measured_fps, 2),
            running_seconds=round(running_seconds, 2),
        )

    async def recv(self) -> VideoFrame:
        target = self._target_profile()
        self._last_profile_key = target.key
        self._last_target_fps = target.fps
        self._last_target_bitrate_mbps = target.bitrate_mbps
        frame_interval = 1 / max(target.fps, 1)
        if self._last_frame_at is not None:
            delay = (self._last_frame_at + frame_interval) - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
        if self._started_at is None:
            self._started_at = time.perf_counter()

        capture_started_at = time.perf_counter()
        frame_data = self._source.render(self._frame_index)
        self._last_capture_ms = round((time.perf_counter() - capture_started_at) * 1000, 3)

        self._last_motion_ratio = self._estimate_motion_ratio(frame_data)
        if self._quality_signal_callback is not None:
            self._quality_signal_callback(QualitySignal(motion_ratio=self._last_motion_ratio))

        resize_started_at = time.perf_counter()
        frame_data = self._resize_for_quality(frame_data, target)
        self._last_resize_ms = round((time.perf_counter() - resize_started_at) * 1000, 3)

        frame = VideoFrame.from_ndarray(frame_data, format="rgb24")
        frame.pts = self._frame_index
        frame.time_base = Fraction(1, max(target.fps, 1))
        self._frame_index += 1
        self._last_frame_at = time.perf_counter()
        self._last_width = frame.width
        self._last_height = frame.height
        return frame

    def _estimate_motion_ratio(self, frame: np.ndarray) -> float:
        sample = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        sample = cv2.cvtColor(sample, cv2.COLOR_RGB2GRAY)
        previous = self._previous_motion_sample
        self._previous_motion_sample = sample
        if previous is None:
            return 0.0
        # 低分辨率差分足够判断画面活跃度，避免给每帧增加明显开销。
        changed = cv2.absdiff(sample, previous) > 15
        return round(float(np.count_nonzero(changed)) / float(changed.size), 4)

    def _target_profile(self) -> QualityProfile:
        if self._quality_profile_provider is None:
            from .quality import QUALITY_PROFILES

            return QUALITY_PROFILES["standard"]
        return self._quality_profile_provider()

    def _resize_for_quality(
        self,
        frame: np.ndarray,
        target: QualityProfile,
    ) -> np.ndarray:
        current_height, current_width = frame.shape[:2]
        # AQE 先只负责降采样保护带宽，避免把低分辨率源强行放大成假 1080p。
        target_width = min(current_width, target.width)
        target_height = min(current_height, target.height)
        if target_width == current_width and target_height == current_height:
            return frame
        return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)


async def wait_for_ice_complete(pc: RTCPeerConnection, timeout: float = 5.0) -> None:
    if pc.iceGatheringState == "complete":
        return

    completed = asyncio.Event()

    @pc.on("icegatheringstatechange")
    def on_ice_gathering_state_change() -> None:
        if pc.iceGatheringState == "complete":
            completed.set()

    await asyncio.wait_for(completed.wait(), timeout=timeout)


class WebRtcSession:
    def __init__(
        self,
        source: FrameSource,
        *,
        quality_profile_provider: Callable[[], QualityProfile] | None = None,
        quality_signal_callback: Callable[[QualitySignal], None] | None = None,
    ) -> None:
        self._source = source
        self._quality_profile_provider = quality_profile_provider
        self._quality_signal_callback = quality_signal_callback
        self._pc = RTCPeerConnection()
        self._video_track: SourceVideoTrack | None = None
        self._closed = False

        @self._pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            if self._pc.connectionState in {"failed", "closed"}:
                await self.close()

    @property
    def peer_connection(self) -> RTCPeerConnection:
        return self._pc

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "connection_state": self._pc.connectionState,
            "video": self._video_track.stats.to_dict()
            if self._video_track is not None
            else None,
        }

    async def create_answer(self, offer_sdp: str, offer_type: str) -> RTCSessionDescription:
        target_profile = self._current_quality_profile()
        self._video_track = SourceVideoTrack(
            self._source,
            quality_profile_provider=self._quality_profile_provider,
            quality_signal_callback=self._quality_signal_callback,
        )
        self._pc.addTrack(self._video_track)
        await self._pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type=offer_type)
        )
        answer = await self._pc.createAnswer()
        answer = RTCSessionDescription(
            sdp=apply_video_bandwidth_to_sdp(answer.sdp, target_profile.bitrate_mbps),
            type=answer.type,
        )
        await self._pc.setLocalDescription(answer)
        await wait_for_ice_complete(self._pc)
        assert self._pc.localDescription is not None
        return self._pc.localDescription

    def _current_quality_profile(self) -> QualityProfile:
        if self._quality_profile_provider is None:
            from .quality import QUALITY_PROFILES

            return QUALITY_PROFILES["standard"]
        return self._quality_profile_provider()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._pc.close()
        except Exception:  # pragma: no cover - 关闭兜底
            LOGGER.exception("failed to close webrtc peer connection")


def apply_video_bandwidth_to_sdp(sdp: str, bitrate_mbps: float) -> str:
    """给 video m-section 写入码率上限，作为 aiortc 内置编码的低延迟约束。"""

    bitrate_kbps = max(int(bitrate_mbps * 1000), 1)
    lines = sdp.splitlines()
    result: list[str] = []
    in_video = False
    inserted = False

    for line in lines:
        if line.startswith("m="):
            if in_video and not inserted:
                result.append(f"b=AS:{bitrate_kbps}")
            in_video = line.startswith("m=video")
            inserted = False
            result.append(line)
            continue

        if in_video and (line.startswith("b=AS:") or line.startswith("b=TIAS:")):
            continue

        result.append(line)
        if in_video and not inserted and line.startswith("c="):
            result.append(f"b=AS:{bitrate_kbps}")
            inserted = True

    if in_video and not inserted:
        result.append(f"b=AS:{bitrate_kbps}")

    return "\r\n".join(result) + "\r\n"
