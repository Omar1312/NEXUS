# Third-party notices and release review

The macOS research reviewed third-party projects only for engineering ideas; no source was copied and no new macOS-specific runtime dependency has been added. Review each candidate's exact license before future adoption. In particular, Glances is LGPL-3.0, osx-cpu-temp is GPL-2.0, and the gptop repository did not assert an SPDX license in the research snapshot. See `MACOS_RESEARCH.md`.

The Windows build script stages license and notice files found in the resolved package metadata under `dist/NEXUS/ThirdPartyNotices`. Review the generated `BUNDLE_INVENTORY.txt` for each release. The inventory below records the observed build environment on 2026-11-24; the exact versions are rebuilt from `requirements.txt` and may change. This file is a review checklist, not legal advice.

| Runtime/build component | Observed version | License metadata / source | Distribution note |
|---|---:|---|---|
| Python | 3.14.7 | PSF License; [Python license](https://docs.python.org/3/license.html) | Python runtime is bundled by PyInstaller. Include its license text if required by the redistributed runtime. |
| PySide6, Essentials, Addons, shiboken6, Qt | 6.12.0 | Wheel metadata: `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`; [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html) | Qt is dynamically bundled. The installed wheel included `LicenseRef-Qt-Commercial.txt`; confirm which applicable license was selected and fulfill LGPL/GPL or commercial distribution terms before public distribution. Qt plugins and bundled third-party Qt components need a resolved-build audit. |
| psutil | 7.2.2 | BSD-3-Clause; package `LICENSE` | License file copied from package metadata. |
| pyqtgraph | 0.14.0 | MIT; package `LICENSE.txt` | Its color-map data has a separate CC-BY notice that the collector includes. |
| NumPy | 2.5.3 | BSD-3-Clause plus bundled subcomponent licenses | Collect all package license/notice files; audit bundled numerical runtime libraries. |
| pywin32 | 312 | PSF-style and component-specific notices | Package ships multiple component licenses; review all files in the generated bundle. |
| nvidia-ml-py | 13.615.71 | BSD metadata/package license | Optional NVIDIA NVML bindings; verify exact wheel notices at release time. |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Used for semantic version comparison. Both license texts are staged. |
| PyInstaller and bootloader | 6.22.3 | GPLv2-or-later with the PyInstaller bootloader exception | Permits packaging proprietary/non-free applications under its exception; retain the exact license and exception. |

NEXUS contains no copied or adapted source code from research candidates. Do not ship binaries if the generated inventory shows a missing runtime license, if Qt redistribution terms are unresolved, or if a transitive runtime component is missing from the notice review. The application and installer are currently unsigned; no Authenticode signature is claimed.
