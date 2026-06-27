from __future__ import annotations

from screen_windows import host as module


def test_run_host_handles_keyboard_interrupt_cleanly(monkeypatch, capsys) -> None:
    def fake_asyncio_run(coro):
        coro.close()
        raise KeyboardInterrupt

    monkeypatch.setattr(module.asyncio, "run", fake_asyncio_run)

    exit_code = module.run_host(
        config_path=None,
        host_override=None,
        port_override=None,
        http_port_override=None,
    )

    assert exit_code == 0
    assert "screen_windows host stopped" in capsys.readouterr().out
