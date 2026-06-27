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
- 2026-06-27 Chrome MCP：`auth.mode="none"` 未输入 PIN 可建立控制会话，能力按钮启用且不依赖 token，控制台无错误。
- 2026-06-27 Chrome MCP：`auth.mode="always"` 首次 PIN 成功；刷新后无 PIN 连接失败且本地不保存 token，控制台无错误。
- 2026-06-27 Android 真机：HeyTap Browser + ADB reverse 通过；PIN 限制 6 位、连接按钮切换“断开主机”、WebRTC 预览、触摸板式滑动输入可用，`/api/health.input` 从 `0/0` 增至 `26/26`。
- 2026-06-27 Android 真机：手机文本输入入口可用，发送 `mobitest` 后 `/api/health.input` 从 `26/26` 增至 `27/27`；Unicode 注入由自动化覆盖。
- 2026-06-27 真实 Host：手动切换 `1920x1080@30fps/8Mbps` 后，`/api/health.stream` 从 `1280x720@24` 更新为 `1920x1080@30`，`quality_state.stream` 同步返回实际流尺寸。

## 自动化覆盖

- 2026-06-27：代码结构收敛为能力域包，根包只保留入口；旧根路径业务导入搜索为零。
- 2026-06-27：文件传输覆盖零字节、错误 offset、超限、非法/保留名、重名、`.part` 过滤和断连清理。
- 2026-06-27：默认配置启用 token hash 持久化，Host 重启后 WebSocket token 认证可复用。
- 2026-06-27：Host Ctrl+C 停止不再输出 traceback，真实终端只显示 `screen_windows host stopped`。
- 2026-06-27：Web UI 失效 token 会清除本地令牌并暂停自动重连，提示重新输入 PIN。
- 2026-06-27：`/api/health.runtime` 与 WS `{type:"stats"}.runtime` 使用同形快照，便于长稳对账。
- 2026-06-27：显示器切换会同步更新输入坐标基准；SendInput 鼠标绝对坐标按虚拟桌面边界映射。
- 2026-06-27：WebRTC Track 静态画面会降到低有效 FPS，stats 暴露 `target_fps/effective_fps/motion_ratio`。
- 2026-06-27 Chrome MCP：Web UI 性能面板可见；页面、health、favicon 请求正常，控制台无 error/warn/issue。
- 2026-06-27：WebRTC 会话进入 failed/closed 后会自动清理 Host 侧 sessions 与 active 计数。
- 2026-06-27：`bench-encode` 支持按配置/宽高/FPS/帧数输出 JSON，便于真实机器记录编码门禁。
- 2026-06-27：`auth_ok.file_transfer` 下发 `chunk_size/max_file_size`，Web UI 上传按服务端限制分片并预拦截超限文件。
- 2026-06-27：Web UI 远控失焦、鼠标离开或停用控制时会释放已按下的键盘/鼠标状态，降低卡键风险。
- 2026-06-27：Web UI 控制通道重连会忽略旧 socket 的迟到 close/message，避免旧会话覆盖新预览状态。
- 2026-06-27：Web UI 在 WebRTC 媒体连接 failed/disconnected 且信令仍可用时会自动重建预览。
- 2026-06-27：Web UI 支持手机触摸板模式和手机文本输入；单指滑动按增量移动远端鼠标，文本输入走 Win32 Unicode 注入。
- 2026-06-27：手动画质分辨率会重建 Host 捕获源并同步输入坐标基准，避免 UI 显示 1080p 但实际仍发送 720p 的模糊画面。
- 2026-06-27 Chrome MCP：Web UI 改为远控驾驶舱布局，健康检查收为摘要；手动自定义 `1600x900@45fps/7.5Mbps` 可生效，控制台无 error/warn/issue。
- 2026-06-27 Chrome MCP：Web UI 增加停止/重建预览、填充/完整显示和全屏入口；页面加载无 error/warn/issue。
- 2026-06-27 Chrome MCP：Web UI 改为新手三步连接导向，画质控件补充用途说明，诊断日志默认折叠；桌面/窄屏快照可读，控制台无 error/warn/issue。
- 2026-06-27 Chrome MCP：交付冒烟通过；PIN 认证、WebRTC `connected`、Chrome video `1280x720`、剪贴板文本双向、文件上传/列表/下载、手动降采样 `1024x576@15fps/1.5Mbps` 均可用，控制台无消息，网络请求 200/204。
- 2026-06-27 环境门禁：`info --json` 识别 WinGet FFmpeg 8.1.1，NVENC/AMF 探针失败后自动落到 QSV；`bench-encode 1280x720@24fps/24帧` 成功。
