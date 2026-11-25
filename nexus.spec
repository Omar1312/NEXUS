# Reproducible one-folder Windows build. Qt runtime/plugin collection is handled
# by PyInstaller's PySide6 hooks; optional platform bridges are explicit.
from pathlib import Path
import os

root = Path(SPECPATH)
icon = root / "assets" / "nexus.ico"
update_config = Path(os.environ.get("NEXUS_UPDATE_CONFIG_FILE", root / "assets" / "update_config.json"))
version_file = os.environ.get("NEXUS_VERSION_INFO")
hiddenimports = ["pynvml", "pythoncom", "win32com.client"]

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(icon), "assets"), (str(update_config), "assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest", "pytestqt", "IPython", "jupyter", "tkinter", "notebook",
        "torch", "scipy", "OpenGL", "pyqtgraph.opengl", "PySide6.QtTest",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NEXUS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_em天ulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon),
    version=version_file,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NEXUS",
)
