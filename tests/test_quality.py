from __future__ import annotations

from screen_windows.quality import QualityController, QualitySignal


def test_quality_controller_downgrades_after_short_bad_signal() -> None:
    controller = QualityController(mode="auto", profile="standard")

    first = controller.update(QualitySignal(rtt_ms=70, bandwidth_mbps=0.4), now=10.0)
    assert first.profile.key == "standard"
    assert first.pending_profile is not None
    assert first.pending_profile.key == "limit"

    second = controller.update(QualitySignal(rtt_ms=70, bandwidth_mbps=0.4), now=11.1)
    assert second.profile.key == "limit"
    assert second.pending_profile is None


def test_quality_controller_manual_lock_ignores_network_signal() -> None:
    controller = QualityController(mode="manual", profile="fast")

    state = controller.update(QualitySignal(rtt_ms=90, bandwidth_mbps=0.2), now=1.0)

    assert state.mode == "manual"
    assert state.locked is True
    assert state.profile.key == "fast"


def test_quality_controller_accepts_manual_custom_profile() -> None:
    controller = QualityController(mode="auto", profile="standard")

    state = controller.set_manual(
        "standard",
        width=1600,
        height=900,
        fps=45,
        bitrate_mbps=7.5,
    )

    assert state.mode == "manual"
    assert state.profile.key == "custom"
    assert state.profile.width == 1600
    assert state.profile.height == 900
    assert state.profile.fps == 45
    assert state.profile.bitrate_mbps == 7.5


def test_quality_controller_merges_partial_signals() -> None:
    controller = QualityController(mode="auto", profile="standard")

    controller.update(QualitySignal(rtt_ms=8, bandwidth_mbps=12), now=1.0)
    state = controller.update(QualitySignal(motion_ratio=0.42), now=1.2)

    assert state.last_signal is not None
    assert state.last_signal.rtt_ms == 8
    assert state.last_signal.bandwidth_mbps == 12
    assert state.last_signal.motion_ratio == 0.42


def test_quality_controller_does_not_treat_missing_bandwidth_as_weak_network() -> None:
    controller = QualityController(mode="auto", profile="standard")

    state = controller.update(QualitySignal(rtt_ms=4, motion_ratio=0.5), now=1.0)

    assert state.profile.key == "standard"
    assert state.pending_profile is not None
    assert state.pending_profile.key == "turbo"


def test_quality_controller_does_not_downgrade_on_low_bitrate_estimate_when_rtt_is_good() -> None:
    controller = QualityController(mode="auto", profile="standard")

    state = controller.update(
        QualitySignal(rtt_ms=2, packet_loss=0, bandwidth_mbps=0.3),
        now=1.0,
    )

    assert state.profile.key == "standard"
    assert state.pending_profile is None
