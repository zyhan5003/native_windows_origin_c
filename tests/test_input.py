from __future__ import annotations

from screen_windows.input import (
    EXTENDED_CODES,
    InputBatch,
    MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_MOVE,
    MOUSEEVENTF_VIRTUALDESK,
    RecordingInputExecutor,
    VK_CODE_MAP,
    WindowsInputExecutor,
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

    monkeypatch.setattr("screen_windows.input.ctypes.windll", type("Windll", (), {"user32": User32()})())
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
