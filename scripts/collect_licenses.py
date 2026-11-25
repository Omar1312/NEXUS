"""Stage license files for direct runtime dependencies in the app folder."""

from __future__ import annotations

import re
import shutil
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

OUTPUT = Path("dist/NEXUS/ThirdPartyNotices")
PACKAGES = (
    "PySide6",
    "PySide6_Essentials",
    "PySide6_Addons",
    "shiboken6",
    "psutil",
    "pyqtgraph",
    "numpy",
    "pywin32",
    "nvidia-ml-py",
    "packaging",
    "PyInstaller",
)

OUTPUT.mkdir(parents=True, exist_ok=True)
inventory = [
    "NEXUS third-party license files staged from the resolved Windows build environment.",
    "Review the complete dependency and redistribution notes in docs/THIRD_PARTY_NOTICES.md.",
    "This inventory is not a legal opinion; specifically review Qt/PySide6 LGPL/GPL/commercial terms before public distribution.",
]
for package in PACKAGES:
    try:
        dist = distribution(package)
    except PackageNotFoundError:
        inventory.append(f"{package}: NOT INSTALLED; required build dependency must be present.")
        continue
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{dist.metadata['Name']}-{dist.version}")
    target = OUTPUT / safe
    copied = 0
    for entry in dist.files or ():
        name = Path(str(entry)).name.lower()
        if not any(token in name for token in ("license", "copying", "notice", "copyright")):
            continue
        source = Path(dist.locate_file(entry))
        if source.is_file():
            relative = Path(str(entry))
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1
    license_value = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "unspecified"
    inventory.append(f"{dist.metadata['Name']} {dist.version} ({license_value}): {copied} license/notice file(s) copied.")
    if copied == 0:
        target.mkdir(parents=True, exist_ok=True)
        (target / "REVIEW_REQUIRED.txt").write_text(
            f"No license file was found in installed distribution metadata. Declared license: {license_value}.\n"
            "Obtain and review the exact license and notice files before redistribution.\n",
            encoding="utf-8",
        )

(OUTPUT / "BUNDLE_INVENTORY.txt").write_text("\n".join(inventory) + "\n", encoding="utf-8")
print(f"Staged third-party license files in {OUTPUT}")
