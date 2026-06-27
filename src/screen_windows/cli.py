from __future__ import annotations

import argparse
import asyncio
import json

from .bench import main as bench_main
from .config import load_config
from .discovery import discover_hosts
from .host import run_host
from .info import main as info_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="screen_windows CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    host_parser = subparsers.add_parser("host", help="启动受控端服务")
    host_parser.add_argument("--config", default=None, help="TOML 配置文件路径")
    host_parser.add_argument("--host", default=None, help="覆盖绑定地址")
    host_parser.add_argument("--port", type=int, default=None, help="覆盖 WebSocket 端口")
    host_parser.add_argument("--http-port", type=int, default=None, help="覆盖 HTTP 端口")

    subparsers.add_parser("bench-encode", help="运行最小 FFmpeg 编码链路基准")

    info_parser = subparsers.add_parser("info", help="输出环境与编码链路摘要")
    info_parser.add_argument("--config", default=None, help="TOML 配置文件路径")
    info_parser.add_argument("--json", action="store_true", help="输出 JSON")

    discover_parser = subparsers.add_parser("discover", help="扫描局域网受控端")
    discover_parser.add_argument("--config", default=None, help="TOML 配置文件路径")
    discover_parser.add_argument(
        "--method",
        choices=["udp", "mdns", "both"],
        default=None,
        help="发现方式，默认读取配置",
    )
    discover_parser.add_argument("--udp-port", type=int, default=None, help="覆盖 UDP 发现端口")
    discover_parser.add_argument("--timeout", type=float, default=3.0, help="扫描秒数")
    discover_parser.add_argument("--json", action="store_true", help="输出 JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "host":
        run_host(
            config_path=args.config,
            host_override=args.host,
            port_override=args.port,
            http_port_override=args.http_port,
        )
        return 0

    if args.command == "bench-encode":
        return bench_main()

    if args.command == "info":
        info_args: list[str] = []
        if args.config is not None:
            info_args.extend(["--config", args.config])
        if args.json:
            info_args.append("--json")
        return info_main(info_args)

    if args.command == "discover":
        config = load_config(args.config)
        udp_port = args.udp_port if args.udp_port is not None else config.discovery.udp_port
        method = args.method if args.method is not None else config.discovery.method
        hosts = asyncio.run(
            discover_hosts(
                method=method,
                udp_port=udp_port,
                timeout_seconds=args.timeout,
            )
        )
        rows = [host.to_dict() for host in hosts]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            if not rows:
                print("未发现 screen_windows 受控端")
            for row in rows:
                print(
                    f"{row['device_name']} "
                    f"http://{row['address']}:{row['http_port']} "
                    f"ws://{row['address']}:{row['ws_port']} "
                    f"auth={row['auth_mode']}"
                )
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2
