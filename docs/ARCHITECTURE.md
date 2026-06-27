# 工程架构

## 包边界

`screen_windows` 根包只保留包入口：`__init__.py` 与 `__main__.py`。业务代码必须放入能力域包，禁止继续在根包新增平铺模块。

| 包 | 职责 |
| --- | --- |
| `app` | CLI、配置、Host 编排、HTTP/WS 服务入口 |
| `control` | 显示器枚举、键鼠输入、剪贴板 |
| `media` | 捕获源、编码探测、AQE、WebRTC 媒体会话 |
| `network` | 发现、协议消息、文件传输 |
| `security` | PIN、Token、认证持久化 |
| `telemetry` | 系统与运行时统计 |
| `web` | Web UI 资源加载与静态页面资产 |

## 新代码规则

1. 新功能先判断所属能力域，再放入对应包；不能判断时先收口命名，禁止临时堆到根包。
2. `app.server.HostServer` 只做跨能力编排；领域细节应下沉到对应能力域包。
3. 不创建旧路径兼容转发模块，例如 `screen_windows.auth -> screen_windows.security.auth`，避免形成双结构。
4. Web UI 大段 HTML/CSS/JS 放在 `web/assets`，Python 只负责加载和服务。
5. 测试导入使用真实能力域路径，测试面跟随最终结构，不保留历史导入。

## 当前结构

```text
src/screen_windows/
  __init__.py
  __main__.py
  app/
  control/
  media/
  network/
  security/
  telemetry/
  web/
```

## 验收

结构收敛必须同时满足：

1. 根包无业务平铺模块。
2. 旧根路径导入搜索为零。
3. `python -m screen_windows ...` 入口仍可用。
4. 自动化主路径通过后再继续功能开发。
