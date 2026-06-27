# screen_windows

Windows 优先的局域网高性能远程桌面项目。

## 当前能力

- Web 客户端：HTTP 单页控制台，无前端构建链。
- 视频：WebRTC 预览，AQE 可调 FPS/分辨率/SDP 目标码率。
- 控制：WebSocket 鉴权、信令、键鼠、剪贴板、文件传输、stats。
- 捕获：DXcam 优先，MSS 与 synthetic 兜底。
- 认证：`pin_once`、`always`、`none`，支持 token hash 持久化。
- 发现：UDP 与 mDNS，CLI 可聚合扫描。
- 证据：`/api/health` 与 WS `stats` 暴露系统、视频、AQE、文件、输入状态。

## 运行

```powershell
python -m pip install -e .[dev]
python -m screen_windows host --host 127.0.0.1 --port 8765 --http-port 8766
```

浏览器打开：

```text
http://127.0.0.1:8766
```

## 常用命令

```powershell
python -m screen_windows info --json
python -m screen_windows discover --method both --json
python -m screen_windows bench-encode
pytest -q
```

## 配置

默认读取 `host_config.toml`。常用片段：

```toml
[auth]
mode = "pin_once" # pin_once | always | none
token_store_path = "tokens.json"

[stream]
source = "auto" # auto | dxcam | mss | synthetic
width = 1280
height = 720
fps = 24
monitor = 0
```

## FFmpeg

- 编码链路需要完整 FFmpeg 构建，不能使用缺少 `rawvideo`/常见 muxer 的精简版。
- 解析优先级：`encoder.ffmpeg_path` > 环境变量 `SCREEN_WINDOWS_FFMPEG` > `PATH`/WinGet 安装 > 内置兜底候选。
- 快速门禁：`python -m screen_windows info` 查看 FFmpeg、硬编探针和显示器摘要；`bench-encode` 再跑最小编码基准。
- Windows 可直接用 `winget install --id Gyan.FFmpeg.Essentials` 安装。

## 验收

自动化只覆盖关键链路。真实浏览器、LAN、多显示器、长稳性能按 `docs/TODO_TESTS.md` 集中验收。
