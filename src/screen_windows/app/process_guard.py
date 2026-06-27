from __future__ import annotations

from dataclasses import dataclass
import os
import time
from collections.abc import Iterable
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover - 项目依赖正常会安装
    psutil = None


@dataclass(frozen=True, slots=True)
class PortCleanupResult:
    terminated_pids: tuple[int, ...]
    released_ports: tuple[int, ...]


def release_stale_host_processes_for_ports(
    ports: Iterable[int],
    *,
    wait_timeout_seconds: float = 5.0,
) -> PortCleanupResult:
    """启动新 Host 前释放旧 screen_windows host，避免用户连到旧进程。"""

    target_ports = {int(port) for port in ports if int(port) > 0}
    if not target_ports or psutil is None:
        return PortCleanupResult(terminated_pids=(), released_ports=())

    owners = _list_listening_port_owners(target_ports)
    current_pid = os.getpid()
    stale_processes = []
    seen_pids: set[int] = set()
    blocked: list[str] = []

    for pid, occupied_ports in owners.items():
        if pid is None:
            port_text = ",".join(str(port) for port in sorted(occupied_ports))
            blocked.append(f"pid=unknown ports={port_text}")
            continue
        if pid == current_pid:
            continue
        process = psutil.Process(pid)
        if _is_screen_windows_host_process(process):
            stale_processes.append(process)
            seen_pids.add(pid)
            continue
        port_text = ",".join(str(port) for port in sorted(occupied_ports))
        blocked.append(f"pid={pid} ports={port_text} cmd={_safe_command_line(process)}")

    if blocked:
        raise RuntimeError(
            "target port is occupied by a non screen_windows host process: "
            + "; ".join(blocked)
        )

    stale_processes.extend(
        _list_same_workspace_host_processes(
            current_pid=current_pid,
            seen_pids=seen_pids,
        )
    )
    terminated_pids = _terminate_processes(stale_processes, wait_timeout_seconds)
    if terminated_pids:
        _wait_ports_released(target_ports, timeout_seconds=wait_timeout_seconds)

    remaining = _list_listening_port_owners(target_ports)
    remaining = {
        pid: ports
        for pid, ports in remaining.items()
        if pid is not None and pid != current_pid
    }
    if remaining:
        details = "; ".join(
            f"pid={pid} ports={','.join(str(port) for port in sorted(ports))}"
            for pid, ports in sorted(remaining.items())
        )
        raise RuntimeError(f"target port is still occupied after cleanup: {details}")

    return PortCleanupResult(
        terminated_pids=tuple(sorted(terminated_pids)),
        released_ports=tuple(sorted(target_ports)) if terminated_pids else (),
    )


def _list_listening_port_owners(ports: set[int]) -> dict[int | None, set[int]]:
    owners: dict[int | None, set[int]] = {}
    assert psutil is not None
    for connection in psutil.net_connections(kind="tcp"):
        local_address = getattr(connection, "laddr", None)
        local_port = getattr(local_address, "port", None)
        if local_port is None and isinstance(local_address, tuple) and len(local_address) >= 2:
            local_port = local_address[1]
        if local_port not in ports:
            continue
        if getattr(connection, "status", "").upper() != "LISTEN":
            continue
        owners.setdefault(getattr(connection, "pid", None), set()).add(int(local_port))
    return owners


def _list_same_workspace_host_processes(
    *,
    current_pid: int,
    seen_pids: set[int],
) -> list[object]:
    assert psutil is not None
    current_cwd = _normalized_path(os.getcwd())
    matches = []
    process_iter = getattr(psutil, "process_iter", None)
    if process_iter is None:
        return matches

    for process in process_iter(["pid", "cmdline", "cwd"]):
        pid = int(getattr(process, "pid", 0) or 0)
        if pid == current_pid or pid in seen_pids:
            continue
        if not _is_screen_windows_host_process(process):
            continue
        if _normalized_path(_safe_cwd(process)) != current_cwd:
            continue
        matches.append(process)
        seen_pids.add(pid)
    return matches


def _terminate_processes(processes: list[object], wait_timeout_seconds: float) -> set[int]:
    if not processes:
        return set()

    assert psutil is not None
    pids = {int(process.pid) for process in processes}
    for process in processes:
        try:
            process.terminate()
        except psutil.Error:
            pass

    gone, alive = psutil.wait_procs(processes, timeout=wait_timeout_seconds)
    for process in alive:
        try:
            process.kill()
        except psutil.Error:
            pass
    if alive:
        psutil.wait_procs(alive, timeout=wait_timeout_seconds)

    return pids


def _wait_ports_released(ports: set[int], *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _list_listening_port_owners(ports):
            return
        time.sleep(0.1)


def _is_screen_windows_host_process(process: object) -> bool:
    command_line = _safe_command_line(process).lower().replace("\\", "/")
    if not command_line:
        return False
    has_project_marker = "screen_windows" in command_line or "screen-windows" in command_line
    has_host_command = " host" in f" {command_line} " or command_line.endswith("/host")
    return has_project_marker and has_host_command


def _safe_command_line(process: object) -> str:
    try:
        return " ".join(process.cmdline())
    except Exception:
        return ""


def _safe_cwd(process: object) -> str:
    try:
        return str(process.cwd())
    except Exception:
        return ""


def _normalized_path(value: str) -> str:
    if not value:
        return ""
    try:
        return str(Path(value).resolve()).casefold()
    except Exception:
        return value.casefold()
