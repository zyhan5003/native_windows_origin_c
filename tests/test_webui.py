from __future__ import annotations

from screen_windows.webui import INDEX_HTML


def test_webui_invalid_token_stops_reconnect_until_pin_is_provided() -> None:
    assert "let autoReconnectPaused = false;" in INDEX_HTML
    assert "if (autoReconnectPaused) {" in INDEX_HTML
    assert "令牌失效，请重新输入 PIN" in INDEX_HTML
    assert "socket.close();" in INDEX_HTML
    assert "if (pinInput.value.trim() || authMode() === 'none') {" in INDEX_HTML


def test_webui_reuses_single_token_clear_helper() -> None:
    assert "function clearStoredAuthToken()" in INDEX_HTML
    assert INDEX_HTML.count("localStorage.removeItem('screen_windows_token')") == 1
