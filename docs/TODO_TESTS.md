# 待集中验收

1. 文件上传 Web UI：Chrome 选择小文件上传，确认 `file_complete`、健康检查计数和落盘内容。
2. 文件传输边界：超大文件、错误 offset、非法文件名、真实浏览器断连后的 `.part` 清理、Web UI 下载已完成文件和 HTTP 票据。
3. 剪贴板 Web UI：认证后读写真实 Win32 文本剪贴板。
4. AQE Web UI：自动/手动切换档位，确认 `quality_state`、健康检查和界面展示一致。
5. AQE 实链路：Chrome 预览时确认 WebRTC stats 每秒上报 RTT/丢包/码率，手动锁定不被 stats 上报解除。
6. AQE 热切：Chrome 确认手动/自动档位变化会影响实际 WebRTC 接收分辨率/FPS。
7. AQE 统计：Chrome 接收 stats 与 `/api/health.webrtc.sessions[].video` 的分辨率/FPS/运动比例对齐。
8. AQE 编码码率：Chrome 验证 answer SDP `b=AS` 初始码率与质量变化后的重协商码率。
9. 系统性能：真实预览/硬编/长稳场景记录 `/api/health.system` 样本数/峰值与视频 `capture_ms/resize_ms`。
10. 控制通道：Chrome 确认 WS `ping/pong` RTT 持续刷新，并可作为 AQE RTT 备用信号。
11. 键盘控制：Chrome 验证字母数字、修饰键、功能键、方向键、小键盘和 PrintScreen/NumLock/ScrollLock。
12. 服务发现：真实 LAN 下用 `python -m screen_windows discover --method both --json` 验证 UDP/mDNS 可发现，mDNS 目标 <5 秒。
13. 认证持久化：配置 `auth.token_store_path` 后，真实浏览器确认主机重启后 token 可复用且无需重新 PIN。
14. 认证模式：Chrome 验证 `auth.mode = "none"` 无需 PIN，`auth.mode = "always"` 禁止 token 复用。
15. Stats 协议：Chrome 确认 WS `{type:"stats"}`、`/api/health` 和媒体状态面板的系统/视频/AQE 数据一致。
16. 多显示器：真实 Windows 多显示器环境确认 `auth_ok.display_info.monitors` 与 `/api/health.stream.display` 一致。
17. 显示器切换：Chrome 调用 `display_switch` 后重新启动预览，确认画面源和输入坐标基准切到目标显示器。
18. 移动端触控：手机/平板验证单指移动/点击、双指右键、双指滚轮映射到受控端。
19. 断线重连：Chrome 预览中重启/断开主机，确认 token 自动重连并重建视频预览。
