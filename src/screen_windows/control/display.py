from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..app.config import StreamConfig

try:
    from mss import MSS
except ImportError:  # pragma: no cover - 环境依赖分支
    MSS = None


@dataclass(frozen=True, slots=True)
class DisplayMonitor:
    id: int
    left: int
    top: int
    width: int
    height: int
    primary: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "primary": self.primary,
        }


@dataclass(frozen=True, slots=True)
class DisplayInfo:
    selected_monitor: int
    monitors: list[DisplayMonitor]
    source: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_monitor": self.selected_monitor,
            "source": self.source,
            "reason": self.reason,
            "monitors": [monitor.to_dict() for monitor in self.monitors],
        }


def enumerate_displays(config: StreamConfig) -> DisplayInfo:
    if MSS is None:
        return _fallback_display_info(config, "mss unavailable")

    try:
        with MSS() as capture:
            monitors = [
                DisplayMonitor(
                    id=index,
                    left=int(raw.get("left", 0)),
                    top=int(raw.get("top", 0)),
                    width=int(raw["width"]),
                    height=int(raw["height"]),
                    primary=index == 0,
                )
                for index, raw in enumerate(capture.monitors[1:])
            ]
    except Exception as exc:  # pragma: no cover - 依赖真实显示环境
        return _fallback_display_info(config, str(exc))

    if not monitors:
        return _fallback_display_info(config, "no monitors reported")

    selected = config.monitor if 0 <= config.monitor < len(monitors) else 0
    return DisplayInfo(
        selected_monitor=selected,
        monitors=monitors,
        source="mss",
        reason="ok",
    )


def _fallback_display_info(config: StreamConfig, reason: str) -> DisplayInfo:
    # 显示枚举失败不能影响远程桌面主链路，先用配置尺寸兜底。
    return DisplayInfo(
        selected_monitor=0,
        monitors=[
            DisplayMonitor(
                id=0,
                left=0,
                top=0,
                width=config.width,
                height=config.height,
                primary=True,
            )
        ],
        source="fallback",
        reason=reason,
    )
