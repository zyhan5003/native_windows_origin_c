from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - 依赖缺失兜底
    psutil = None


@dataclass(frozen=True, slots=True)
class SystemStatsSnapshot:
    enabled: bool
    reason: str
    pid: int
    sample_count: int
    cpu_percent: float | None
    memory_rss_mb: float | None
    thread_count: int | None
    handle_count: int | None
    peak_cpu_percent: float | None
    peak_memory_rss_mb: float | None
    peak_thread_count: int | None
    peak_handle_count: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "reason": self.reason,
            "pid": self.pid,
            "sample_count": self.sample_count,
            "cpu_percent": self.cpu_percent,
            "memory_rss_mb": self.memory_rss_mb,
            "thread_count": self.thread_count,
            "handle_count": self.handle_count,
            "peak_cpu_percent": self.peak_cpu_percent,
            "peak_memory_rss_mb": self.peak_memory_rss_mb,
            "peak_thread_count": self.peak_thread_count,
            "peak_handle_count": self.peak_handle_count,
        }


class SystemStatsCollector:
    def __init__(self) -> None:
        self._pid = os.getpid()
        self._process = psutil.Process(self._pid) if psutil is not None else None
        self._cpu_primed = False
        self._sample_count = 0
        self._peak_cpu_percent: float | None = None
        self._peak_memory_rss_mb: float | None = None
        self._peak_thread_count: int | None = None
        self._peak_handle_count: int | None = None

    def snapshot(self) -> SystemStatsSnapshot:
        if self._process is None:
            return SystemStatsSnapshot(
                enabled=False,
                reason="psutil unavailable",
                pid=self._pid,
                sample_count=self._sample_count,
                cpu_percent=None,
                memory_rss_mb=None,
                thread_count=None,
                handle_count=None,
                peak_cpu_percent=None,
                peak_memory_rss_mb=None,
                peak_thread_count=None,
                peak_handle_count=None,
            )

        # psutil 的进程 CPU 百分比第一次调用是预热值，不能拿来做性能判断。
        if not self._cpu_primed:
            self._process.cpu_percent(interval=None)
            self._cpu_primed = True
            cpu_percent: float | None = 0.0
        else:
            cpu_percent = round(self._process.cpu_percent(interval=None), 2)

        memory = self._process.memory_info()
        handle_count = (
            self._process.num_handles()
            if hasattr(self._process, "num_handles")
            else None
        )
        memory_rss_mb = round(memory.rss / (1024 * 1024), 2)
        thread_count = self._process.num_threads()
        self._sample_count += 1
        self._peak_cpu_percent = _max_optional(self._peak_cpu_percent, cpu_percent)
        self._peak_memory_rss_mb = _max_optional(self._peak_memory_rss_mb, memory_rss_mb)
        self._peak_thread_count = _max_optional(self._peak_thread_count, thread_count)
        self._peak_handle_count = _max_optional(self._peak_handle_count, handle_count)
        return SystemStatsSnapshot(
            enabled=True,
            reason="ok",
            pid=self._pid,
            sample_count=self._sample_count,
            cpu_percent=cpu_percent,
            memory_rss_mb=memory_rss_mb,
            thread_count=thread_count,
            handle_count=handle_count,
            peak_cpu_percent=self._peak_cpu_percent,
            peak_memory_rss_mb=self._peak_memory_rss_mb,
            peak_thread_count=self._peak_thread_count,
            peak_handle_count=self._peak_handle_count,
        )


def _max_optional(current: float | int | None, value: float | int | None):
    if value is None:
        return current
    if current is None:
        return value
    return max(current, value)
