from __future__ import annotations

from screen_windows.control.input import (
    EXTENDED_CODES,
    InputBatch,
    MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_MOVE,
    MOUSEEVENTF_VIRTUALDESK,
    RecordingInputExecutor,
    VK_CODE_MAP,
    WindowsInputExecutor,
    _normalize_absolute_mouse_coordinate,
    parse_input_event,
)


def test_parse_input_event_key() -> None:
    event = parse_input_event(
        {
            "type": "key",
            "code": "KeyA",
            "pressed": True,
        }
    )

    assert event.kind == "key"
    assert event.code == "KeyA"
    assert event.pressed is True


def test_parse_input_event_text() -> None:
    event = parse_input_event({"type": "text", "text": "你好 remote"})

    assert event.kind == "text"
    assert event.text == "你好 remote"


def test_keyboard_mapping_covers_numpad_and_system_keys() -> None:
    assert VK_CODE_MAP["Numpad0"] == 0x60
    assert VK_CODE_MAP["Numpad9"] == 0x69
    assert VK_CODE_MAP["NumpadAdd"] == 0x6B
    assert VK_CODE_MAP["NumpadDivide"] == 0x6F
    assert VK_CODE_MAP["PrintScreen"] == 0x2C
    assert VK_CODE_MAP["ScrollLock"] == 0x91
    assert VK_CODE_MAP["NumLock"] == 0x90
    assert "NumpadEnter" in EXTENDED_CODES
    assert "NumpadDivide" in EXTENDED_CODES


def test_recording_input_executor_records_batch() -> None:
    batch = InputBatch.from_dict(
        {
            "seq": 3,
            "events": [
                {"type": "mouse_move", "x": 12, "y": 18},
                {"type": "mouse_button", "button": "left", "pressed": True},
            ],
        }
    )
    executor = RecordingInputExecutor(display_width=1280, display_height=720)

    executor.execute_batch(batch)

    assert len(executor.applied_batches) == 1
    assert executor.applied_batches[0].seq == 3
    assert executor.applied_batches[0].events[0].kind == "mouse_move"


def test_windows_input_executor_maps_mouse_to_virtual_desktop(monkeypatch) -> None:
    sent_inputs = []

    class User32:
        def SendInput(self, count, pointer, size):
            sent_inputs.append(pointer._obj)
            return 1

        def MapVirtualKeyW(self, vk, mode):
            return vk

    monkeypatch.setattr("screen_windows.control.input.ctypes.windll", type("Windll", (), {"user32": User32()})())
    executor = WindowsInputExecutor(
        display_width=800,
        display_height=450,
        display_left=640,
        display_top=0,
        virtual_left=0,
        virtual_top=0,
        virtual_width=1440,
        virtual_height=450,
    )

    executor._send_mouse_move(0, 0)

    mouse = sent_inputs[0].mi
    assert mouse.dx == round((640 * 65535) / 1439)
    assert mouse.dy == 0
    assert mouse.dwFlags == MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK


def test_windows_input_executor_scales_stream_coordinates_to_display_pixels(monkeypatch) -> None:
    sent_inputs = []

    class User32:
        def SendInput(self, count, pointer, size):
            sent_inputs.append(pointer._obj)
            return 1

        def MapVirtualKeyW(self, vk, mode):
            return vk

    monkeypatch.setattr("screen_windows.control.input.ctypes.windll", type("Windll", (), {"user32": User32()})())
    executor = WindowsInputExecutor(
        display_width=1280,
        display_height=720,
        display_physical_width=1920,
        display_physical_height=1080,
        virtual_width=1920,
        virtual_height=1080,
    )

    executor._send_mouse_move(1279, 719)

    mouse = sent_inputs[0].mi
    assert mouse.dx == 65535
    assert mouse.dy == 65535


def test_absolute_mouse_coordinate_normalization_reaches_edges() -> None:
    assert _normalize_absolute_mouse_coordinate(-10, 1080) == 0
    assert _normalize_absolute_mouse_coordinate(0, 1080) == 0
    assert _normalize_absolute_mouse_coordinate(1078, 1080) < 65535
    assert _normalize_absolute_mouse_coordinate(1079, 1080) == 65535
    assert _normalize_absolute_mouse_coordinate(2000, 1080) == 65535
    assert _normalize_absolute_mouse_coordinate(0, 1) == 0


def test_windows_input_executor_sends_unicode_text(monkeypatch) -> None:
    sent_inputs = []

    class User32:
        def SendInput(self, count, pointer, size):
            sent_inputs.append(pointer._obj)
            return 1

        def MapVirtualKeyW(self, vk, mode):
            return vk

    monkeypatch.setattr("screen_windows.control.input.ctypes.windll", type("Windll", (), {"user32": User32()})())
    executor = WindowsInputExecutor(display_width=800, display_height=450)

    executor._send_text("中A😀")

    assert [item.ki.wScan for item in sent_inputs] == [
        ord("中"),
        ord("中"),
        ord("A"),
        ord("A"),
        0xD83D,
        0xD83D,
        0xDE00,
        0xDE00,
    ]
    assert sent_inputs[0].ki.dwFlags & 0x0004
    assert sent_inputs[1].ki.dwFlags & 0x0002
