from __future__ import annotations

from screen_windows.app.cli import build_parser
from screen_windows.app.cli import main as cli_main


def test_cli_registers_discover_command() -> None:
    parser = build_parser()

    args = parser.parse_args(["discover", "--method", "both", "--timeout", "0.1", "--json"])

    assert args.command == "discover"
    assert args.method == "both"
    assert args.timeout == 0.1
    assert args.json is True


def test_cli_registers_info_command() -> None:
    parser = build_parser()

    args = parser.parse_args(["info", "--config", "host_config.toml", "--json"])

    assert args.command == "info"
    assert args.config == "host_config.toml"
    assert args.json is True


def test_cli_registers_bench_encode_overrides() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "bench-encode",
            "--config",
            "host_config.toml",
            "--frames",
            "9",
            "--width",
            "800",
            "--height",
            "450",
            "--fps",
            "60",
            "--json",
        ]
    )

    assert args.command == "bench-encode"
    assert args.config == "host_config.toml"
    assert args.frames == 9
    assert args.width == 800
    assert args.height == 450
    assert args.fps == 60
    assert args.json is True


def test_cli_host_returns_run_host_exit_code(monkeypatch) -> None:
    from screen_windows.app import cli as module

    calls = {}

    def fake_run_host(**kwargs):
        calls.update(kwargs)
        return 0

    monkeypatch.setattr(module, "run_host", fake_run_host)

    exit_code = cli_main(["host", "--host", "127.0.0.1", "--port", "8765", "--http-port", "8766"])

    assert exit_code == 0
    assert calls == {
        "config_path": None,
        "host_override": "127.0.0.1",
        "port_override": 8765,
        "http_port_override": 8766,
    }
