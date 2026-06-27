from __future__ import annotations

import asyncio

from .config import apply_overrides, load_config
from .server import HostServer


async def _run_host_async(
    *,
    config_path: str | None,
    host_override: str | None,
    port_override: int | None,
    http_port_override: int | None,
) -> None:
    config = load_config(config_path)
    config = apply_overrides(
        config,
        host_override=host_override,
        port_override=port_override,
        http_port_override=http_port_override,
    )

    server = HostServer(config)
    await server.run_forever()


def run_host(
    *,
    config_path: str | None,
    host_override: str | None,
    port_override: int | None,
    http_port_override: int | None,
) -> int:
    try:
        asyncio.run(
            _run_host_async(
                config_path=config_path,
                host_override=host_override,
                port_override=port_override,
                http_port_override=http_port_override,
            )
        )
    except KeyboardInterrupt:
        print("screen_windows host stopped")
        return 0
    return 0
