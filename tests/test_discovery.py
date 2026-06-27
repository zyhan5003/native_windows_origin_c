from __future__ import annotations

import asyncio
import socket

from screen_windows.discovery import (
    DISCOVERY_MAGIC,
    DiscoveryAnnouncement,
    DiscoveryManager,
    MDNS_SERVICE_TYPE,
    _discovered_host_from_mdns_info,
    discover_udp_hosts,
)


def test_discovery_announcement_roundtrip() -> None:
    announcement = DiscoveryAnnouncement(
        device_name="host-a",
        ws_port=8765,
        http_port=8766,
        auth_mode="pin_once",
    )

    parsed = DiscoveryAnnouncement.from_json_bytes(announcement.to_json_bytes())

    assert parsed.device_name == "host-a"
    assert parsed.ws_port == 8765
    assert parsed.http_port == 8766
    assert parsed.magic == DISCOVERY_MAGIC


def test_discovery_manager_reports_disabled_backends() -> None:
    manager = DiscoveryManager(method="off", udp_port=9876, interval_seconds=1)

    status = manager.status

    assert status["method"] == "off"
    assert status["backends"][0]["name"] == "udp"
    assert status["backends"][0]["enabled"] is False
    assert status["backends"][1]["name"] == "mdns"
    assert status["backends"][1]["enabled"] is False


def test_mdns_service_type_is_stable() -> None:
    assert MDNS_SERVICE_TYPE == "_screen-windows._tcp.local."


def test_mdns_service_info_is_parsed_into_discovered_host() -> None:
    class Info:
        name = f"host-c.{MDNS_SERVICE_TYPE}"
        port = 8766
        addresses = [socket.inet_aton("127.0.0.1")]
        properties = {
            b"magic": DISCOVERY_MAGIC.encode("utf-8"),
            b"device": b"host-c",
            b"ws": b"8765",
            b"http": b"8766",
            b"auth": b"pin_once",
            b"version": b"0.1.0",
        }

    host = _discovered_host_from_mdns_info(Info())

    assert host is not None
    assert host.address == "127.0.0.1"
    assert host.announcement.device_name == "host-c"
    assert host.announcement.ws_port == 8765
    assert host.announcement.http_port == 8766


def test_discover_udp_hosts_receives_announcement() -> None:
    asyncio.run(_test_discover_udp_hosts_receives_announcement())


async def _test_discover_udp_hosts_receives_announcement() -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    finally:
        probe.close()
    announcement = DiscoveryAnnouncement(
        device_name="host-b",
        ws_port=8765,
        http_port=8766,
        auth_mode="pin_once",
    )
    scan_task = asyncio.create_task(
        discover_udp_hosts(udp_port=port, timeout_seconds=1.0)
    )
    await asyncio.sleep(0.05)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(announcement.to_json_bytes(), ("127.0.0.1", port))
    finally:
        sock.close()

    hosts = await scan_task

    assert len(hosts) == 1
    assert hosts[0].address == "127.0.0.1"
    assert hosts[0].announcement.device_name == "host-b"
