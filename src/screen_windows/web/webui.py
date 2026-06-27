from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

WEBUI_ASSET_PACKAGE = "screen_windows.web.assets"
WEBUI_HTML_NAME = "webui.html"
LAUNCHER_HTML_NAME = "launcher.html"


@lru_cache(maxsize=1)
def load_index_html() -> str:
    """读取内置 Web UI 页面，保持服务端入口不关心前端资产布局。"""
    return files(WEBUI_ASSET_PACKAGE).joinpath(WEBUI_HTML_NAME).read_text(
        encoding="utf-8"
    )


INDEX_HTML = load_index_html()


@lru_cache(maxsize=1)
def load_launcher_html() -> str:
    """读取本地启动页，和远程控制页保持同一套资产加载方式。"""
    return files(WEBUI_ASSET_PACKAGE).joinpath(LAUNCHER_HTML_NAME).read_text(
        encoding="utf-8"
    )


LAUNCHER_HTML = load_launcher_html()
