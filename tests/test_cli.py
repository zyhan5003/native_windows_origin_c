from __future__ import annotations

from screen_windows.cli import build_parser


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
