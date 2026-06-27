from __future__ import annotations

from screen_windows.telemetry.stats import SystemStatsCollector


def test_system_stats_snapshot_has_stable_shape() -> None:
    snapshot = SystemStatsCollector().snapshot().to_dict()

    assert snapshot["pid"] > 0
    assert "enabled" in snapshot
    assert "sample_count" in snapshot
    assert "cpu_percent" in snapshot
    assert "memory_rss_mb" in snapshot
    assert "thread_count" in snapshot
    assert "handle_count" in snapshot
    assert "peak_cpu_percent" in snapshot
    assert "peak_memory_rss_mb" in snapshot
    assert "peak_thread_count" in snapshot
    assert "peak_handle_count" in snapshot


def test_system_stats_snapshot_accumulates_peak_values() -> None:
    collector = SystemStatsCollector()

    first = collector.snapshot().to_dict()
    second = collector.snapshot().to_dict()

    if not second["enabled"]:
        assert second["sample_count"] == 0
        return

    assert first["sample_count"] == 1
    assert second["sample_count"] == 2
    assert second["peak_memory_rss_mb"] >= second["memory_rss_mb"]
    assert second["peak_thread_count"] >= second["thread_count"]
    if second["handle_count"] is not None:
        assert second["peak_handle_count"] >= second["handle_count"]
