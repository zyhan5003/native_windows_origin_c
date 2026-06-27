from __future__ import annotations

from screen_windows.clipboard import ClipboardService, RecordingClipboardBackend


def test_clipboard_service_tracks_text_reads_and_writes() -> None:
    backend = RecordingClipboardBackend(text="hello")
    service = ClipboardService(backend=backend, backend_name="recording")

    assert service.read_text() == "hello"
    service.write_text("world")

    assert backend.text == "world"
    assert backend.writes == ["world"]
    assert service.read_count == 1
    assert service.write_count == 1
    assert service.mime_types == ("text/plain",)
