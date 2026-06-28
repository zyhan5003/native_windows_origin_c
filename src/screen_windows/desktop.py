from __future__ import annotations

from screen_windows.app.launcher import run_launcher


def main() -> int:
    """Windows 桌面版打包入口，默认直接打开本地启动页。"""
    return run_launcher()


if __name__ == "__main__":
    raise SystemExit(main())
