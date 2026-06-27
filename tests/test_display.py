from __future__ import annotations

from screen_windows.config import StreamConfig
from screen_windows.display import enumerate_displays


def test_enumerate_displays_uses_mss_monitors(monkeypatch) -> None:
    import screen_windows.display as module

    class FakeMss:
        monitors = [
            {"left": 0, "top": 0, "width": 3200, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 1920, "top": 0, "width": 1280, "height": 720},
        ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(module, "MSS", FakeMss)

    info = enumerate_displays(StreamConfig(width=800, height=600, monitor=1))

    assert info.source == "mss"
    assert info.selected_monitor == 1
    assert len(info.monitors) == 2
    assert info.monitors[0].primary is True
    assert info.monitors[1].width == 1280


def test_enumerate_displays_falls_back_when_mss_missing(monkeypatch) -> None:
    import screen_windows.display as module

    monkeypatch.setattr(module, "MSS", None)

    info = enumerate_displays(StreamConfig(width=800, height=600, monitor=3))

    assert info.source == "fallback"
    assert info.selected_monitor == 0
    assert info.monitors[0].width == 800
    assert info.monitors[0].height == 600
