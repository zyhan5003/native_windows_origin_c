from __future__ import annotations


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>screen_windows</title>
    <style>
      :root {
        color-scheme: light;
        --bg-1: #edf3f8;
        --bg-2: #dfe7f0;
        --panel: rgba(8, 16, 27, 0.88);
        --panel-soft: rgba(255, 255, 255, 0.08);
        --text: #eff5fb;
        --muted: #9eb0c2;
        --accent: #88f06d;
        --accent-2: #ffb84f;
        --border: rgba(255, 255, 255, 0.14);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Bahnschrift", "Segoe UI", "Microsoft YaHei", sans-serif;
        background:
          radial-gradient(circle at top left, rgba(109, 210, 255, 0.34) 0, transparent 22%),
          radial-gradient(circle at right 20%, rgba(136, 240, 109, 0.22) 0, transparent 18%),
          linear-gradient(150deg, var(--bg-1) 0%, var(--bg-2) 100%);
        color: var(--text);
      }
      .app {
        width: min(1180px, calc(100vw - 32px));
        margin: 22px auto;
        display: grid;
        gap: 18px;
      }
      .hero {
        display: grid;
        grid-template-columns: 1.1fr 0.9fr;
        gap: 18px;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 26px;
        padding: 22px;
        box-shadow: 0 18px 60px rgba(8, 18, 33, 0.2);
        backdrop-filter: blur(18px);
      }
      h1 {
        margin: 0 0 10px;
        font-size: clamp(30px, 4vw, 52px);
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }
      p {
        margin: 0 0 16px;
        color: var(--muted);
        line-height: 1.6;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 8px 14px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid var(--border);
        color: #ffffff;
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .accent-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 18px var(--accent);
      }
      .hero-copy {
        display: grid;
        gap: 18px;
      }
      .metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }
      .metric {
        padding: 14px 16px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
      }
      .metric strong {
        display: block;
        font-size: 22px;
        margin-bottom: 6px;
      }
      .metric span {
        color: var(--muted);
        font-size: 12px;
      }
      .controls {
        display: grid;
        gap: 12px;
      }
      .field {
        display: grid;
        gap: 8px;
      }
      .field label {
        color: var(--muted);
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .field input,
      .field textarea,
      .field select {
        width: 100%;
        padding: 14px 16px;
        border-radius: 16px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.05);
        color: var(--text);
        outline: none;
      }
      .field select option {
        color: #07111d;
      }
      .field textarea {
        min-height: 110px;
        resize: vertical;
        font: inherit;
        line-height: 1.45;
      }
      .field input:focus,
      .field textarea:focus {
        border-color: rgba(136, 240, 109, 0.7);
        box-shadow: 0 0 0 4px rgba(136, 240, 109, 0.12);
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
      }
      .file-list {
        display: grid;
        gap: 8px;
      }
      .file-item {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
        padding: 10px 12px;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
      }
      .file-item span {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .file-item a {
        color: var(--accent);
        text-decoration: none;
        white-space: nowrap;
      }
      .control-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
      }
      button {
        border: 0;
        border-radius: 16px;
        padding: 13px 18px;
        font: inherit;
        cursor: pointer;
        transition: transform 160ms ease, opacity 160ms ease, background 160ms ease;
      }
      button:hover {
        transform: translateY(-1px);
      }
      button:disabled {
        opacity: 0.45;
        cursor: not-allowed;
        transform: none;
      }
      .primary {
        background: linear-gradient(120deg, var(--accent), #c0ff8d);
        color: #04130a;
      }
      .secondary {
        background: rgba(255, 255, 255, 0.08);
        color: var(--text);
        border: 1px solid var(--border);
      }
      .workspace {
        display: grid;
        grid-template-columns: 1.4fr 0.6fr;
        gap: 18px;
      }
      .video-shell {
        position: relative;
        overflow: hidden;
        min-height: 540px;
      }
      .video-stage {
        aspect-ratio: 16 / 9;
        width: 100%;
        border-radius: 20px;
        background:
          linear-gradient(160deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.08)),
          #070f18;
        border: 1px solid rgba(255, 255, 255, 0.1);
        overflow: hidden;
        position: relative;
        outline: none;
        touch-action: none;
      }
      .video-stage.control-armed {
        box-shadow: 0 0 0 2px rgba(136, 240, 109, 0.95), 0 0 0 10px rgba(136, 240, 109, 0.08);
      }
      video {
        width: 100%;
        height: 100%;
        display: block;
        background: #060d16;
        object-fit: contain;
      }
      .overlay {
        position: absolute;
        left: 18px;
        bottom: 18px;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
        border-radius: 999px;
        background: rgba(5, 10, 17, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #f4f8fb;
        font-size: 12px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }
      .status-list {
        display: grid;
        gap: 12px;
      }
      .status-card {
        padding: 14px 16px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
      }
      .status-card strong {
        display: block;
        margin-bottom: 8px;
        font-size: 13px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      code, pre {
        display: block;
        margin: 0;
        padding: 12px;
        border-radius: 14px;
        background: #09121d;
        color: #d7e5f2;
        overflow: auto;
        font-family: "Cascadia Code", "Consolas", monospace;
        font-size: 12px;
        line-height: 1.5;
      }
      .status-line {
        color: #ffffff;
        font-size: 14px;
      }
      .status-line em {
        color: var(--accent-2);
        font-style: normal;
      }
      @media (max-width: 920px) {
        .hero,
        .workspace {
          grid-template-columns: 1fr;
        }
        .metrics {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <main class="app">
      <section class="hero">
        <section class="panel hero-copy">
          <span class="badge"><span class="accent-dot"></span>screen_windows host</span>
          <div>
            <h1>LAN Control Deck</h1>
            <p>这一版直接打通浏览器预览链路：控制端通过 WebSocket 鉴权和信令，与受控端建立 WebRTC 视频会话。当前默认视频源为可替换的合成帧，后续无缝接入 DXcam / FFmpeg。</p>
          </div>
          <div class="metrics">
            <div class="metric">
              <strong>WebRTC</strong>
              <span>UDP 视频主链路已接入</span>
            </div>
            <div class="metric">
              <strong>Auth</strong>
              <span>PIN / Token 复用会话</span>
            </div>
            <div class="metric">
              <strong>Signal</strong>
              <span>WebSocket 独立端口</span>
            </div>
          </div>
        </section>

        <section class="panel controls">
          <div class="field">
            <label for="pin">Pairing PIN</label>
            <input id="pin" inputmode="numeric" placeholder="首次连接输入 6 位 PIN" />
          </div>
          <div class="actions">
            <button id="connectBtn" class="primary">建立控制会话</button>
            <button id="streamBtn" class="secondary" disabled>启动视频预览</button>
            <button id="controlBtn" class="secondary" disabled>启用远程控制</button>
            <button id="resetBtn" class="secondary">清除本地令牌</button>
          </div>
          <div class="status-card">
            <strong>会话状态</strong>
            <div id="sessionStatus" class="status-line">等待连接</div>
          </div>
          <div class="status-card">
            <strong>控制状态</strong>
            <div id="controlStatus" class="status-line">未启用</div>
          </div>
          <div class="status-card">
            <strong>健康检查</strong>
            <code id="health">loading...</code>
          </div>
        </section>
      </section>

      <section class="workspace">
        <section class="panel video-shell">
          <div id="controlSurface" class="video-stage" tabindex="0">
            <video id="remoteVideo" autoplay playsinline muted></video>
            <div class="overlay" id="videoOverlay">signal idle</div>
          </div>
        </section>

        <section class="panel status-list">
          <div class="status-card">
            <strong>剪贴板</strong>
            <div class="field">
              <label for="clipboardText">Text</label>
              <textarea id="clipboardText" placeholder="文本剪贴板内容"></textarea>
            </div>
            <div class="actions">
              <button id="clipboardReadBtn" class="secondary" disabled>读取主机</button>
              <button id="clipboardWriteBtn" class="secondary" disabled>写入主机</button>
            </div>
            <div id="clipboardStatus" class="status-line">等待认证</div>
          </div>
          <div class="status-card">
            <strong>文件传输</strong>
            <div class="field">
              <label for="fileInput">Upload</label>
              <input id="fileInput" type="file" />
            </div>
            <div class="actions">
              <button id="fileUploadBtn" class="secondary" disabled>上传到主机</button>
              <button id="fileRefreshBtn" class="secondary" disabled>刷新列表</button>
            </div>
            <div id="fileStatus" class="status-line">等待认证</div>
            <div id="fileList" class="file-list"></div>
          </div>
          <div class="status-card">
            <strong>自适应质量</strong>
            <div class="field">
              <label for="qualityMode">Mode</label>
              <select id="qualityMode">
                <option value="auto">自动调节</option>
                <option value="manual">手动锁定</option>
              </select>
            </div>
            <div class="field">
              <label for="qualityProfile">Profile</label>
              <select id="qualityProfile">
                <option value="turbo">极速 60fps / 20Mbps</option>
                <option value="fast">高速 60fps / 10Mbps</option>
                <option value="standard" selected>标准 30fps / 5Mbps</option>
                <option value="eco">节能 30fps / 2Mbps</option>
                <option value="limit">极限 15fps / 0.5Mbps</option>
              </select>
            </div>
            <div class="actions">
              <button id="qualityApplyBtn" class="secondary" disabled>应用质量</button>
            </div>
            <div id="qualityStatus" class="status-line">等待认证</div>
          </div>
          <div class="status-card">
            <strong>显示器</strong>
            <div class="field">
              <label for="displaySelect">Monitor</label>
              <select id="displaySelect"></select>
            </div>
            <div class="actions">
              <button id="displayApplyBtn" class="secondary" disabled>切换显示器</button>
            </div>
            <div id="displayStatus" class="status-line">等待认证</div>
          </div>
          <div class="status-card">
            <strong>信令日志</strong>
            <pre id="signalLog">尚未建立连接。</pre>
          </div>
          <div class="status-card">
            <strong>媒体状态</strong>
            <pre id="mediaLog">尚未开始会话。</pre>
          </div>
        </section>
      </section>
    </main>
    <script>
      let hostInfo = null;
      let signalSocket = null;
      let signalReadyPromise = null;
      let resolveSignalReady = null;
      let rejectSignalReady = null;
      let signalReady = false;
      let authToken = localStorage.getItem('screen_windows_token') || '';
      let peerConnection = null;
      let previewDesired = false;
      let reconnectingSignal = false;
      let reconnectTimer = null;
      let reconnectAttempts = 0;
      let autoReconnectPaused = false;
      let controlActive = false;
      let inputSequence = 0;
      let pendingInputEvents = [];
      let activeFileUpload = null;
      let fileAccessTicket = '';
      let fileAccessExpiresAt = 0;
      let fileAccessPromise = null;
      let resolveFileAccess = null;
      let rejectFileAccess = null;
      let qualityEnabled = false;
      let qualityStatsTimer = null;
      let qualityRenegotiateTimer = null;
      let activeNegotiatedProfileKey = null;
      let pendingRenegotiateProfileKey = null;
      let qualityRenegotiating = false;
      let previousInboundVideoStats = null;
      let controlPingTimer = null;
      let latestControlRttMs = null;
      let statsTimer = null;
      let displayEnabled = false;
      let touchState = null;

      const healthEl = document.getElementById('health');
      const sessionStatusEl = document.getElementById('sessionStatus');
      const controlStatusEl = document.getElementById('controlStatus');
      const signalLogEl = document.getElementById('signalLog');
      const mediaLogEl = document.getElementById('mediaLog');
      const overlayEl = document.getElementById('videoOverlay');
      const remoteVideo = document.getElementById('remoteVideo');
      const controlSurface = document.getElementById('controlSurface');
      const connectBtn = document.getElementById('connectBtn');
      const streamBtn = document.getElementById('streamBtn');
      const controlBtn = document.getElementById('controlBtn');
      const resetBtn = document.getElementById('resetBtn');
      const pinInput = document.getElementById('pin');
      const clipboardText = document.getElementById('clipboardText');
      const clipboardReadBtn = document.getElementById('clipboardReadBtn');
      const clipboardWriteBtn = document.getElementById('clipboardWriteBtn');
      const clipboardStatusEl = document.getElementById('clipboardStatus');
      const fileInput = document.getElementById('fileInput');
      const fileUploadBtn = document.getElementById('fileUploadBtn');
      const fileRefreshBtn = document.getElementById('fileRefreshBtn');
      const fileStatusEl = document.getElementById('fileStatus');
      const fileListEl = document.getElementById('fileList');
      const qualityMode = document.getElementById('qualityMode');
      const qualityProfile = document.getElementById('qualityProfile');
      const qualityApplyBtn = document.getElementById('qualityApplyBtn');
      const qualityStatusEl = document.getElementById('qualityStatus');
      const displaySelect = document.getElementById('displaySelect');
      const displayApplyBtn = document.getElementById('displayApplyBtn');
      const displayStatusEl = document.getElementById('displayStatus');

      function updateSessionStatus(text, accent = false) {
        sessionStatusEl.innerHTML = accent ? `<em>${text}</em>` : text;
      }

      function logSignal(message, payload) {
        const rows = [new Date().toLocaleTimeString(), message];
        if (payload !== undefined) {
          rows.push(JSON.stringify(payload, null, 2));
        }
        signalLogEl.textContent = rows.join('\\n');
      }

      function logMedia(message, payload) {
        const rows = [new Date().toLocaleTimeString(), message];
        if (payload !== undefined) {
          rows.push(JSON.stringify(payload, null, 2));
        }
        mediaLogEl.textContent = rows.join('\\n');
      }

      function updateControlState(active, message) {
        controlActive = active;
        controlSurface.classList.toggle('control-armed', active);
        controlBtn.textContent = active ? '停止远程控制' : '启用远程控制';
        controlStatusEl.innerHTML = active ? `<em>${message}</em>` : message;
        if (active) {
          controlSurface.focus();
        }
      }

      function updateClipboardControls(enabled, message) {
        clipboardReadBtn.disabled = !enabled;
        clipboardWriteBtn.disabled = !enabled;
        clipboardStatusEl.innerHTML = enabled ? `<em>${message}</em>` : message;
      }

      function updateFileControls(enabled, message) {
        fileUploadBtn.disabled = !enabled;
        fileRefreshBtn.disabled = !enabled;
        fileStatusEl.innerHTML = enabled ? `<em>${message}</em>` : message;
      }

      function formatBytes(size) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let value = Number(size) || 0;
        let unitIndex = 0;
        while (value >= 1024 && unitIndex < units.length - 1) {
          value /= 1024;
          unitIndex += 1;
        }
        return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
      }

      function renderFileList(files) {
        fileListEl.textContent = '';
        if (!files || files.length === 0) {
          const empty = document.createElement('div');
          empty.className = 'status-line';
          empty.textContent = '暂无可下载文件';
          fileListEl.appendChild(empty);
          return;
        }

        files.forEach((file) => {
          const item = document.createElement('div');
          item.className = 'file-item';

          const name = document.createElement('span');
          name.textContent = `${file.name} · ${formatBytes(file.size)}`;

          const link = document.createElement('a');
          const ticketQuery = fileAccessTicket ? `?ticket=${encodeURIComponent(fileAccessTicket)}` : '';
          link.href = `/api/files/${encodeURIComponent(file.name)}${ticketQuery}`;
          link.download = file.name;
          link.textContent = '下载';

          item.appendChild(name);
          item.appendChild(link);
          fileListEl.appendChild(item);
        });
      }

      function fileAccessQuery() {
        return fileAccessTicket ? `?ticket=${encodeURIComponent(fileAccessTicket)}` : '';
      }

      async function ensureFileAccessTicket() {
        if (authMode() === 'none') {
          fileAccessTicket = '';
          fileAccessExpiresAt = 0;
          return;
        }
        if (fileAccessTicket && Date.now() < fileAccessExpiresAt - 10000) {
          return;
        }
        if (fileAccessPromise) {
          await fileAccessPromise;
          return;
        }
        await openSignalSession();
        fileAccessPromise = new Promise((resolve, reject) => {
          resolveFileAccess = resolve;
          rejectFileAccess = reject;
        });
        signalSocket.send(JSON.stringify({ type: 'file_access' }));
        fileStatusEl.innerHTML = '<em>正在申请文件访问票据...</em>';
        await fileAccessPromise;
      }

      async function refreshFileList() {
        try {
          await ensureFileAccessTicket();
          const response = await fetch(`/api/files${fileAccessQuery()}`);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const payload = await response.json();
          renderFileList(payload.files || []);
        } catch (error) {
          fileStatusEl.textContent = `文件列表错误: ${error}`;
        }
      }

      function updateQualityControls(enabled, message) {
        qualityEnabled = enabled;
        qualityApplyBtn.disabled = !enabled;
        qualityStatusEl.innerHTML = enabled ? `<em>${message}</em>` : message;
      }

      function updateDisplayControls(enabled, message) {
        displayEnabled = enabled;
        displayApplyBtn.disabled = !enabled;
        displayStatusEl.innerHTML = enabled ? `<em>${message}</em>` : message;
      }

      function renderDisplayInfo(displayInfo) {
        if (!displayInfo || !Array.isArray(displayInfo.monitors)) {
          return;
        }
        displaySelect.innerHTML = '';
        displayInfo.monitors.forEach((monitor) => {
          const option = document.createElement('option');
          option.value = String(monitor.id);
          option.textContent = `#${monitor.id} ${monitor.width}x${monitor.height}${monitor.primary ? ' 主屏' : ''}`;
          displaySelect.appendChild(option);
        });
        displaySelect.value = String(displayInfo.selected_monitor || 0);
        updateDisplayControls(true, `当前显示器 #${displaySelect.value}`);
      }

      function renderQualityState(state) {
        if (!state || !state.profile) {
          return;
        }
        qualityMode.value = state.mode || 'auto';
        qualityProfile.value = state.profile.key || 'standard';
        const profile = state.profile;
        const pending = state.pending_profile ? `，候选 ${state.pending_profile.name}` : '';
        qualityStatusEl.innerHTML = `<em>${profile.name} ${profile.width}x${profile.height} @ ${profile.fps}fps / ${profile.bitrate_mbps}Mbps${pending}</em>`;
      }

      function stopQualityStatsReporter() {
        if (qualityStatsTimer !== null) {
          window.clearInterval(qualityStatsTimer);
          qualityStatsTimer = null;
        }
        previousInboundVideoStats = null;
      }

      function clearQualityRenegotiateTimer() {
        if (qualityRenegotiateTimer !== null) {
          window.clearTimeout(qualityRenegotiateTimer);
          qualityRenegotiateTimer = null;
        }
        pendingRenegotiateProfileKey = null;
      }

      function stopControlPingReporter() {
        if (controlPingTimer !== null) {
          window.clearInterval(controlPingTimer);
          controlPingTimer = null;
        }
        latestControlRttMs = null;
      }

      function stopStatsReporter() {
        if (statsTimer !== null) {
          window.clearInterval(statsTimer);
          statsTimer = null;
        }
      }

      function clearReconnectTimer() {
        if (reconnectTimer !== null) {
          window.clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
      }

      function clearStoredAuthToken() {
        localStorage.removeItem('screen_windows_token');
        authToken = '';
      }

      function rejectPendingSignalReady(error) {
        if (rejectSignalReady) {
          rejectSignalReady(error);
        }
        resolveSignalReady = null;
        rejectSignalReady = null;
        signalReadyPromise = null;
        signalReady = false;
      }

      async function closeLocalPreviewAfterSignalLoss() {
        stopQualityStatsReporter();
        clearQualityRenegotiateTimer();
        activeNegotiatedProfileKey = null;
        if (peerConnection) {
          const closingConnection = peerConnection;
          await closingConnection.close();
          if (peerConnection === closingConnection) {
            peerConnection = null;
          }
        }
        remoteVideo.srcObject = null;
        controlBtn.disabled = true;
      }

      function scheduleSignalReconnect() {
        if (!canAutoReconnect() || reconnectTimer !== null) {
          return;
        }
        const delayMs = Math.min(3000, 500 * (2 ** reconnectAttempts));
        reconnectAttempts += 1;
        reconnectingSignal = true;
        updateSessionStatus(`控制通道断开，${delayMs}ms 后自动重连...`, true);
        reconnectTimer = window.setTimeout(async () => {
          reconnectTimer = null;
          try {
            await openSignalSession();
          } catch (error) {
            logSignal('reconnect failed', { error: String(error) });
            scheduleSignalReconnect();
          }
        }, delayMs);
      }

      async function loadHealth() {
        const response = await fetch('/api/health');
        hostInfo = await response.json();
        healthEl.textContent = JSON.stringify(hostInfo, null, 2);
        overlayEl.textContent = `${hostInfo.stream.source} | ${hostInfo.stream.width}x${hostInfo.stream.height} @ ${hostInfo.stream.fps}fps`;
        renderQualityState(hostInfo.quality);
        renderDisplayInfo(hostInfo.stream && hostInfo.stream.display);
      }

      async function computeSignature(token, timestamp) {
        const key = await crypto.subtle.importKey(
          'raw',
          new TextEncoder().encode(token),
          { name: 'HMAC', hash: 'SHA-256' },
          false,
          ['sign']
        );
        const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(String(timestamp)));
        return Array.from(new Uint8Array(signature))
          .map((value) => value.toString(16).padStart(2, '0'))
          .join('');
      }

      function authMode() {
        return hostInfo && hostInfo.auth_mode ? String(hostInfo.auth_mode).toLowerCase() : 'pin_once';
      }

      function canReuseToken() {
        return authMode() !== 'always' && authMode() !== 'none';
      }

      function canAutoReconnect() {
        if (autoReconnectPaused) {
          return false;
        }
        return authMode() === 'none' || (canReuseToken() && Boolean(authToken));
      }

      function storeAuthToken(token) {
        if (!canReuseToken()) {
          clearStoredAuthToken();
          return;
        }
        authToken = token;
        localStorage.setItem('screen_windows_token', authToken);
      }

      async function openSignalSession() {
        if (!hostInfo) {
          await loadHealth();
        }
        if (signalSocket && signalSocket.readyState === WebSocket.OPEN && signalReady) {
          return;
        }
        if (signalSocket && signalSocket.readyState === WebSocket.OPEN && signalReadyPromise) {
          return signalReadyPromise;
        }
        if (signalSocket && signalSocket.readyState === WebSocket.CONNECTING && signalReadyPromise) {
          return signalReadyPromise;
        }

        const wsUrl = `ws://${location.hostname}:${hostInfo.ports.ws}`;
        const socket = new WebSocket(wsUrl);
        signalSocket = socket;
        signalReadyPromise = new Promise((resolve, reject) => {
          resolveSignalReady = resolve;
          rejectSignalReady = reject;
        });
        signalReady = false;
        updateSessionStatus('正在建立控制会话...', true);
        logSignal('connecting', { wsUrl });

        try {
          await new Promise((resolve, reject) => {
            socket.addEventListener('open', resolve, { once: true });
            socket.addEventListener('error', () => reject(new Error('WebSocket open failed')), { once: true });
          });
        } catch (error) {
          if (signalSocket === socket) {
            signalSocket = null;
          }
          rejectPendingSignalReady(error);
          throw error;
        }

        socket.addEventListener('close', () => {
          if (signalSocket === socket) {
            signalSocket = null;
          }
          signalReady = false;
          rejectPendingSignalReady(new Error('signal socket closed'));
          stopControlPingReporter();
          stopStatsReporter();
          streamBtn.disabled = true;
          updateClipboardControls(false, '连接关闭');
          updateFileControls(false, '连接关闭');
          updateQualityControls(false, '连接关闭');
          updateDisplayControls(false, '连接关闭');
          updateControlState(false, '连接关闭');
          updateSessionStatus('控制会话已关闭');
          overlayEl.textContent = 'signal closed';
          // 控制通道断开时服务端会释放旧 WebRTC 会话；本地先关旧预览，重连后再重建。
          closeLocalPreviewAfterSignalLoss().catch((error) => {
            logMedia('preview close failed after signal loss', { error: String(error) });
          });
          scheduleSignalReconnect();
        });

        socket.addEventListener('message', async (event) => {
          const payload = JSON.parse(event.data);
          logSignal('message', payload);

          if (payload.type === 'auth_ok') {
            storeAuthToken(payload.token);
            clearReconnectTimer();
            reconnectAttempts = 0;
            streamBtn.disabled = false;
            updateClipboardControls(Boolean(payload.capabilities && payload.capabilities.clipboard), '可同步');
            updateFileControls(Boolean(payload.capabilities && payload.capabilities.file_transfer), '可上传');
            updateQualityControls(Boolean(payload.capabilities && payload.capabilities.quality), '可调节');
            renderDisplayInfo(payload.display_info);
            updateSessionStatus('控制会话已认证', true);
            overlayEl.textContent = 'signal ready';
            startControlPingReporter();
            startStatsReporter();
            requestQualityState();
            signalReady = true;
            if (resolveSignalReady) {
              resolveSignalReady();
            }
            resolveSignalReady = null;
            rejectSignalReady = null;
            signalReadyPromise = null;
            // 文件列表是附属能力，不能阻塞视频预览主链路的认证完成。
            refreshFileList().catch((error) => {
              fileStatusEl.textContent = `文件列表错误: ${error}`;
            });
            if (reconnectingSignal && previewDesired) {
              reconnectingSignal = false;
              await startPreview();
            } else {
              reconnectingSignal = false;
            }
          }

          if (payload.type === 'pong') {
            const sentAt = Number(payload.t);
            if (Number.isFinite(sentAt)) {
              latestControlRttMs = Math.max(Date.now() - sentAt, 0);
              updateSessionStatus(`控制会话已认证，WS RTT ${latestControlRttMs}ms`, true);
              sendQualitySignals({ rtt_ms: latestControlRttMs });
            }
          }

          if (payload.type === 'auth_error') {
            if (authToken && pinInput.value.trim()) {
              clearStoredAuthToken();
              socket.send(JSON.stringify({
                type: 'auth',
                version: '0.1.0',
                pin: pinInput.value.trim(),
              }));
              updateSessionStatus('令牌失效，回退到 PIN 配对...', true);
              return;
            }
            if (authToken) {
              // token 失效时停止自动重连风暴，让用户明确重新输入 PIN。
              clearStoredAuthToken();
              clearReconnectTimer();
              autoReconnectPaused = true;
              reconnectingSignal = false;
              reconnectAttempts = 0;
              streamBtn.disabled = true;
              updateSessionStatus(`令牌失效，请重新输入 PIN: ${payload.reason}`);
              rejectPendingSignalReady(new Error(`auth failed: ${payload.reason}`));
              socket.close();
              return;
            }
            updateSessionStatus(`认证失败: ${payload.reason}`);
            rejectPendingSignalReady(new Error(`auth failed: ${payload.reason}`));
          }

          if (payload.type === 'webrtc_answer') {
            await peerConnection.setRemoteDescription({
              type: payload.description_type,
              sdp: payload.sdp,
            });
            logMedia('remote description applied');
          }

          if (payload.type === 'input_ack') {
            controlStatusEl.innerHTML = `<em>批次 ${payload.seq} 已处理 ${payload.processed_events} 个事件</em>`;
          }

          if (payload.type === 'clipboard_text') {
            clipboardText.value = payload.text || '';
            clipboardStatusEl.innerHTML = `<em>已读取 ${clipboardText.value.length} 个字符</em>`;
          }

          if (payload.type === 'clipboard_ack') {
            clipboardStatusEl.innerHTML = `<em>已写入 ${payload.text_length} 个字符</em>`;
            await loadHealth();
          }

          if (payload.type === 'clipboard_error') {
            clipboardStatusEl.textContent = `剪贴板错误: ${payload.reason}`;
          }

          if (payload.type === 'file_ready' || payload.type === 'file_chunk_ack') {
            if (activeFileUpload && payload.id === activeFileUpload.id) {
              await sendNextFileChunk(payload.offset);
            }
          }

          if (payload.type === 'file_complete') {
            if (activeFileUpload && payload.id === activeFileUpload.id) {
              fileStatusEl.innerHTML = `<em>已上传 ${payload.name} (${payload.size} bytes)</em>`;
              activeFileUpload = null;
              fileUploadBtn.disabled = false;
              await loadHealth();
              await refreshFileList();
            }
          }

          if (payload.type === 'file_error') {
            fileStatusEl.textContent = `文件错误: ${payload.reason}`;
            activeFileUpload = null;
            fileUploadBtn.disabled = false;
          }

          if (payload.type === 'file_access') {
            fileAccessTicket = payload.ticket || '';
            fileAccessExpiresAt = Date.now() + (Number(payload.expires_in_seconds || 0) * 1000);
            if (resolveFileAccess) {
              resolveFileAccess();
            }
            fileAccessPromise = null;
            resolveFileAccess = null;
            rejectFileAccess = null;
          }

          if (payload.type === 'quality_state') {
            renderQualityState(payload.quality);
            if (hostInfo) {
              hostInfo.quality = payload.quality;
              healthEl.textContent = JSON.stringify(hostInfo, null, 2);
            }
            scheduleQualityRenegotiation(payload.quality);
          }

          if (payload.type === 'quality_error') {
            qualityStatusEl.textContent = `质量错误: ${payload.reason}`;
          }

          if (payload.type === 'stats') {
            renderRuntimeStats(payload.runtime);
          }

          if (payload.type === 'display_state') {
            await applyDisplayState(payload);
          }

          if (payload.type === 'display_error') {
            displayStatusEl.textContent = `显示器错误: ${payload.reason}`;
          }
        });

        const timestamp = Math.floor(Date.now() / 1000);
        if (!canReuseToken() && authToken) {
          clearStoredAuthToken();
        }
        if (pinInput.value.trim() || authMode() === 'none') {
          autoReconnectPaused = false;
        }
        if (canReuseToken() && authToken) {
          const signature = await computeSignature(authToken, timestamp);
          socket.send(JSON.stringify({
            type: 'auth',
            version: '0.1.0',
            token: authToken,
            timestamp,
            signature,
          }));
          updateSessionStatus('尝试复用本地令牌...', true);
        } else {
          const authPayload = {
            type: 'auth',
            version: '0.1.0',
          };
          if (authMode() !== 'none') {
            authPayload.pin = pinInput.value.trim();
          }
          socket.send(JSON.stringify(authPayload));
          updateSessionStatus(authMode() === 'none' ? '无认证模式握手...' : '使用 PIN 发起配对...', true);
        }
        return signalReadyPromise;
      }

      async function waitForIceGatheringComplete(connection, timeoutMs = 3000) {
        if (connection.iceGatheringState === 'complete') {
          return true;
        }

        return await new Promise((resolve) => {
          let done = false;
          const finish = (completed) => {
            if (done) {
              return;
            }
            done = true;
            window.clearTimeout(timer);
            connection.removeEventListener('icegatheringstatechange', handler);
            resolve(completed);
          };
          const handler = () => {
            if (connection.iceGatheringState === 'complete') {
              finish(true);
            }
          };
          // 局域网无 STUN/TURN 时，部分 Chrome 环境不会及时触发 complete；超时后继续用已收集候选协商。
          const timer = window.setTimeout(() => finish(false), timeoutMs);
          connection.addEventListener('icegatheringstatechange', handler);
        });
      }

      async function startPreview() {
        await openSignalSession();
        if (!signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          throw new Error('signal socket not ready');
        }
        previewDesired = true;
        clearQualityRenegotiateTimer();

        if (peerConnection) {
          stopQualityStatsReporter();
          await peerConnection.close();
        }

        peerConnection = new RTCPeerConnection({ iceServers: [] });
        const connection = peerConnection;
        connection.addTransceiver('video', { direction: 'recvonly' });

        connection.addEventListener('track', (event) => {
          remoteVideo.srcObject = event.streams[0];
          overlayEl.textContent = 'video live';
          controlBtn.disabled = false;
          logMedia('remote track attached', {
            kind: event.track.kind,
            streams: event.streams.length,
          });
        });

        connection.addEventListener('connectionstatechange', () => {
          logMedia('connectionstatechange', { state: connection.connectionState });
          if (['failed', 'closed', 'disconnected'].includes(connection.connectionState)) {
            stopQualityStatsReporter();
          }
        });

        const offer = await connection.createOffer();
        await connection.setLocalDescription(offer);
        const iceComplete = await waitForIceGatheringComplete(connection);

        signalSocket.send(JSON.stringify({
          type: 'webrtc_offer',
          description_type: connection.localDescription.type,
          sdp: connection.localDescription.sdp,
        }));
        activeNegotiatedProfileKey = hostInfo && hostInfo.quality && hostInfo.quality.profile
          ? hostInfo.quality.profile.key
          : null;
        startQualityStatsReporter();
        overlayEl.textContent = 'negotiating';
        logMedia('offer sent', {
          type: connection.localDescription.type,
          iceComplete,
          iceGatheringState: connection.iceGatheringState,
        });
      }

      function scheduleQualityRenegotiation(state) {
        if (!state || !state.profile || !previewDesired || !peerConnection) {
          return;
        }
        if (!signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        const nextProfileKey = state.profile.key;
        if (!activeNegotiatedProfileKey || activeNegotiatedProfileKey === nextProfileKey) {
          return;
        }
        if (pendingRenegotiateProfileKey === nextProfileKey && qualityRenegotiateTimer !== null) {
          return;
        }
        clearQualityRenegotiateTimer();
        pendingRenegotiateProfileKey = nextProfileKey;
        const delayMs = state.mode === 'manual' ? 300 : 2500;
        qualityStatusEl.innerHTML = `<em>${state.profile.name} 已生效，${delayMs}ms 后重协商码率</em>`;
        qualityRenegotiateTimer = window.setTimeout(async () => {
          qualityRenegotiateTimer = null;
          const scheduledProfileKey = pendingRenegotiateProfileKey;
          pendingRenegotiateProfileKey = null;
          if (!scheduledProfileKey || qualityRenegotiating) {
            return;
          }
          if (!previewDesired || !peerConnection || activeNegotiatedProfileKey === scheduledProfileKey) {
            return;
          }
          qualityRenegotiating = true;
          try {
            logMedia('quality renegotiation', {
              from: activeNegotiatedProfileKey,
              to: scheduledProfileKey,
            });
            await startPreview();
          } catch (error) {
            logMedia('quality renegotiation failed', { error: String(error) });
          } finally {
            qualityRenegotiating = false;
          }
        }, delayMs);
      }

      async function closePreviewForDisplaySwitch() {
        previewDesired = false;
        activeNegotiatedProfileKey = null;
        clearQualityRenegotiateTimer();
        stopQualityStatsReporter();
        updateControlState(false, '显示器已切换，请重新启动视频预览');
        controlBtn.disabled = true;
        if (peerConnection) {
          await peerConnection.close();
          peerConnection = null;
        }
        remoteVideo.srcObject = null;
        streamBtn.disabled = false;
      }

      async function applyDisplayState(payload) {
        if (hostInfo) {
          hostInfo.stream = {
            ...hostInfo.stream,
            ...payload.stream,
            display: payload.display,
          };
          healthEl.textContent = JSON.stringify(hostInfo, null, 2);
        }
        renderDisplayInfo(payload.display);
        overlayEl.textContent = `${payload.stream.source} | ${payload.stream.width}x${payload.stream.height} @ ${payload.stream.fps}fps`;
        displayStatusEl.innerHTML = `<em>已切换到 #${payload.display.selected_monitor}，请重新启动预览</em>`;
        await closePreviewForDisplaySwitch();
      }

      function applyDisplaySelection() {
        if (!displayEnabled || !signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        signalSocket.send(JSON.stringify({
          type: 'display_switch',
          monitor: Number(displaySelect.value),
        }));
        displayStatusEl.innerHTML = '<em>正在切换...</em>';
      }

      function pushInputEvent(eventPayload) {
        if (!controlActive || !signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }

        if (eventPayload.type === 'mouse_move') {
          const index = pendingInputEvents.findIndex((item) => item.type === 'mouse_move');
          if (index >= 0) {
            pendingInputEvents[index] = eventPayload;
            return;
          }
        }

        if (eventPayload.type === 'mouse_wheel') {
          const index = pendingInputEvents.findIndex((item) => item.type === 'mouse_wheel');
          if (index >= 0) {
            pendingInputEvents[index].delta_y += eventPayload.delta_y;
            return;
          }
        }

        pendingInputEvents.push(eventPayload);
      }

      function flushInputEvents() {
        if (!controlActive || pendingInputEvents.length === 0) {
          return;
        }
        const payload = {
          type: 'input',
          seq: ++inputSequence,
          events: pendingInputEvents.splice(0, pendingInputEvents.length),
        };
        signalSocket.send(JSON.stringify(payload));
      }

      function requestQualityState() {
        if (!qualityEnabled || !signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        signalSocket.send(JSON.stringify({
          type: 'quality',
          action: 'state',
        }));
      }

      function startControlPingReporter() {
        stopControlPingReporter();
        sendControlPing();
        controlPingTimer = window.setInterval(sendControlPing, 2000);
      }

      function sendControlPing() {
        if (!signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        signalSocket.send(JSON.stringify({
          type: 'ping',
          t: Date.now(),
        }));
      }

      function startStatsReporter() {
        stopStatsReporter();
        requestRuntimeStats();
        statsTimer = window.setInterval(requestRuntimeStats, 2000);
      }

      function requestRuntimeStats() {
        if (!signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        signalSocket.send(JSON.stringify({ type: 'stats' }));
      }

      function renderRuntimeStats(runtime) {
        if (!runtime) {
          return;
        }
        if (hostInfo) {
          hostInfo.runtime = runtime;
          hostInfo.system = runtime.system || hostInfo.system;
          hostInfo.webrtc = runtime.webrtc || hostInfo.webrtc;
          hostInfo.quality = runtime.quality || hostInfo.quality;
          healthEl.textContent = JSON.stringify(hostInfo, null, 2);
        }
        const video = runtime.webrtc && runtime.webrtc.sessions && runtime.webrtc.sessions[0]
          ? runtime.webrtc.sessions[0].video
          : null;
        const system = runtime.system || {};
        logMedia('runtime stats', {
          uptime_seconds: runtime.uptime_seconds,
          cpu_percent: system.cpu_percent,
          memory_rss_mb: system.memory_rss_mb,
          active_webrtc_sessions: runtime.active_webrtc_sessions,
          video,
        });
      }

      function startQualityStatsReporter() {
        stopQualityStatsReporter();
        qualityStatsTimer = window.setInterval(reportQualityStats, 1000);
      }

      function maybeSetSignal(signals, key, value) {
        if (Number.isFinite(value)) {
          signals[key] = Number(value.toFixed(3));
        }
      }

      async function collectQualitySignals() {
        if (!peerConnection || peerConnection.connectionState === 'closed') {
          return null;
        }

        const report = await peerConnection.getStats();
        let inboundVideo = null;
        let candidatePair = null;
        let remoteInbound = null;

        report.forEach((stat) => {
          if (stat.type === 'inbound-rtp' && stat.kind === 'video' && !stat.isRemote) {
            inboundVideo = stat;
          }
          if (stat.type === 'candidate-pair' && stat.state === 'succeeded' && stat.nominated) {
            candidatePair = stat;
          }
          if (stat.type === 'remote-inbound-rtp' && stat.kind === 'video') {
            remoteInbound = stat;
          }
        });

        if (!inboundVideo) {
          return null;
        }

        const signals = {};
        const rttSeconds = candidatePair && Number.isFinite(candidatePair.currentRoundTripTime)
          ? candidatePair.currentRoundTripTime
          : (remoteInbound && Number.isFinite(remoteInbound.roundTripTime) ? remoteInbound.roundTripTime : null);
          if (rttSeconds !== null) {
            maybeSetSignal(signals, 'rtt_ms', rttSeconds * 1000);
          } else if (latestControlRttMs !== null) {
            maybeSetSignal(signals, 'rtt_ms', latestControlRttMs);
          }

        const availableBitrate = candidatePair && Number.isFinite(candidatePair.availableIncomingBitrate)
          ? candidatePair.availableIncomingBitrate
          : null;
        if (availableBitrate !== null && availableBitrate > 0) {
          // AQE 只用 WebRTC 可用带宽估计决策，避免静态画面低吞吐被误判成弱网。
          maybeSetSignal(signals, 'bandwidth_mbps', availableBitrate / 1000000);
        }

        if (previousInboundVideoStats) {
          const elapsedMs = inboundVideo.timestamp - previousInboundVideoStats.timestamp;
          const receivedBytes = inboundVideo.bytesReceived - previousInboundVideoStats.bytesReceived;
          const packetsReceived = inboundVideo.packetsReceived - previousInboundVideoStats.packetsReceived;
          const packetsLost = inboundVideo.packetsLost - previousInboundVideoStats.packetsLost;
          const packetTotal = packetsReceived + Math.max(packetsLost, 0);
          if (packetTotal > 0) {
            maybeSetSignal(signals, 'packet_loss', (Math.max(packetsLost, 0) / packetTotal) * 100);
          }
        }

        previousInboundVideoStats = {
          timestamp: inboundVideo.timestamp,
          bytesReceived: inboundVideo.bytesReceived || 0,
          packetsReceived: inboundVideo.packetsReceived || 0,
          packetsLost: inboundVideo.packetsLost || 0,
        };

        return Object.keys(signals).length > 0 ? signals : null;
      }

      function sendQualitySignals(signals) {
        if (!qualityEnabled || !signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        signalSocket.send(JSON.stringify({
          type: 'quality',
          action: 'signals',
          signals,
        }));
      }

      async function reportQualityStats() {
        if (!qualityEnabled || !signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        try {
          const signals = await collectQualitySignals();
          if (!signals) {
            return;
          }
          sendQualitySignals(signals);
        } catch (error) {
          logMedia('quality stats failed', { error: String(error) });
        }
      }

      function applyQualitySelection() {
        if (!qualityEnabled || !signalSocket || signalSocket.readyState !== WebSocket.OPEN) {
          return;
        }
        const mode = qualityMode.value;
        const payload = {
          type: 'quality',
          mode,
        };
        if (mode === 'manual') {
          payload.profile = qualityProfile.value;
        } else {
          payload.signals = {};
        }
        signalSocket.send(JSON.stringify(payload));
        qualityStatusEl.innerHTML = '<em>正在应用...</em>';
      }

      function getVideoContentRect() {
        const rect = remoteVideo.getBoundingClientRect();
        const fallbackAspect = hostInfo ? (hostInfo.stream.width / hostInfo.stream.height) : (16 / 9);
        const videoAspect = remoteVideo.videoWidth && remoteVideo.videoHeight
          ? remoteVideo.videoWidth / remoteVideo.videoHeight
          : fallbackAspect;
        const rectAspect = rect.width / rect.height;

        let width = rect.width;
        let height = rect.height;
        let left = rect.left;
        let top = rect.top;

        if (rectAspect > videoAspect) {
          height = rect.height;
          width = height * videoAspect;
          left = rect.left + ((rect.width - width) / 2);
        } else {
          width = rect.width;
          height = width / videoAspect;
          top = rect.top + ((rect.height - height) / 2);
        }

        return { left, top, width, height };
      }

      function mapPointerEvent(event) {
        if (!hostInfo) {
          return null;
        }
        const rect = getVideoContentRect();
        if (event.clientX < rect.left || event.clientX > rect.left + rect.width) {
          return null;
        }
        if (event.clientY < rect.top || event.clientY > rect.top + rect.height) {
          return null;
        }

        const ratioX = Math.max(0, Math.min((event.clientX - rect.left) / rect.width, 1));
        const ratioY = Math.max(0, Math.min((event.clientY - rect.top) / rect.height, 1));
        return {
          x: Math.round(ratioX * Math.max(hostInfo.stream.width - 1, 1)),
          y: Math.round(ratioY * Math.max(hostInfo.stream.height - 1, 1)),
        };
      }

      function mapMouseButton(button) {
        if (button === 0) return 'left';
        if (button === 1) return 'middle';
        if (button === 2) return 'right';
        return null;
      }

      function mapClientPoint(clientX, clientY) {
        return mapPointerEvent({ clientX, clientY });
      }

      function sendMouseClick(button) {
        pushInputEvent({ type: 'mouse_button', button, pressed: true });
        pushInputEvent({ type: 'mouse_button', button, pressed: false });
      }

      function touchCenter(touches) {
        let x = 0;
        let y = 0;
        for (let index = 0; index < touches.length; index += 1) {
          x += touches[index].clientX;
          y += touches[index].clientY;
        }
        return {
          x: x / Math.max(touches.length, 1),
          y: y / Math.max(touches.length, 1),
        };
      }

      function handleTouchStart(event) {
        if (!controlActive) {
          return;
        }
        event.preventDefault();
        const touches = Array.from(event.touches);
        const center = touchCenter(touches);
        touchState = {
          count: touches.length,
          startX: center.x,
          startY: center.y,
          lastX: center.x,
          lastY: center.y,
          startedAt: Date.now(),
          moved: false,
        };
        const mapped = mapClientPoint(center.x, center.y);
        if (mapped) {
          pushInputEvent({ type: 'mouse_move', x: mapped.x, y: mapped.y });
        }
      }

      function handleTouchMove(event) {
        if (!controlActive || !touchState) {
          return;
        }
        event.preventDefault();
        const touches = Array.from(event.touches);
        if (touches.length === 0) {
          return;
        }
        const center = touchCenter(touches);
        const mapped = mapClientPoint(center.x, center.y);
        const deltaY = center.y - touchState.lastY;
        if (Math.abs(center.x - touchState.startX) > 8 || Math.abs(center.y - touchState.startY) > 8) {
          touchState.moved = true;
        }
        if (touches.length >= 2) {
          pushInputEvent({ type: 'mouse_wheel', delta_y: Math.trunc(deltaY * 4) });
        } else if (mapped) {
          pushInputEvent({ type: 'mouse_move', x: mapped.x, y: mapped.y });
        }
        touchState.lastX = center.x;
        touchState.lastY = center.y;
      }

      function handleTouchEnd(event) {
        if (!controlActive || !touchState) {
          return;
        }
        event.preventDefault();
        const elapsed = Date.now() - touchState.startedAt;
        if (!touchState.moved && elapsed < 350) {
          sendMouseClick(touchState.count >= 2 ? 'right' : 'left');
        }
        if (event.touches.length === 0) {
          touchState = null;
        }
      }

      connectBtn.addEventListener('click', async () => {
        try {
          await openSignalSession();
        } catch (error) {
          updateSessionStatus(String(error));
          logSignal('connect failed', { error: String(error) });
        }
      });

      streamBtn.addEventListener('click', async () => {
        try {
          await startPreview();
        } catch (error) {
          overlayEl.textContent = 'preview failed';
          logMedia('preview failed', { error: String(error) });
        }
      });

      controlBtn.addEventListener('click', () => {
        if (controlActive) {
          updateControlState(false, '已停用');
          return;
        }
        updateControlState(true, '已启用，点击画面即可发送键鼠');
      });

      resetBtn.addEventListener('click', async () => {
        clearStoredAuthToken();
        autoReconnectPaused = true;
        updateControlState(false, '令牌已清除');
        updateSessionStatus('本地令牌已清除');
      });

      clipboardReadBtn.addEventListener('click', async () => {
        await openSignalSession();
        signalSocket.send(JSON.stringify({ type: 'clipboard_read' }));
        clipboardStatusEl.innerHTML = '<em>正在读取...</em>';
      });

      clipboardWriteBtn.addEventListener('click', async () => {
        await openSignalSession();
        signalSocket.send(JSON.stringify({
          type: 'clipboard_write',
          mime: 'text/plain',
          text: clipboardText.value,
        }));
        clipboardStatusEl.innerHTML = '<em>正在写入...</em>';
      });

      function bytesToBase64(bytes) {
        let binary = '';
        for (let index = 0; index < bytes.length; index += 1) {
          binary += String.fromCharCode(bytes[index]);
        }
        return btoa(binary);
      }

      async function sendNextFileChunk(offset) {
        if (!activeFileUpload) {
          return;
        }
        if (offset >= activeFileUpload.file.size) {
          signalSocket.send(JSON.stringify({
            type: 'file_req',
            id: activeFileUpload.id,
            action: 'complete',
          }));
          fileStatusEl.innerHTML = '<em>正在完成...</em>';
          return;
        }

        const end = Math.min(offset + activeFileUpload.chunkSize, activeFileUpload.file.size);
        const buffer = await activeFileUpload.file.slice(offset, end).arrayBuffer();
        signalSocket.send(JSON.stringify({
          type: 'file_chunk',
          id: activeFileUpload.id,
          offset,
          data: bytesToBase64(new Uint8Array(buffer)),
        }));
        const percent = Math.round((end / Math.max(activeFileUpload.file.size, 1)) * 100);
        fileStatusEl.innerHTML = `<em>上传中 ${percent}%</em>`;
      }

      fileUploadBtn.addEventListener('click', async () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) {
          fileStatusEl.textContent = '未选择文件';
          return;
        }
        await openSignalSession();
        activeFileUpload = {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          file,
          chunkSize: 64 * 1024,
        };
        fileUploadBtn.disabled = true;
        fileStatusEl.innerHTML = '<em>正在准备...</em>';
        signalSocket.send(JSON.stringify({
          type: 'file_req',
          id: activeFileUpload.id,
          action: 'send',
          name: file.name,
          size: file.size,
        }));
      });

      fileRefreshBtn.addEventListener('click', async () => {
        await refreshFileList();
      });

      qualityApplyBtn.addEventListener('click', async () => {
        await openSignalSession();
        applyQualitySelection();
      });

      displayApplyBtn.addEventListener('click', async () => {
        await openSignalSession();
        applyDisplaySelection();
      });

      controlSurface.addEventListener('mousemove', (event) => {
        const mapped = mapPointerEvent(event);
        if (!mapped) {
          return;
        }
        pushInputEvent({
          type: 'mouse_move',
          x: mapped.x,
          y: mapped.y,
        });
      });

      controlSurface.addEventListener('mousedown', (event) => {
        if (!controlActive) {
          return;
        }
        event.preventDefault();
        const mapped = mapPointerEvent(event);
        if (mapped) {
          pushInputEvent({
            type: 'mouse_move',
            x: mapped.x,
            y: mapped.y,
          });
        }
        const button = mapMouseButton(event.button);
        if (!button) {
          return;
        }
        pushInputEvent({
          type: 'mouse_button',
          button,
          pressed: true,
        });
      });

      controlSurface.addEventListener('mouseup', (event) => {
        if (!controlActive) {
          return;
        }
        event.preventDefault();
        const button = mapMouseButton(event.button);
        if (!button) {
          return;
        }
        pushInputEvent({
          type: 'mouse_button',
          button,
          pressed: false,
        });
      });

      controlSurface.addEventListener('wheel', (event) => {
        if (!controlActive) {
          return;
        }
        event.preventDefault();
        pushInputEvent({
          type: 'mouse_wheel',
          delta_y: Math.trunc(event.deltaY),
        });
      }, { passive: false });

      controlSurface.addEventListener('contextmenu', (event) => {
        if (controlActive) {
          event.preventDefault();
        }
      });

      controlSurface.addEventListener('touchstart', handleTouchStart, { passive: false });
      controlSurface.addEventListener('touchmove', handleTouchMove, { passive: false });
      controlSurface.addEventListener('touchend', handleTouchEnd, { passive: false });
      controlSurface.addEventListener('touchcancel', (event) => {
        event.preventDefault();
        touchState = null;
      }, { passive: false });

      window.addEventListener('keydown', (event) => {
        if (!controlActive || event.target === pinInput) {
          return;
        }
        event.preventDefault();
        if (event.repeat) {
          return;
        }
        pushInputEvent({
          type: 'key',
          code: event.code,
          pressed: true,
        });
      });

      window.addEventListener('keyup', (event) => {
        if (!controlActive || event.target === pinInput) {
          return;
        }
        event.preventDefault();
        pushInputEvent({
          type: 'key',
          code: event.code,
          pressed: false,
        });
      });

      window.setInterval(flushInputEvents, 8);

      loadHealth().catch((error) => {
        healthEl.textContent = String(error);
      });
    </script>
  </body>
</html>
"""
