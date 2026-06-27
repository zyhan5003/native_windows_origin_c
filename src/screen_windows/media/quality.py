from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any


PROFILE_ORDER = ("limit", "eco", "standard", "fast", "turbo")
UPGRADE_HOLD_SECONDS = 3.0
DOWNGRADE_HOLD_SECONDS = 1.0


@dataclass(frozen=True, slots=True)
class QualityProfile:
    key: str
    name: str
    fps: int
    width: int
    height: int
    bitrate_mbps: float
    max_rtt_ms: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "bitrate_mbps": self.bitrate_mbps,
            "max_rtt_ms": self.max_rtt_ms,
        }


QUALITY_PROFILES: dict[str, QualityProfile] = {
    "turbo": QualityProfile(
        key="turbo",
        name="极速",
        fps=60,
        width=1920,
        height=1080,
        bitrate_mbps=20.0,
        max_rtt_ms=5.0,
    ),
    "fast": QualityProfile(
        key="fast",
        name="高速",
        fps=60,
        width=1920,
        height=1080,
        bitrate_mbps=10.0,
        max_rtt_ms=10.0,
    ),
    "standard": QualityProfile(
        key="standard",
        name="标准",
        fps=30,
        width=1920,
        height=1080,
        bitrate_mbps=5.0,
        max_rtt_ms=30.0,
    ),
    "eco": QualityProfile(
        key="eco",
        name="节能",
        fps=24,
        width=1280,
        height=720,
        bitrate_mbps=2.0,
        max_rtt_ms=50.0,
    ),
    "limit": QualityProfile(
        key="limit",
        name="极限",
        fps=15,
        width=1280,
        height=720,
        bitrate_mbps=0.5,
        max_rtt_ms=None,
    ),
}


@dataclass(frozen=True, slots=True)
class QualitySignal:
    rtt_ms: float | None = None
    packet_loss: float | None = None
    bandwidth_mbps: float | None = None
    motion_ratio: float | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "QualitySignal":
        raw = payload or {}
        return cls(
            rtt_ms=_optional_float(raw.get("rtt_ms")),
            packet_loss=_optional_float(raw.get("packet_loss")),
            bandwidth_mbps=_optional_float(raw.get("bandwidth_mbps")),
            motion_ratio=_optional_float(raw.get("motion_ratio")),
        )

    def to_dict(self) -> dict[str, float]:
        result: dict[str, float] = {}
        if self.rtt_ms is not None:
            result["rtt_ms"] = self.rtt_ms
        if self.packet_loss is not None:
            result["packet_loss"] = self.packet_loss
        if self.bandwidth_mbps is not None:
            result["bandwidth_mbps"] = self.bandwidth_mbps
        if self.motion_ratio is not None:
            result["motion_ratio"] = self.motion_ratio
        return result


@dataclass(frozen=True, slots=True)
class QualityState:
    mode: str
    profile: QualityProfile
    pending_profile: QualityProfile | None
    last_signal: QualitySignal | None
    locked: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "profile": self.profile.to_dict(),
            "pending_profile": self.pending_profile.to_dict()
            if self.pending_profile is not None
            else None,
            "last_signal": self.last_signal.to_dict()
            if self.last_signal is not None
            else None,
            "locked": self.locked,
            "profiles": [QUALITY_PROFILES[key].to_dict() for key in PROFILE_ORDER],
        }


class QualityController:
    def __init__(self, *, mode: str = "auto", profile: str = "standard") -> None:
        self._mode = _normalize_mode(mode)
        self._profile = _get_profile(profile)
        self._pending_profile: QualityProfile | None = None
        self._pending_since: float | None = None
        self._last_signal: QualitySignal | None = None

    @property
    def state(self) -> QualityState:
        return QualityState(
            mode=self._mode,
            profile=self._profile,
            pending_profile=self._pending_profile,
            last_signal=self._last_signal,
            locked=self._mode == "manual",
        )

    def set_manual(
        self,
        profile: str,
        *,
        width: Any | None = None,
        height: Any | None = None,
        fps: Any | None = None,
        bitrate_mbps: Any | None = None,
    ) -> QualityState:
        self._mode = "manual"
        self._profile = _manual_profile(
            profile,
            width=width,
            height=height,
            fps=fps,
            bitrate_mbps=bitrate_mbps,
        )
        self._clear_pending()
        return self.state

    def set_auto(self, signal: QualitySignal | None = None, *, now: float | None = None) -> QualityState:
        self._mode = "auto"
        if signal is None:
            self._clear_pending()
            return self.state
        return self.update(signal, now=now)

    def update(self, signal: QualitySignal, *, now: float | None = None) -> QualityState:
        current_time = time.monotonic() if now is None else now
        self._last_signal = self._merge_signal(signal)
        if self._mode == "manual":
            return self.state

        desired = self.choose_profile(self._last_signal)
        if desired.key == self._profile.key:
            self._clear_pending()
            return self.state

        # 升档慢、降档快：抵抗瞬时好转，但网络变差时快速保护体验。
        if self._pending_profile is None or self._pending_profile.key != desired.key:
            self._pending_profile = desired
            self._pending_since = current_time
            return self.state

        hold_seconds = self._required_hold_seconds(desired)
        if self._pending_since is not None and current_time - self._pending_since >= hold_seconds:
            self._profile = desired
            self._clear_pending()

        return self.state

    def _merge_signal(self, signal: QualitySignal) -> QualitySignal:
        if self._last_signal is None:
            return signal
        return QualitySignal(
            rtt_ms=signal.rtt_ms
            if signal.rtt_ms is not None
            else self._last_signal.rtt_ms,
            packet_loss=signal.packet_loss
            if signal.packet_loss is not None
            else self._last_signal.packet_loss,
            bandwidth_mbps=signal.bandwidth_mbps
            if signal.bandwidth_mbps is not None
            else self._last_signal.bandwidth_mbps,
            motion_ratio=signal.motion_ratio
            if signal.motion_ratio is not None
            else self._last_signal.motion_ratio,
        )

    def choose_profile(self, signal: QualitySignal) -> QualityProfile:
        rtt = signal.rtt_ms if signal.rtt_ms is not None else 30.0
        loss = signal.packet_loss if signal.packet_loss is not None else 0.0
        bandwidth = signal.bandwidth_mbps if signal.bandwidth_mbps is not None else math.inf
        motion = signal.motion_ratio if signal.motion_ratio is not None else 0.0

        if loss >= 5.0 or rtt > 50.0:
            return QUALITY_PROFILES["limit"]
        if rtt < 5.0 and bandwidth >= 15.0 and motion >= 0.35:
            return QUALITY_PROFILES["turbo"]
        if rtt < 10.0 and bandwidth >= 8.0:
            return QUALITY_PROFILES["fast"]
        if rtt < 30.0 and bandwidth >= 4.0:
            return QUALITY_PROFILES["standard"]
        if rtt < 30.0:
            # 浏览器可用带宽估计在静态画面会偏低，低 RTT/零丢包时不单独降级。
            return QUALITY_PROFILES["standard"]
        if rtt < 50.0 and bandwidth >= 1.5:
            return QUALITY_PROFILES["eco"]
        if rtt < 50.0:
            return QUALITY_PROFILES["eco"]
        return QUALITY_PROFILES["limit"]

    def _required_hold_seconds(self, desired: QualityProfile) -> float:
        desired_index = _profile_rank(desired.key)
        current_index = _profile_rank(self._profile.key)
        if desired_index > current_index:
            return UPGRADE_HOLD_SECONDS
        return DOWNGRADE_HOLD_SECONDS

    def _clear_pending(self) -> None:
        self._pending_profile = None
        self._pending_since = None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _normalize_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in {"auto", "manual"}:
        raise ValueError("quality mode must be auto or manual")
    return mode


def _get_profile(key: str) -> QualityProfile:
    profile_key = key.strip().lower()
    if profile_key not in QUALITY_PROFILES:
        raise ValueError(f"unknown quality profile: {key}")
    return QUALITY_PROFILES[profile_key]


def _profile_rank(key: str) -> int:
    if key in PROFILE_ORDER:
        return PROFILE_ORDER.index(key)
    return PROFILE_ORDER.index("standard")


def _manual_profile(
    profile: str,
    *,
    width: Any | None,
    height: Any | None,
    fps: Any | None,
    bitrate_mbps: Any | None,
) -> QualityProfile:
    base = _get_profile(profile)
    if width is None and height is None and fps is None and bitrate_mbps is None:
        return base

    # 手动档允许用户直接选择分辨率/FPS/码率，Track 和 SDP 会使用这些值。
    custom_width = _bounded_int(width if width is not None else base.width, "width", 320, 3840)
    custom_height = _bounded_int(height if height is not None else base.height, "height", 180, 2160)
    custom_fps = _bounded_int(fps if fps is not None else base.fps, "fps", 5, 120)
    custom_bitrate = _bounded_float(
        bitrate_mbps if bitrate_mbps is not None else base.bitrate_mbps,
        "bitrate_mbps",
        0.1,
        100.0,
    )
    return QualityProfile(
        key="custom",
        name="自定义",
        fps=custom_fps,
        width=custom_width,
        height=custom_height,
        bitrate_mbps=custom_bitrate,
        max_rtt_ms=None,
    )


def _bounded_int(value: Any, field_name: str, minimum: int, maximum: int) -> int:
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return parsed


def _bounded_float(value: Any, field_name: str, minimum: float, maximum: float) -> float:
    parsed = float(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return parsed
