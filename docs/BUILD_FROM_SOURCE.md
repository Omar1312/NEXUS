# Build from source

NEXUS requires Python 3.11 or newer.

## Windows

```powershell
python -m pip install -r requirements.txt
python -m nexus
python -m pytest -o addopts='' -q
python -m compileall -q nexus tests scripts
python -m pip check
scripts\build_windows.ps1
scripts\build_installer.ps1
```

The frozen application is written to `dist\NEXUS`. The installer is written to `release\NEXUS-Setup-<version>-x64.exe` and requires Inno Setup 6 or 7. The installer build script discovers `ISCC.exe` from PATH, standard install directories, and the Windows uninstall registry.

## macOS

Use a native macOS 14.4+ host or the prepared GitHub Actions runners. Install dependencies with `python3 -m pip install -e '.[dev,build]'`, then run `bash scripts/build_macos.sh` and `bash scripts/build_dmg.sh`. The scripts build the native architecture of the host. ARM64 and Intel artifacts are produced separately by `.github/workflows/macos-build.yml`.

macOS app bundles and DMGs have not been built on this Windows host. GPU utilization, thermal, fan, power, and memory-pressure readings remain unavailable in the least-privilege macOS baseline.
