from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
from typing import Any, Literal, Protocol

ULONG_PTR = ctypes.c_size_t


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

MAPVK_VK_TO_VSC = 0
WHEEL_DELTA = 120

VK_CODE_MAP: dict[str, int] = {
    "Backspace": 0x08,
    "Tab": 0x09,
    "Enter": 0x0D,
    "ShiftLeft": 0xA0,
    "ShiftRight": 0xA1,
    "ControlLeft": 0xA2,
    "ControlRight": 0xA3,
    "AltLeft": 0xA4,
    "AltRight": 0xA5,
    "Pause": 0x13,
    "CapsLock": 0x14,
    "Escape": 0x1B,
    "Space": 0x20,
    "PageUp": 0x21,
    "PageDown": 0x22,
    "End": 0x23,
    "Home": 0x24,
    "ArrowLeft": 0x25,
    "ArrowUp": 0x26,
    "ArrowRight": 0x27,
    "ArrowDown": 0x28,
    "Insert": 0x2D,
    "Delete": 0x2E,
    "PrintScreen": 0x2C,
    "ScrollLock": 0x91,
    "NumLock": 0x90,
    "MetaLeft": 0x5B,
    "MetaRight": 0x5C,
    "NumpadEnter": 0x0D,
    "ContextMenu": 0x5D,
    "Minus": 0xBD,
    "Equal": 0xBB,
    "BracketLeft": 0xDB,
    "BracketRight": 0xDD,
    "Backslash": 0xDC,
    "Semicolon": 0xBA,
    "Quote": 0xDE,
    "Backquote": 0xC0,
    "Comma": 0xBC,
    "Period": 0xBE,
    "Slash": 0xBF,
}

for digit in range(10):
    VK_CODE_MAP[f"Digit{digit}"] = 0x30 + digit
    VK_CODE_MAP[f"Numpad{digit}"] = 0x60 + digit

for offset, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    VK_CODE_MAP[f"Key{letter}"] = 0x41 + offset

for offset in range(1, 13):
    VK_CODE_MAP[f"F{offset}"] = 0x6F + offset

# 小键盘运算键在浏览器里是独立 event.code，需映射到 Win32 VK 才能远程输入。
VK_CODE_MAP.update(
    {
        "NumpadMultiply": 0x6A,
        "NumpadAdd": 0x6B,
        "NumpadSubtract": 0x6D,
        "NumpadDecimal": 0x6E,
        "NumpadDivide": 0x6F,
    }
)

EXTENDED_CODES = {
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "Insert",
    "Delete",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "ControlRight",
    "AltRight",
    "NumpadEnter",
    "NumpadDivide",
    "MetaLeft",
    "MetaRight",
    "ContextMenu",
}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


@dataclass(frozen=True, slots=True)
class MouseMoveEvent:
    kind: Literal["mouse_move"]
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class MouseButtonEvent:
    kind: Literal["mouse_button"]
    button: Literal["left", "middle", "right"]
    pressed: bool


@dataclass(frozen=True, slots=True)
class MouseWheelEvent:
    kind: Literal["mouse_wheel"]
    delta_y: int


@dataclass(frozen=True, slots=True)
class KeyEvent:
    kind: Literal["key"]
    code: str
    pressed: bool


@dataclass(frozen=True, slots=True)
class TextEvent:
    kind: Literal["text"]
    text: str


InputEvent = MouseMoveEvent | MouseButtonEvent | MouseWheelEvent | KeyEvent | TextEvent


@dataclass(frozen=True, slots=True)
class InputBatch:
    seq: int
    events: tuple[InputEvent, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InputBatch":
        seq = int(payload.get("seq", 0))
        raw_events = payload.get("events")
        if not isinstance(raw_events, list) or not raw_events:
            raise ValueError("input batch requires non-empty events")
        return cls(seq=seq, events=tuple(parse_input_event(item) for item in raw_events))


class InputExecutor(Protocol):
    display_width: int
    display_height: int
    display_physical_width: int
    display_physical_height: int
    display_left: int
    display_top: int
    virtual_left: int
    virtual_top: int
    virtual_width: int
    virtual_height: int

    def execute_batch(self, batch: InputBatch) -> None:
        ...


@dataclass(slots=True)
class RecordingInputExecutor:
    display_width: int
    display_height: int
    display_physical_width: int
    display_physical_height: int
    display_left: int
    display_top: int
    virtual_left: int
    virtual_top: int
    virtual_width: int
    virtual_height: int
    applied_batches: list[InputBatch]

    def __init__(
        self,
        display_width: int,
        display_height: int,
        *,
        display_physical_width: int | None = None,
        display_physical_height: int | None = None,
        display_left: int = 0,
        display_top: int = 0,
        virtual_left: int = 0,
        virtual_top: int = 0,
        virtual_width: int | None = None,
        virtual_height: int | None = None,
    ) -> None:
        self.display_width = display_width
        self.display_height = display_height
        self.display_physical_width = display_physical_width or display_width
        self.display_physical_height = display_physical_height or display_height
        self.display_left = display_left
        self.display_top = display_top
        self.virtual_left = virtual_left
        self.virtual_top = virtual_top
        self.virtual_width = virtual_width or display_width
        self.virtual_height = virtual_height or display_height
        self.applied_batches = []

    def execute_batch(self, batch: InputBatch) -> None:
        self.applied_batches.append(batch)


class WindowsInputExecutor:
    """使用 SendInput 执行远程输入事件。"""

    def __init__(
        self,
        display_width: int,
        display_height: int,
        *,
        display_physical_width: int | None = None,
        display_physical_height: int | None = None,
        display_left: int = 0,
        display_top: int = 0,
        virtual_left: int = 0,
        virtual_top: int = 0,
        virtual_width: int | None = None,
        virtual_height: int | None = None,
    ) -> None:
        self.display_width = max(display_width, 1)
        self.display_height = max(display_height, 1)
        self.display_physical_width = max(display_physical_width or self.display_width, 1)
        self.display_physical_height = max(display_physical_height or self.display_height, 1)
        self.display_left = display_left
        self.display_top = display_top
        self.virtual_left = virtual_left
        self.virtual_top = virtual_top
        self.virtual_width = max(virtual_width or self.display_width, 1)
        self.virtual_height = max(virtual_height or self.display_height, 1)
        self._user32 = ctypes.windll.user32

    def execute_batch(self, batch: InputBatch) -> None:
        for event in batch.events:
            self._execute_event(event)

    def _execute_event(self, event: InputEvent) -> None:
        if event.kind == "mouse_move":
            self._send_mouse_move(event.x, event.y)
            return
        if event.kind == "mouse_button":
            self._send_mouse_button(event.button, event.pressed)
            return
        if event.kind == "mouse_wheel":
            self._send_mouse_wheel(event.delta_y)
            return
        if event.kind == "key":
            self._send_key(event.code, event.pressed)
            return
        if event.kind == "text":
            self._send_text(event.text)
            return
        raise ValueError(f"unsupported input event kind: {event.kind}")

    def _send_input(self, input_item: INPUT) -> None:
        sent = self._user32.SendInput(1, ctypes.byref(input_item), ctypes.sizeof(INPUT))
        if sent != 1:
            raise OSError("SendInput failed")

    def _send_mouse_move(self, x: int, y: int) -> None:
        local_x = max(0, min(x, self.display_width - 1))
        local_y = max(0, min(y, self.display_height - 1))
        physical_x = int(round((local_x * max(self.display_physical_width - 1, 1)) / max(self.display_width - 1, 1)))
        physical_y = int(round((local_y * max(self.display_physical_height - 1, 1)) / max(self.display_height - 1, 1)))
        absolute_x = self.display_left + physical_x
        absolute_y = self.display_top + physical_y
        virtual_x = absolute_x - self.virtual_left
        virtual_y = absolute_y - self.virtual_top
        normalized_x = _normalize_absolute_mouse_coordinate(virtual_x, self.virtual_width)
        normalized_y = _normalize_absolute_mouse_coordinate(virtual_y, self.virtual_height)
        input_item = INPUT(
            type=INPUT_MOUSE,
            mi=MOUSEINPUT(
                dx=normalized_x,
                dy=normalized_y,
                mouseData=0,
                dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                time=0,
                dwExtraInfo=0,
            ),
        )
        self._send_input(input_item)

    def _send_mouse_button(self, button: str, pressed: bool) -> None:
        flag_map = {
            ("left", True): MOUSEEVENTF_LEFTDOWN,
            ("left", False): MOUSEEVENTF_LEFTUP,
            ("middle", True): MOUSEEVENTF_MIDDLEDOWN,
            ("middle", False): MOUSEEVENTF_MIDDLEUP,
            ("right", True): MOUSEEVENTF_RIGHTDOWN,
            ("right", False): MOUSEEVENTF_RIGHTUP,
        }
        flags = flag_map[(button, pressed)]
        input_item = INPUT(
            type=INPUT_MOUSE,
            mi=MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=0,
                dwFlags=flags,
                time=0,
                dwExtraInfo=0,
            ),
        )
        self._send_input(input_item)

    def _send_mouse_wheel(self, delta_y: int) -> None:
        wheel_clicks = 0
        if delta_y > 0:
            wheel_clicks = -WHEEL_DELTA
        elif delta_y < 0:
            wheel_clicks = WHEEL_DELTA
        if wheel_clicks == 0:
            return
        input_item = INPUT(
            type=INPUT_MOUSE,
            mi=MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=wheel_clicks & 0xFFFFFFFF,
                dwFlags=MOUSEEVENTF_WHEEL,
                time=0,
                dwExtraInfo=0,
            ),
        )
        self._send_input(input_item)

    def _send_key(self, code: str, pressed: bool) -> None:
        vk = VK_CODE_MAP.get(code)
        if vk is None:
            return
        scan_code = self._user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
        flags = KEYEVENTF_SCANCODE
        if code in EXTENDED_CODES:
            flags |= KEYEVENTF_EXTENDEDKEY
        if not pressed:
            flags |= KEYEVENTF_KEYUP

        input_item = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=0,
                wScan=scan_code,
                dwFlags=flags,
                time=0,
                dwExtraInfo=0,
            ),
        )
        self._send_input(input_item)

    def _send_text(self, text: str) -> None:
        # 手机软键盘不会可靠产生桌面键盘码，使用 UTF-16 单元注入覆盖中文等文本输入。
        encoded = text.encode("utf-16-le", errors="surrogatepass")
        for offset in range(0, len(encoded), 2):
            scan_code = int.from_bytes(encoded[offset : offset + 2], "little")
            for pressed in (True, False):
                input_item = INPUT(
                    type=INPUT_KEYBOARD,
                    ki=KEYBDINPUT(
                        wVk=0,
                        wScan=scan_code,
                        dwFlags=KEYEVENTF_UNICODE | (0 if pressed else KEYEVENTF_KEYUP),
                        time=0,
                        dwExtraInfo=0,
                    ),
                )
                self._send_input(input_item)


def parse_input_event(payload: dict[str, Any]) -> InputEvent:
    if not isinstance(payload, dict):
        raise ValueError("input event must be an object")

    event_type = str(payload.get("type", ""))
    if event_type == "mouse_move":
        return MouseMoveEvent(
            kind="mouse_move",
            x=int(payload["x"]),
            y=int(payload["y"]),
        )
    if event_type == "mouse_button":
        button = str(payload["button"])
        if button not in {"left", "middle", "right"}:
            raise ValueError(f"unsupported mouse button: {button}")
        return MouseButtonEvent(
            kind="mouse_button",
            button=button,
            pressed=bool(payload["pressed"]),
        )
    if event_type == "mouse_wheel":
        return MouseWheelEvent(
            kind="mouse_wheel",
            delta_y=int(payload["delta_y"]),
        )
    if event_type == "key":
        return KeyEvent(
            kind="key",
            code=str(payload["code"]),
            pressed=bool(payload["pressed"]),
        )
    if event_type == "text":
        text = payload.get("text", "")
        if not isinstance(text, str):
            raise ValueError("text input event requires string text")
        if not text:
            raise ValueError("text input event requires text")
        if len(text) > 500:
            raise ValueError("text input event is too long")
        return TextEvent(kind="text", text=text)
    raise ValueError(f"unsupported input event type: {event_type}")


def _normalize_absolute_mouse_coordinate(position: int, span: int) -> int:
    span = max(span, 1)
    clamped = max(0, min(position, span - 1))
    if span == 1:
        return 0
    if clamped >= span - 1:
        return 65535
    # SendInput 绝对坐标使用 0..65535，边缘像素必须饱和才能稳定命中底边/右边。
    return int(round((clamped * 65535) / max(span - 1, 1)))
