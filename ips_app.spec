# -*- mode: python ; coding: utf-8 -*-
# PyInstaller onedir bundle: IPS_App.exe + _internal/ (see docs/desktop_build.md).
# Build from repo root with the app venv activated:
#   pip install -r requirements.txt -r requirements-desktop.txt
#   pyinstaller --clean IPS_App.spec

import pathlib

from PyInstaller.utils.hooks import collect_all

block_cipher = None
# SPEC / SPECPATH are provided by PyInstaller when evaluating this file.
ROOT = pathlib.Path(SPEC).resolve().parent

ICON = ROOT / "static" / "ips_app.ico"
if not ICON.is_file():
    raise FileNotFoundError(f"Missing icon for EXE: {ICON} (generate with Pillow from static/icon-512.png)")

# Application trees (Streamlit entry: app/main.py)
datas_app = [
    (str(ROOT / "app"), "app"),
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "static"), "static"),
    (str(ROOT / ".streamlit"), ".streamlit"),
]

datas_extra: list = []
binaries_extra: list = []
hidden_extra: list = []
for pkg in ("streamlit", "pywebview"):
    d, b, h = collect_all(pkg)
    datas_extra.extend(d)
    binaries_extra.extend(b)
    hidden_extra.extend(h)

hidden_extra = sorted(set(hidden_extra))

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[str(ROOT)],
    binaries=binaries_extra,
    datas=datas_extra + datas_app,
    hiddenimports=hidden_extra,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IPS_App",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="IPS_App",
)
