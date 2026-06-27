# 集中验收

## 运行

```powershell
python -m screen_windows host --host 127.0.0.1 --port 8765 --http-port 8766
```

打开 `http://127.0.0.1:8766`，先完成认证，再启动视频预览。

## 证据入口

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8766/api/health" -UseBasicParsing
python -m screen_windows info --json
python -m screen_windows discover --method both --json
python -m screen_windows bench-encode
```

浏览器侧记录控制台、网络请求、WebRTC stats、媒体状态面板。

## 必过项

1. 预览：Chrome 能看到实时画面，stats 中 FPS/分辨率/码率目标与 AQE 一致。
2. 控制：鼠标、键盘、小键盘、触控、断线重连可用。
3. 文件：上传、下载、断连清理 `.part`、HTTP 票据有效。
4. 剪贴板：真实 Win32 文本读写成功。
5. 发现：真实 LAN 下 UDP/mDNS 可发现。
6. 性能：长稳记录 `/api/health.system` 样本数/峰值和视频 `capture_ms/resize_ms`。

细项待测记录见 `docs/TODO_TESTS.md`。

## 最近烟测

- 2026-06-27 Chrome MCP：本机 `dxcam` 预览已连通，WebRTC `connected`，视频 `1280x720` live track，控制台无错误。
- 2026-06-27 Chrome MCP：小文件上传/列表/带票据下载通过，health `completed_files=1`，落盘内容一致，控制台无错误。
- 2026-06-27 Chrome MCP：文本剪贴板双向读写通过，Win32 内容一致，health `reads=1/writes=1`，控制台无错误。
