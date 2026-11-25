"""Native, architecture-specific macOS application bundle."""
from pathlib import Path
import os

root = Path(SPECPATH)
icon = root / "assets" / "nexus.icns"
update_config = Path(os.environ.get("NEXUS_UPDATE_CONFIG_FILE", root / "assets" / "update_config.json"))
target_arch = os.environ.get("NEXUS_TARGET_ARCH")

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(icon), "assets"), (str(update_config), "assets")],
    hiddenimports=[],
    excludes=[
        "pytest", "pytestqt", "IPython", "jupyter", "tkinter", "notebook",
        "torch", "scipy", "OpenGL", "pyqtgraph.opengl", "PySide6.QtTest",
        "pynvml", "win32api", "winreg", "win32com", "pythoncom",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="NEXUS", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    target_arch=target_arch or None, codesign_identity=None, entitlements_file=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="NEXUS")
app = BUNDLE(
    coll,
    name="NEXUS.app",
    icon=str(icon),
    bundle_identifier="com.nexus.desktop",
    info_plist={
        "CFBundleName": "NEXUS",
        "CFBundleDisplayName": "NEXUS",
        "CFBundleShortVersionString": os.environ.get("NEXUS_VERSION", "1.0.0"),
        "LSMinimumSystemVersion": "14.4",
        "NSHighResolutionCapable": True,
        "NSApplicationCategoryType": "public.app-category.utilities",
    },
)
