# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


hiddenimports = collect_submodules("screen_windows")

datas = [
    ("src/screen_windows/web/assets/*.html", "screen_windows/web/assets"),
]

a = Analysis(
    ["src/screen_windows/desktop.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "black",
        "debugpy",
        "docutils",
        "IPython",
        "ipykernel",
        "ipywidgets",
        "jedi",
        "jupyter",
        "jupyter_client",
        "jupyter_core",
        "lxml",
        "matplotlib",
        "nbformat",
        "PIL",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "pytest",
        "sphinx",
        "tkinter",
        "tornado",
        "traitlets",
        "zmq",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="screen_windows",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="screen_windows",
)
