from __future__ import annotations

from dataclasses import asdict, dataclass
import asyncio
import json
import platform
import socket
from typing import Any

try:
    from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
except ImportError:  # pragma: no cover - 可选依赖分支
    ServiceBrowser = None
    ServiceInfo = None
    Zeroconf = None


DISCOVERY_MAGIC = "screen_windows_host_v1"
MDNS_SERVICE_TYPE = "_screen-windows._tcp.local."


@dataclass(frozen=True, slots=True)
class DiscoveryAnnouncement:
    device_name: str
    ws_port: int
    http_port: int
    auth_mode: str
    version: str = "0.1.0"
    magic: str = DISCOVERY_MAGIC

    def to_json_bytes(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @classmethod
    def from_json_bytes(cls, payload: bytes) -> "DiscoveryAnnouncement":
        raw = json.loads(payload.decode("utf-8"))
        if raw.get("magic") != DISCOVERY_MAGIC:
            raise ValueError("invalid discovery payload")
        return cls(
            device_name=raw["device_name"],
            ws_port=int(raw["ws_port"]),
            http_port=int(raw["http_port"]),
            auth_mode=raw["auth_mode"],
            version=raw.get("version", "0.1.0"),
            magic=raw.get("magic", DISCOVERY_MAGIC),
        )


@dataclass(frozen=True, slots=True)
class DiscoveryBackendStatus:
    name: str
    enabled: bool
    running: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "running": self.running,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DiscoveredHost:
    address: str
    announcement: DiscoveryAnnouncement

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "device_name": self.announcement.device_name,
            "ws_port": self.announcement.ws_port,
            "http_port": self.announcement.http_port,
            "auth_mode": self.announcement.auth_mode,
            "version": self.announcement.version,
        }


class UdpDiscoveryBroadcaster:
    """使用广播包发送主机在线信息。"""

    def __init__(self, udp_port: int, interval_seconds: float) -> None:
        self._udp_port = udp_port
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._last_error = ""

    async def start(self, announcement: DiscoveryAnnouncement) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._broadcast_loop(announcement))

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    @property
    def status(self) -> DiscoveryBackendStatus:
        return DiscoveryBackendStatus(
            name="udp",
            enabled=True,
            running=self._task is not None and not self._task.done(),
            reason=self._last_error or "ok",
        )

    async def _broadcast_loop(self, announcement: DiscoveryAnnouncement) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)
            payload = announcement.to_json_bytes()
            loop = asyncio.get_running_loop()
            while not self._stop_event.is_set():
                try:
                    await loop.sock_sendto(sock, payload, ("255.255.255.255", self._udp_port))
                    self._last_error = ""
                except OSError as exc:
                    self._last_error = str(exc)
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._interval,
                    )
                except TimeoutError:
                    continue
        finally:
            sock.close()


class MdnsDiscoveryPublisher:
    """mDNS 是体验增强；失败时不影响 UDP 保底发现。"""

    def __init__(self) -> None:
        self._zeroconf: Any | None = None
        self._service_info: Any | None = None
        self._status = DiscoveryBackendStatus(
            name="mdns",
            enabled=True,
            running=False,
            reason="not started",
        )

    async def start(self, announcement: DiscoveryAnnouncement) -> None:
        if self._service_info is not None:
            return
        if Zeroconf is None or ServiceInfo is None:
            self._status = DiscoveryBackendStatus("mdns", True, False, "zeroconf unavailable")
            return

        try:
            address = _primary_ipv4_address()
            service_name = f"{_safe_service_name(announcement.device_name)}.{MDNS_SERVICE_TYPE}"
            properties = {
                "magic": announcement.magic,
                "version": announcement.version,
                "auth": announcement.auth_mode,
                "ws": str(announcement.ws_port),
                "http": str(announcement.http_port),
                "device": announcement.device_name,
            }
            self._zeroconf = Zeroconf()
            self._service_info = ServiceInfo(
                MDNS_SERVICE_TYPE,
                service_name,
                addresses=[socket.inet_aton(address)],
                port=announcement.http_port,
                properties=properties,
                server=f"{platform.node() or 'screen-windows'}.local.",
            )
            await asyncio.to_thread(self._zeroconf.register_service, self._service_info)
            self._status = DiscoveryBackendStatus("mdns", True, True, "ok")
        except Exception as exc:  # pragma: no cover - 依赖系统网络环境
            self._service_info = None
            if self._zeroconf is not None:
                await asyncio.to_thread(self._zeroconf.close)
                self._zeroconf = None
            self._status = DiscoveryBackendStatus("mdns", True, False, str(exc))

    async def stop(self) -> None:
        if self._zeroconf is None:
            self._status = DiscoveryBackendStatus("mdns", True, False, "stopped")
            return
        try:
            if self._service_info is not None:
                await asyncio.to_thread(self._zeroconf.unregister_service, self._service_info)
        finally:
            await asyncio.to_thread(self._zeroconf.close)
            self._zeroconf = None
            self._service_info = None
            self._status = DiscoveryBackendStatus("mdns", True, False, "stopped")

    @property
    def status(self) -> DiscoveryBackendStatus:
        return self._status


class DiscoveryManager:
    def __init__(
        self,
        *,
        method: str,
        udp_port: int,
        interval_seconds: float,
    ) -> None:
        self._method = method.strip().lower()
        self._udp = UdpDiscoveryBroadcaster(udp_port, interval_seconds)
        self._mdns = MdnsDiscoveryPublisher()

    async def start(self, announcement: DiscoveryAnnouncement) -> None:
        if self._method in {"off", "none", "disabled"}:
            return
        if self._method in {"udp", "both"}:
            await self._udp.start(announcement)
        if self._method in {"mdns", "both"}:
            await self._mdns.start(announcement)

    async def stop(self) -> None:
        if self._method in {"udp", "both"}:
            await self._udp.stop()
        if self._method in {"mdns", "both"}:
            await self._mdns.stop()

    @property
    def status(self) -> dict[str, Any]:
        return {
            "method": self._method,
            "backends": [
                self._udp.status.to_dict()
                if self._method in {"udp", "both"}
                else DiscoveryBackendStatus("udp", False, False, "disabled").to_dict(),
                self._mdns.status.to_dict()
                if self._method in {"mdns", "both"}
                else DiscoveryBackendStatus("mdns", False, False, "disabled").to_dict(),
            ],
        }


def _primary_ipv4_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _safe_service_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value)
    return cleaned.strip("-") or "screen-windows"


async def discover_udp_hosts(
    *,
    udp_port: int,
    timeout_seconds: float,
) -> list[DiscoveredHost]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    hosts: dict[tuple[str, int, int], DiscoveredHost] = {}
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", udp_port))
        sock.setblocking(False)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                payload, address = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 4096),
                    timeout=remaining,
                )
            except TimeoutError:
                break
            try:
                announcement = DiscoveryAnnouncement.from_json_bytes(payload)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            key = (address[0], announcement.ws_port, announcement.http_port)
            hosts[key] = DiscoveredHost(address=address[0], announcement=announcement)
    finally:
        sock.close()
    return list(hosts.values())


class _MdnsCollector:
    def __init__(self) -> None:
        self.names: set[str] = set()

    def add_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        self.names.add(name)

    def update_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        self.names.add(name)

    def remove_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        self.names.discard(name)


async def discover_mdns_hosts(*, timeout_seconds: float) -> list[DiscoveredHost]:
    if Zeroconf is None or ServiceBrowser is None:
        return []

    zeroconf = Zeroconf()
    collector = _MdnsCollector()
    try:
        ServiceBrowser(zeroconf, MDNS_SERVICE_TYPE, collector)
        await asyncio.sleep(max(timeout_seconds, 0.0))
        hosts: dict[tuple[str, int, int], DiscoveredHost] = {}
        for name in collector.names:
            info = await asyncio.to_thread(
                zeroconf.get_service_info,
                MDNS_SERVICE_TYPE,
                name,
            )
            host = _discovered_host_from_mdns_info(info)
            if host is None:
                continue
            key = (host.address, host.announcement.ws_port, host.announcement.http_port)
            hosts[key] = host
        return list(hosts.values())
    except Exception:  # pragma: no cover - 依赖系统 mDNS 环境
        return []
    finally:
        await asyncio.to_thread(zeroconf.close)


async def discover_hosts(
    *,
    method: str,
    udp_port: int,
    timeout_seconds: float,
) -> list[DiscoveredHost]:
    normalized = method.strip().lower()
    tasks = []
    if normalized in {"udp", "both"}:
        tasks.append(discover_udp_hosts(udp_port=udp_port, timeout_seconds=timeout_seconds))
    if normalized in {"mdns", "both"}:
        tasks.append(discover_mdns_hosts(timeout_seconds=timeout_seconds))
    if not tasks:
        return []

    results = await asyncio.gather(*tasks)
    hosts: dict[tuple[str, int, int], DiscoveredHost] = {}
    for group in results:
        for host in group:
            key = (host.address, host.announcement.ws_port, host.announcement.http_port)
            hosts[key] = host
    return list(hosts.values())


def _discovered_host_from_mdns_info(info: Any | None) -> DiscoveredHost | None:
    if info is None:
        return None
    properties = {
        _decode_bytes(key): _decode_bytes(value)
        for key, value in dict(info.properties or {}).items()
    }
    if properties.get("magic") != DISCOVERY_MAGIC:
        return None
    addresses = getattr(info, "addresses", []) or []
    if not addresses:
        return None
    address = socket.inet_ntoa(addresses[0])
    http_port = int(properties.get("http") or info.port)
    announcement = DiscoveryAnnouncement(
        device_name=properties.get("device") or info.name.split(".")[0],
        ws_port=int(properties["ws"]),
        http_port=http_port,
        auth_mode=properties.get("auth", "pin_once"),
        version=properties.get("version", "0.1.0"),
    )
    return DiscoveredHost(address=address, announcement=announcement)


def _decode_bytes(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
