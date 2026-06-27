from __future__ import annotations

from screen_windows.web.webui import INDEX_HTML


def test_webui_invalid_token_stops_reconnect_until_pin_is_provided() -> None:
    assert "let autoReconnectPaused = false;" in INDEX_HTML
    assert "if (autoReconnectPaused) {" in INDEX_HTML
    assert "令牌失效，请重新输入 PIN" in INDEX_HTML
    assert "socket.close();" in INDEX_HTML
    assert "if (pinInput.value.trim() || authMode() === 'none') {" in INDEX_HTML


def test_webui_reuses_single_token_clear_helper() -> None:
    assert "function clearStoredAuthToken()" in INDEX_HTML
    assert INDEX_HTML.count("localStorage.removeItem('screen_windows_token')") == 1


def test_webui_renders_video_performance_stats() -> None:
    assert 'id="mediaStats"' in INDEX_HTML
    assert "function renderMediaStats(runtime)" in INDEX_HTML
    assert "video.effective_fps" in INDEX_HTML
    assert "video.motion_ratio" in INDEX_HTML
    assert "video.capture_ms" in INDEX_HTML
    assert "system.cpu_percent" in INDEX_HTML


def test_webui_uses_server_file_transfer_limits() -> None:
    assert "function updateFileTransferLimits(limits)" in INDEX_HTML
    assert "updateFileTransferLimits(payload.file_transfer)" in INDEX_HTML
    assert "file.size > fileTransferLimits.maxFileSize" in INDEX_HTML
    assert "chunkSize: fileTransferLimits.chunkSize" in INDEX_HTML
    assert INDEX_HTML.count("chunkSize: 64 * 1024") == 1


def test_webui_releases_pressed_inputs_on_focus_loss() -> None:
    assert "const pressedKeys = new Set();" in INDEX_HTML
    assert "const pressedMouseButtons = new Set();" in INDEX_HTML
    assert "function releasePressedInputs()" in INDEX_HTML
    assert "sendMouseButton(button, true)" in INDEX_HTML
    assert "sendMouseButton(button, false)" in INDEX_HTML
    assert "sendKey(event.code, true)" in INDEX_HTML
    assert "sendKey(event.code, false)" in INDEX_HTML
    assert "controlSurface.addEventListener('mouseleave'" in INDEX_HTML
    assert "window.addEventListener('blur'" in INDEX_HTML


def test_webui_ignores_stale_signal_socket_events() -> None:
    assert "if (signalSocket !== socket) {" in INDEX_HTML
    assert "stale close ignored" in INDEX_HTML
    assert "stale message ignored" in INDEX_HTML
    assert "if (peerConnection === closingConnection) {" in INDEX_HTML


def test_webui_rebuilds_media_when_webrtc_fails() -> None:
    assert "let mediaReconnectTimer = null;" in INDEX_HTML
    assert "function scheduleMediaReconnect(reason)" in INDEX_HTML
    assert "scheduleMediaReconnect(connection.connectionState)" in INDEX_HTML
    assert "mediaReconnectAttempts += 1;" in INDEX_HTML
    assert "await startPreview();" in INDEX_HTML
    assert "clearMediaReconnectTimer();" in INDEX_HTML


def test_webui_exposes_manual_resolution_fps_and_bitrate_controls() -> None:
    assert 'id="qualityResolution"' in INDEX_HTML
    assert 'id="qualityFps"' in INDEX_HTML
    assert 'id="qualityBitrate"' in INDEX_HTML
    assert '<option value="1600x900">1600 x 900</option>' in INDEX_HTML
    assert "payload.width = resolution.width;" in INDEX_HTML
    assert "payload.height = resolution.height;" in INDEX_HTML
    assert "payload.fps = Number(qualityFps.value);" in INDEX_HTML
    assert "payload.bitrate_mbps = Number(qualityBitrate.value);" in INDEX_HTML
    assert "function qualityProfileKey(profile)" in INDEX_HTML


def test_webui_has_preview_lifecycle_and_view_controls() -> None:
    assert 'id="rebuildPreviewBtn"' in INDEX_HTML
    assert 'id="fitModeBtn"' in INDEX_HTML
    assert 'id="fullscreenBtn"' in INDEX_HTML
    assert "async function stopPreview" in INDEX_HTML
    assert "type: 'webrtc_close'" in INDEX_HTML
    assert "streamBtn.textContent = active ? '停止画面预览' : '2. 启动画面预览';" in INDEX_HTML
    assert "controlSurface.requestFullscreen()" in INDEX_HTML
    assert "controlSurface.classList.toggle('fit-cover'" in INDEX_HTML


def test_webui_guides_non_professional_users() -> None:
    assert "远程控制台" in INDEX_HTML
    assert 'aria-label="三步开始"' in INDEX_HTML
    assert "align-self: start;" in INDEX_HTML
    assert "1. 连接主机" in INDEX_HTML
    assert "2. 启动画面预览" in INDEX_HTML
    assert "3. 启用键鼠控制" in INDEX_HTML
    assert "不确定时保持自动" in INDEX_HTML
    assert "高级诊断日志" in INDEX_HTML
