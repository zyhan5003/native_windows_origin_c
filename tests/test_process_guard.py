from __future__ import annotations

from types import SimpleNamespace

import pytest

from screen_windows.app import process_guard
from screen_windows.app.process_guard import release_stale_host_processes_for_ports


def test_release_stale_host_processes_terminates_screen_windows_host(monkeypatch) -> None:
    fake_process = FakeProcess(
        1234,
        ["python", "-m", "screen_windows", "host", "--port", "8765"],
    )
    fake_psutil = FakePsutil(
        [
            FakeConnection(8765, 1234),
            FakeConnection(8766, 1234),
        ],
        {1234: fake_process},
    )
    monkeypatch.setattr(process_guard, "psutil", fake_psutil)
    monkeypatch.setattr(process_guard.os, "getpid", lambda: 9999)

    result = release_stale_host_processes_for_ports((8765, 8766))

    assert result.terminated_pids == (1234,)
    assert result.released_ports == (8765, 8766)
    assert fake_process.terminated is True


def test_release_stale_host_processes_terminates_same_workspace_orphans(monkeypatch, tmp_path) -> None:
    orphan = FakeProcess(
        3456,
        ["python", "-m", "screen_windows", "host", "--port", "18765"],
        cwd=str(tmp_path),
    )
    fake_psutil = FakePsutil([], {3456: orphan})
    monkeypatch.setattr(process_guard, "psutil", fake_psutil)
    monkeypatch.setattr(process_guard.os, "getpid", lambda: 9999)
    monkeypatch.chdir(tmp_path)

    result = release_stale_host_processes_for_ports((8765, 8766))

    assert result.terminated_pids == (3456,)
    assert orphan.terminated is True


def test_release_stale_host_processes_keeps_other_workspace_orphans(monkeypatch, tmp_path) -> None:
    other_workspace = tmp_path / "other"
    other_workspace.mkdir()
    orphan = FakeProcess(
        4567,
        ["python", "-m", "screen_windows", "host", "--port", "18765"],
        cwd=str(other_workspace),
    )
    fake_psutil = FakePsutil([], {4567: orphan})
    monkeypatch.setattr(process_guard, "psutil", fake_psutil)
    monkeypatch.setattr(process_guard.os, "getpid", lambda: 9999)
    monkeypatch.chdir(tmp_path)

    result = release_stale_host_processes_for_ports((8765, 8766))

    assert result.terminated_pids == ()
    assert orphan.terminated is False


def test_release_stale_host_processes_rejects_non_project_port_owner(monkeypatch) -> None:
    fake_process = FakeProcess(2345, ["python", "-m", "other_service"])
    fake_psutil = FakePsutil([FakeConnection(8765, 2345)], {2345: fake_process})
    monkeypatch.setattr(process_guard, "psutil", fake_psutil)
    monkeypatch.setattr(process_guard.os, "getpid", lambda: 9999)

    with pytest.raises(RuntimeError, match="non screen_windows host"):
        release_stale_host_processes_for_ports((8765,))

    assert fake_process.terminated is False


class FakeConnection:
    def __init__(self, port: int, pid: int) -> None:
        self.laddr = SimpleNamespace(port=port)
        self.pid = pid
        self.status = "LISTEN"


class FakeProcess:
    def __init__(self, pid: int, command_line: list[str], cwd: str = "D:/project/screen_windows") -> None:
        self.pid = pid
        self._command_line = command_line
        self._cwd = cwd
        self.terminated = False
        self.killed = False

    def cmdline(self) -> list[str]:
        return self._command_line

    def cwd(self) -> str:
        return self._cwd

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


class FakePsutil:
    Error = RuntimeError

    def __init__(self, connections: list[FakeConnection], processes: dict[int, FakeProcess]) -> None:
        self._connections = connections
        self._processes = processes
        self._released = False

    def net_connections(self, kind: str):
        if self._released:
            return []
        return list(self._connections)

    def Process(self, pid: int) -> FakeProcess:
        return self._processes[pid]

    def process_iter(self, attrs):
        return list(self._processes.values())

    def wait_procs(self, processes, timeout: float):
        self._released = True
        return list(processes), []
