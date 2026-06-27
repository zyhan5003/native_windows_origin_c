from __future__ import annotations

from dataclasses import dataclass
import math
from threading import Lock
from typing import Protocol

import cv2
import numpy as np

from ..app.config import StreamConfig

try:
    import dxcam
except ImportError:  # pragma: no cover - 环境依赖分支
    dxcam = None

try:
    from mss import MSS
except ImportError:  # pragma: no cover - 环境依赖分支
    MSS = None


class FrameSource(Protocol):
    """抽象视频源，后续可替换为 FFmpeg 管线。"""

    width: int
    height: int
    fps: int
    source_name: str

    def render(self, frame_index: int) -> np.ndarray:
        """输出 rgb24 帧。"""


@dataclass(slots=True)
class SyntheticFrameSource:
    width: int
    height: int
    fps: int
    source_name: str = "synthetic"

    @classmethod
    def from_config(cls, config: StreamConfig) -> "SyntheticFrameSource":
        return cls(width=config.width, height=config.height, fps=config.fps)

    def render(self, frame_index: int) -> np.ndarray:
        frame = np.empty((self.height, self.width, 3), dtype=np.uint8)
        x = np.linspace(0, 255, self.width, dtype=np.float32)
        y = np.linspace(0, 255, self.height, dtype=np.float32)
        phase = frame_index * 4.0

        frame[..., 0] = np.mod(x[None, :] + phase, 255).astype(np.uint8)
        frame[..., 1] = np.mod(y[:, None] * 0.85 + phase * 0.7, 255).astype(np.uint8)
        frame[..., 2] = np.mod((x[None, :] * 0.35) + (y[:, None] * 0.45) + phase, 255).astype(
            np.uint8
        )

        self._draw_hud(frame, frame_index)
        return frame

    def _draw_hud(self, frame: np.ndarray, frame_index: int) -> None:
        accent = np.array([236, 243, 250], dtype=np.uint8)
        lime = np.array([179, 255, 117], dtype=np.uint8)
        orange = np.array([255, 171, 74], dtype=np.uint8)

        frame[32:148, 36:420] = np.array([14, 23, 31], dtype=np.uint8)
        frame[52:66, 52:180] = accent
        frame[74:86, 52:310] = np.array([52, 78, 102], dtype=np.uint8)
        frame[104:118, 52:240] = lime
        frame[124:136, 52:380] = orange

        orbit_x = 160 + int(120 * math.sin(frame_index / 8))
        orbit_y = 420 + int(90 * math.cos(frame_index / 11))
        frame[max(orbit_y - 36, 0) : orbit_y + 36, max(orbit_x - 36, 0) : orbit_x + 36] = (
            np.array([250, 248, 242], dtype=np.uint8)
        )

        scanline = (frame_index * 6) % max(self.height - 6, 1)
        frame[scanline : scanline + 6, :, :] = np.array([255, 255, 255], dtype=np.uint8)


class DxcamFrameSource:
    source_name = "dxcam"

    def __init__(self, config: StreamConfig) -> None:
        if dxcam is None:
            raise RuntimeError("dxcam is not installed")
        self.width = config.width
        self.height = config.height
        self.fps = config.fps
        self._monitor = config.monitor
        self._lock = Lock()
        self._camera = dxcam.create(output_color="BGR", output_idx=config.monitor)
        self._last_frame: np.ndarray | None = None
        self._last_frame = self._capture_frame()

    def render(self, frame_index: int) -> np.ndarray:
        with self._lock:
            frame = self._capture_frame()
            self._last_frame = frame
        return frame

    def _capture_frame(self) -> np.ndarray:
        frame = self._camera.grab()
        if frame is None:
            if self._last_frame is None:
                raise RuntimeError("dxcam returned no frame")
            frame = self._last_frame

        frame = self._resize_if_needed(frame)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def _resize_if_needed(self, frame: np.ndarray) -> np.ndarray:
        if frame.shape[1] == self.width and frame.shape[0] == self.height:
            return frame
        return cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)


class MssFrameSource:
    source_name = "mss"

    def __init__(self, config: StreamConfig) -> None:
        if MSS is None:
            raise RuntimeError("mss is not installed")
        self.width = config.width
        self.height = config.height
        self.fps = config.fps
        self._monitor = config.monitor
        self._lock = Lock()
        self._mss = MSS()

        monitor_index = config.monitor + 1
        if monitor_index >= len(self._mss.monitors):
            raise RuntimeError(f"mss monitor index out of range: {config.monitor}")
        self._monitor_info = self._mss.monitors[monitor_index]

    def render(self, frame_index: int) -> np.ndarray:
        with self._lock:
            shot = self._mss.grab(self._monitor_info)
        frame = np.array(shot, dtype=np.uint8)[..., :3]
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if frame.shape[1] == self.width and frame.shape[0] == self.height:
            return frame
        return cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)


def build_frame_source(config: StreamConfig) -> FrameSource:
    source = config.source.lower()
    if source == "synthetic":
        return SyntheticFrameSource.from_config(config)
    if source == "dxcam":
        return DxcamFrameSource(config)
    if source == "mss":
        return MssFrameSource(config)
    if source == "auto":
        try:
            return DxcamFrameSource(config)
        except Exception:
            try:
                return MssFrameSource(config)
            except Exception:
                return SyntheticFrameSource.from_config(config)
    raise ValueError(f"unsupported stream source: {config.source}")
