from __future__ import annotations

import numpy as np

from screen_windows.config import StreamConfig
from screen_windows.video_source import SyntheticFrameSource, build_frame_source


def test_synthetic_frame_source_outputs_expected_shape() -> None:
    source = SyntheticFrameSource(width=320, height=180, fps=24)

    frame = source.render(0)

    assert frame.shape == (180, 320, 3)
    assert frame.dtype == np.uint8


def test_build_frame_source_auto_falls_back_to_synthetic_when_backends_fail(
    monkeypatch,
) -> None:
    import screen_windows.video_source as module

    def fail_dxcam(config: StreamConfig):
        raise RuntimeError("dxcam unavailable")

    def fail_mss(config: StreamConfig):
        raise RuntimeError("mss unavailable")

    monkeypatch.setattr(module, "DxcamFrameSource", fail_dxcam)
    monkeypatch.setattr(module, "MssFrameSource", fail_mss)

    source = build_frame_source(StreamConfig(source="auto", width=320, height=180, fps=12))

    assert source.source_name == "synthetic"
