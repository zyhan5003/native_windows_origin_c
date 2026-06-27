from __future__ import annotations

from dataclasses import dataclass, field
import ctypes
from ctypes import wintypes
import time
from typing import Protocol


CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


class ClipboardBackend(Protocol):
    def read_text(self) -> str:
        ...

    def write_text(self, text: str) -> None:
        ...


@dataclass(slots=True)
class ClipboardService:
    backend: ClipboardBackend
    backend_name: str
    read_count: int = 0
    write_count: int = 0

    @property
    def mime_types(self) -> tuple[str, ...]:
        return ("text/plain",)

    def read_text(self) -> str:
        text = self.backend.read_text()
        self.read_count += 1
        return text

    def write_text(self, text: str) -> None:
        self.backend.write_text(text)
        self.write_count += 1


@dataclass(slots=True)
class RecordingClipboardBackend:
    text: str = ""
    writes: list[str] = field(default_factory=list)

    def read_text(self) -> str:
        return self.text

    def write_text(self, text: str) -> None:
        self.text = text
        self.writes.append(text)


class WindowsClipboardBackend:
    """使用 Win32 Clipboard API 读写文本剪贴板。"""

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        self._user32.OpenClipboard.argtypes = [wintypes.HWND]
        self._user32.OpenClipboard.restype = wintypes.BOOL
        self._user32.CloseClipboard.argtypes = []
        self._user32.CloseClipboard.restype = wintypes.BOOL
        self._user32.EmptyClipboard.argtypes = []
        self._user32.EmptyClipboard.restype = wintypes.BOOL
        self._user32.GetClipboardData.argtypes = [wintypes.UINT]
        self._user32.GetClipboardData.restype = wintypes.HANDLE
        self._user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        self._user32.SetClipboardData.restype = wintypes.HANDLE
        self._user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        self._user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

        self._kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self._kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        self._kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalLock.restype = wintypes.LPVOID
        self._kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalUnlock.restype = wintypes.BOOL
        self._kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalFree.restype = wintypes.HGLOBAL

    def read_text(self) -> str:
        self._open_clipboard()
        try:
            if not self._user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return ""

            handle = self._user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                raise OSError("GetClipboardData failed")

            locked = self._kernel32.GlobalLock(handle)
            if not locked:
                raise OSError("GlobalLock failed")
            try:
                return ctypes.wstring_at(locked)
            finally:
                self._kernel32.GlobalUnlock(handle)
        finally:
            self._user32.CloseClipboard()

    def write_text(self, text: str) -> None:
        payload = text.replace("\r\n", "\n")
        buffer = ctypes.create_unicode_buffer(payload)
        size = ctypes.sizeof(buffer)
        handle = self._kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            raise OSError("GlobalAlloc failed")

        locked = self._kernel32.GlobalLock(handle)
        if not locked:
            self._kernel32.GlobalFree(handle)
            raise OSError("GlobalLock failed")

        try:
            ctypes.memmove(locked, ctypes.addressof(buffer), size)
        finally:
            self._kernel32.GlobalUnlock(handle)

        self._open_clipboard()
        try:
            if not self._user32.EmptyClipboard():
                raise OSError("EmptyClipboard failed")
            if not self._user32.SetClipboardData(CF_UNICODETEXT, handle):
                raise OSError("SetClipboardData failed")
            handle = None
        finally:
            self._user32.CloseClipboard()
            if handle:
                self._kernel32.GlobalFree(handle)

    def _open_clipboard(self) -> None:
        # 剪贴板可能被其他进程短暂占用，做极小重试避免误判失败。
        for _ in range(10):
            if self._user32.OpenClipboard(None):
                return
            time.sleep(0.02)
        raise OSError("OpenClipboard failed")
