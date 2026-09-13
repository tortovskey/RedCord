# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project_root = Path.cwd()
assets_dir = project_root / "redcord" / "assets"
data_dir = project_root / "redcord" / "data"

a = Analysis(
    ["redcord/app/main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(assets_dir), "redcord/assets"),
        (str(data_dir), "redcord/data"),
        (str(project_root / ".env.example"), "."),
        (str(project_root / "README.md"), "."),
    ],
    hiddenimports=["psycopg", "sqlalchemy.dialects.postgresql", "PyQt6.sip"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RedCord",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(assets_dir / "redcord_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="redcord",
)
