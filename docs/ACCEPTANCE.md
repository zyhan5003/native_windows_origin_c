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
- 2026-06-27 Chrome MCP：AQE 自动档低 RTT/零丢包保持标准档；手动锁定节能档后 `locked=true/profile=eco`，重协商 SDP `b=AS:2000`，控制台无错误。

## 自动化覆盖

- 2026-06-27：文件传输覆盖零字节、错误 offset、超限、非法/保留名、重名、`.part` 过滤和断连清理。
- 2026-06-27：默认配置启用 token hash 持久化，Host 重启后 WebSocket token 认证可复用。
- 2026-06-27：Host Ctrl+C 停止不再输出 traceback，真实终端只显示 `screen_windows host stopped`。
- 2026-06-27：Web UI 失效 token 会清除本地令牌并暂停自动重连，提示重新输入 PIN。
- 2026-06-27：`/api/health.runtime` 与 WS `{type:"stats"}.runtime` 使用同形快照，便于长稳对账。
- 2026-06-27：显示器切换会同步更新输入坐标基准；SendInput 鼠标绝对坐标按虚拟桌面边界映射。
- 2026-06-27：WebRTC Track 静态画面会降到低有效 FPS，stats 暴露 `target_fps/effective_fps/motion_ratio`。
- 2026-06-27 Chrome MCP：Web UI 性能面板可见；页面、health、favicon 请求正常，控制台无 error/warn/issue。
