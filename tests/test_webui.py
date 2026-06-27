from __future__ import annotations

from screen_windows.web.webui import INDEX_HTML


def test_webui_invalid_token_stops_reconnect_until_pin_is_provided() -> None:
    assert "let autoReconnectPaused = false;" in INDEX_HTML
    assert "if (autoReconnectPaused) {" in INDEX_HTML
    assert "令牌失效，请重新输入 PIN" in INDEX_HTML
    assert "socket.close();" in INDEX_HTML
    assert "if (normalizedPin() || authMode() === 'none') {" in INDEX_HTML


def test_webui_reuses_single_token_clear_helper() -> None:
    assert "function clearStoredAuthToken()" in INDEX_HTML
    assert "const authTokenStorageKey = 'screen_windows_token';" in INDEX_HTML
    assert "function readStoredAuthToken()" in INDEX_HTML
    assert "window.localStorage.getItem(authTokenStorageKey)" in INDEX_HTML
    assert "window.localStorage.removeItem(authTokenStorageKey)" in INDEX_HTML
    assert "window.localStorage.setItem(authTokenStorageKey, authToken)" in INDEX_HTML
    assert "localStorage.getItem('screen_windows_token')" not in INDEX_HTML
    assert "localStorage.removeItem('screen_windows_token')" not in INDEX_HTML
    assert "localStorage.setItem('screen_windows_token'" not in INDEX_HTML


def test_webui_wraps_signal_sends_for_disconnect_races() -> None:
    assert "function sendSocketMessage(socket, payload, { requireReady = false } = {})" in INDEX_HTML
    assert "try {" in INDEX_HTML
    assert "socket.send(JSON.stringify(payload));" in INDEX_HTML
    assert "logSignal('send failed'" in INDEX_HTML
    assert "function sendSignalMessage(payload, options)" in INDEX_HTML
    assert "signalSocket.send(JSON.stringify" not in INDEX_HTML


def test_webui_does_not_reuse_token_without_web_crypto_hmac() -> None:
    assert "function canSignAuthToken()" in INDEX_HTML
    assert "window.crypto.subtle.importKey" in INDEX_HTML
    assert "canReuseToken() && authToken && canSignAuthToken()" in INDEX_HTML
    assert "当前手机浏览器或 HTTP 环境不支持令牌复用" in INDEX_HTML
    assert "throw new Error('当前浏览器或 HTTP 环境不支持令牌签名" in INDEX_HTML


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
    assert "function applyStreamState(stream)" in INDEX_HTML
    assert "applyStreamState(payload.stream)" in INDEX_HTML
    assert '<option value="eco" selected>节能 720p24 / 2M</option>' in INDEX_HTML
    assert "eco: { width: 1280, height: 720, fps: 24, bitrate: 2 }" in INDEX_HTML


def test_webui_has_preview_lifecycle_and_view_controls() -> None:
    assert 'id="rebuildPreviewBtn"' in INDEX_HTML
    assert 'id="fitModeBtn"' in INDEX_HTML
    assert 'id="fullscreenBtn"' in INDEX_HTML
    assert "async function stopPreview" in INDEX_HTML
    assert "type: 'webrtc_close'" in INDEX_HTML
    assert "streamBtn.textContent = active ? '停止画面预览' : '2. 启动画面预览';" in INDEX_HTML
    assert "if (!controlSurface.requestFullscreen)" in INDEX_HTML
    assert "controlSurface.requestFullscreen()" in INDEX_HTML
    assert "全屏被浏览器拦截" in INDEX_HTML
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


def test_webui_connection_button_toggles_disconnect_state() -> None:
    assert "function updateConnectButton(connected, connecting = false)" in INDEX_HTML
    assert 'maxlength="6"' in INDEX_HTML
    assert "function normalizedPin()" in INDEX_HTML
    assert "connectBtn.textContent = connected ? '断开主机'" in INDEX_HTML
    assert "async function disconnectSignalSession" in INDEX_HTML
    assert "await disconnectSignalSession();" in INDEX_HTML
    assert "updateConnectButton(true);" in INDEX_HTML


def test_webui_exposes_mobile_text_input() -> None:
    assert 'id="remoteTextInput"' in INDEX_HTML
    assert 'id="remoteTextSendBtn"' in INDEX_HTML
    assert "function sendTextInput(text)" in INDEX_HTML
    assert "events: [{ type: 'text', text }]" in INDEX_HTML
    assert "isEditableTarget(event.target)" in INDEX_HTML
    assert "单次最多发送 500 个字符" in INDEX_HTML


def test_webui_uses_touchpad_style_mobile_control() -> None:
    assert "let remoteCursor = null;" in INDEX_HTML
    assert "let lastRemoteCursor = null;" in INDEX_HTML
    assert "const touchPointerScale = 1.35;" in INDEX_HTML
    assert "function moveRemoteCursorBy(deltaX, deltaY)" in INDEX_HTML
    assert "setRemoteCursor(lastRemoteCursor || defaultRemoteCursor(), { send: false })" in INDEX_HTML
    assert "remoteCursor.x + (deltaX * touchPointerScale)" in INDEX_HTML
    assert "手机使用触摸板模式" in INDEX_HTML
    assert "sendMouseClick(touchState.count >= 2 ? 'right' : 'left')" in INDEX_HTML


def test_webui_shows_remote_cursor_indicator_for_touchpad_control() -> None:
    assert 'id="remoteCursorIndicator"' in INDEX_HTML
    assert ".remote-cursor.visible" in INDEX_HTML
    assert "function ensureVisibleRemoteCursor()" in INDEX_HTML
    assert "ensureVisibleRemoteCursor();" in INDEX_HTML
    assert "function renderRemoteCursorIndicator()" in INDEX_HTML
    assert "remoteCursorIndicator.style.transform" in INDEX_HTML
    assert "renderRemoteCursorIndicator();" in INDEX_HTML
    assert "hideRemoteCursorIndicator();" in INDEX_HTML
    assert "function migrateRemoteCursor(previousStream, nextStream)" in INDEX_HTML
    assert "migrateRemoteCursor(previousStream, hostInfo.stream)" in INDEX_HTML
    assert "setRemoteCursor(lastRemoteCursor || defaultRemoteCursor(), { send: false })" in INDEX_HTML
