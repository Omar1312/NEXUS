# Windows build instructions

These instructions apply to Windows only. macOS build preparation and native verification status are documented in `MACOS_BUILD_INSTRUCTIONS.md` and `MACOS_TESTING.md`. The Windows packaging scripts do not create macOS artifacts.

## Requirements

- Windows 10/11 x64
- 64-bit Python 3.11+
- Runtime/build dependencies from `requirements.txt`
- Inno Setup 6 or 7 for the installer build

## Build the executable

From the project root in PowerShell:

```powershell
python -m pip install -r requirements.txt
scripts\build_windows.ps1
```

To configure a public update source for a specific build, pass the publisher-selected GitHub repository. Leave this unset until the repository exists:

```powershell
scripts\build_windows.ps1 -ReleaseRepository owner/repository
```

The script checks Python architecture/version and dependencies, runs `pip check`, pytest and compilation checks, obtains the version from `nexus.__version__`, generates Windows file metadata, and builds `dist\NEXUS\NEXUS.exe` from `nexus.spec`. PyInstaller's PySide6 hooks collect Qt runtime files and platform plugins; the spec collects pyqtgraph modules and the optional NVML/WMI imports. Inspect PyInstaller warnings after dependency changes.

`-SkipTests` may be used only when a preceding test run is recorded:

```powershell
scripts\build_windows.ps1 -SkipTests
```

The distribution is one-folder; copy the entire `dist\NEXUS` directory. Do not copy the executable alone. It is not code signed.

## Build the installer

Install Inno Setup 6 or 7 from the [official download page](https://jrsoftware.org/inno-setup/downloads), then run:

```powershell
scripts\build_installer.ps1
```

The installer consumes `dist\NEXUS` by default, obtains its version from `nexus.__version__`, generates a temporary include, validates the embedded icon/config/Qt platform plugin, and writes `release\NEXUS-Setup-<version>-x64.exe`. To package an alternate PyInstaller directory, pass `-BuildDirectory <path>`; this is useful when an older app folder is still open. Its permanent Inno AppId is in `installer\NEXUS.iss`; do not change it. Installer compilation and installation tests remain pending until Inno Setup is available.

## Release build

```powershell
scripts\build_release.ps1
```

This runs checks/builds, validates artifacts, computes SHA-256 checksums and writes a local release summary. It never publishes. See [Release process](RELEASE_PROCESS.md).
