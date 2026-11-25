"""Generate PyInstaller's Windows VERSIONINFO from nexus.__version__."""

from __future__ import annotations

import re
from pathlib import Path

from nexus import __version__

match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?", __version__)
if match is None:
    raise SystemExit(f"Unsupported Windows file version: {__version__}")
version = tuple(int(part) for part in match.groups()) + (0,)
Path("work").mkdir(exist_ok=True)
Path("work/nexus_version_info.txt").write_text(
    """# UTF-8\nVSVersionInfo(\n  ffi=FixedFileInfo(\n    filevers={version},\n    prodvers={version},\n    mask=0x3f,\n    flags=0x0,\n    OS=0x40004,\n    fileType=0x1,\n    subtype=0x0,\n    date=(0, 0)\n    ),\n  kids=[\n    StringFileInfo([\n      StringTable('040904B0', [\n        StringStruct('CompanyName', 'NEXUS Project'),\n        StringStruct('FileDescription', 'NEXUS system performance monitor'),\n        StringStruct('FileVersion', '{display}'),\n        StringStruct('InternalName', 'NEXUS'),\n        StringStruct('OriginalFilename', 'NEXUS.exe'),\n        StringStruct('ProductName', 'NEXUS'),\n        StringStruct('ProductVersion', '{display}')])\n      ]),\n    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n  ]\n)\n""".format(version=version, display=__version__),
    encoding="utf-8",
)
