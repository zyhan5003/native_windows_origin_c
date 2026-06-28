# screen_windows

Windows 优先的局域网远程桌面工具。受控端在 Windows 上运行，控制端用浏览器打开页面即可预览画面、操作键鼠、传输文件和同步剪贴板。

项目目标是局域网内低延迟、可诊断、易部署的远控体验，不面向公网穿透场景。

## English introduction

`screen_windows` is a Windows-first LAN remote desktop tool. The host runs on Windows, while the controller only needs a modern browser on a phone, tablet, or another computer. It focuses on local-network low latency, WebRTC H264 video, browser-based keyboard/mouse control, mobile touchpad interaction, clipboard sync, file transfer, and practical runtime diagnostics.

This project is designed for trusted LAN usage, not public internet exposure or cloud relay scenarios.

## 联系与支持

如有切实帮助，欢迎联系 `664911336@qq.com`；也欢迎联系 `18210409689`，用于支持 agents cost。

## 当前能力

- 本地启动页：用浏览器选择绑定地址、端口、分辨率、FPS、码率、PIN、捕获源和编码后端后启动 Host。
- Web 控制台：HTTP 单页应用，无前端构建链，手机和桌面浏览器都可用。
- 视频预览：WebRTC H264，支持分辨率、FPS、码率和 AQE 自动/手动质量控制。
- 硬编运行时：自动探测可用 H264 编码器，实时 WebRTC 优先使用探测通过的硬编后端。
- 远程控制：WebSocket 鉴权、信令、键鼠输入、移动端触摸板模式、手机文本输入、stats。
- 辅助能力：剪贴板读写、文件上传/下载、UDP/mDNS 局域网发现。
- 诊断证据：`/api/health` 与 WS `stats` 暴露系统、视频、编码、AQE、输入和文件状态。

## 快速开始

```powershell
python -m pip install -e .[dev]
python -m screen_windows launcher
```

## Windows 打包

先装打包工具：

```powershell
python -m pip install pyinstaller
```

生成可分发目录：

```powershell
pyinstaller --noconfirm screen_windows.spec
```

打包后可直接运行 `dist\screen_windows\screen_windows.exe`。如果要给别人发，优先发整个 `dist\screen_windows\` 目录，不建议只拷单个 exe。

启动后会自动打开本地启动页：

```text
http://127.0.0.1:8770
```

在启动页中选择参数并点击“启动受控端”。如果要让手机或另一台电脑连接，绑定地址选择 `0.0.0.0`，然后打开页面显示的局域网访问地址。

也可以跳过启动页，直接用命令行启动 Host：

```powershell
python -m screen_windows host --host 0.0.0.0 --port 8765 --http-port 8766
```

控制端浏览器打开：

```text
http://<host-ip>:8766
```

## 常用命令

```powershell
python -m screen_windows launcher
python -m screen_windows host --host 0.0.0.0 --port 8765 --http-port 8766
python -m screen_windows info --json
python -m screen_windows discover --method both --json
python -m screen_windows bench-encode --width 1920 --height 1080 --fps 30 --frames 60 --json
pytest -q
```

## 硬编码能力

项目会主动探测 FFmpeg、硬编编码器、rawvideo 管线和最小启动编码，避免只看编码器列表导致“看似支持、实际不可用”。

`encoder.backend = "auto"` 时的探测顺序：

| 后端 | FFmpeg 编码器 | 典型硬件 | 说明 |
| --- | --- | --- | --- |
| `nvenc` | `h264_nvenc` | NVIDIA GPU | 优先尝试，驱动/CUDA DLL 不可用会自动跳过。 |
| `amf` | `h264_amf` | AMD GPU | AMF 运行时不可用会自动跳过。 |
| `qsv` | `h264_qsv` | Intel iGPU | 常见核显硬编路径，是否可用以运行时探测为准。 |
| `libx264` | `libx264` | CPU | 兜底软编，保证可用性。 |

实时 WebRTC 会优先协商 H264，并使用探测通过的硬编后端；如果首帧硬编失败，会自动回退到 `libx264`，不直接断流。

查看探测和运行时是否真的使用硬编：

```powershell
python -m screen_windows info --json
Invoke-WebRequest -Uri "http://127.0.0.1:8766/api/health" -UseBasicParsing
```

重点字段：

```text
encoder.selected_backend
encoder.ffmpeg_encoder
encoder.pipeline_ready
encoder.runtime.active_encoder
encoder.runtime.hardware_active
encoder.runtime.fallback_reason
```

推荐安装完整 FFmpeg：

```powershell
winget install --id Gyan.FFmpeg.Essentials
```

FFmpeg 解析优先级：

```text
encoder.ffmpeg_path > SCREEN_WINDOWS_FFMPEG > PATH/WinGet 自动发现
```

## 配置

默认读取当前目录的 `host_config.toml`。不写配置也能启动，路径类默认值会放在用户 AppData，便于跨机部署。

常用配置片段：

```toml
[server]
bind = "0.0.0.0"
port = 8765
http_port = 8766

[auth]
mode = "pin_once" # pin_once | always | none
# pin 留空时启动后自动生成。
# token_store_path 默认位于用户 AppData，不建议写死机器绝对路径。

[stream]
source = "auto" # auto | dxcam | mss | synthetic
width = 1280
height = 720
fps = 24
monitor = 0

[encoder]
backend = "auto" # auto | nvenc | amf | qsv | libx264
bitrate = "10M"
# ffmpeg_path 留空时自动查找。

[discovery]
method = "udp" # udp | mdns | both | none

[file_transfer]
# receive_dir 默认位于用户 AppData，跨机部署时可按需覆盖。
max_file_size = 536870912
```

## 验证

快速环境门禁：

```powershell
python -m screen_windows info --json
python -m screen_windows bench-encode --width 1920 --height 1080 --fps 30 --frames 60 --json
```

关键自动化：

```powershell
pytest -q
```

真实交付验收建议结合浏览器、手机、局域网、多显示器和长稳性能做小范围验证。

## 项目结构

```text
src/screen_windows/
  app/        CLI、配置、Host 编排、HTTP/WS 服务
  control/    显示器枚举、键鼠输入、剪贴板
  media/      捕获源、编码探测、WebRTC、AQE
  network/    发现、协议消息、文件传输
  security/   PIN、Token、认证持久化
  telemetry/  系统与运行时统计
  web/        Web UI 资源加载与静态页面
```

代码按运行入口、控制能力、媒体链路、网络协议、安全认证、遥测和 Web 资源分层，便于后续按模块维护。

## 安全说明

- 默认认证模式是 `pin_once`，首次输入 PIN 后使用 token 复用。
- `auth.mode = "none"` 只适合完全可信的局域网。
- 本项目当前不提供公网穿透、账号系统或端到端云服务。
- 文件下载只暴露接收目录内已完成文件，认证模式下需要短期访问票据。
- 源码按 MIT 开源；FFmpeg / H.264 / 硬编相关运行时由使用者自行确保本机安装与分发合规，仓库不捆绑专有二进制。
