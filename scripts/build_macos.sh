#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "build_macos.sh must run on macOS; native bundles cannot be cross-built here." >&2
  exit 2
fi
case "$(uname -m)" in
  arm64) ARCH=arm64 ;;
  x86_64) ARCH=x64 ;;
  *) echo "Unsupported macOS build architecture: $(uname -m)" >&2; exit 2 ;;
esac
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required")
PY
python3 -m pip check
python3 -m compileall -q nexus
python3 - <<'PY'
from PySide6.QtWidgets import QApplication
import psutil, pyqtgraph
print("PySide6, psutil and pyqtgraph imports are available")
PY
VERSION="$(python3 -c 'from nexus import __version__; print(__version__)')"
export NEXUS_VERSION="$VERSION"
export NEXUS_TARGET_ARCH="$(uname -m)"
python3 -m PyInstaller --noconfirm --clean nexus_macos.spec
APP="$ROOT/dist/NEXUS.app"
BIN="$APP/Contents/MacOS/NEXUS"
[[ -d "$APP" && -x "$BIN" ]] || { echo "PyInstaller did not create a valid NEXUS.app" >&2; exit 1; }
EXPECTED_MACH_ARCH="$(uname -m)"
ACTUAL_MACH_ARCH="$(lipo -archs "$BIN")"
[[ "$ACTUAL_MACH_ARCH" == "$EXPECTED_MACH_ARCH" ]] || {
  echo "Expected a native $EXPECTED_MACH_ARCH app binary, found: $ACTUAL_MACH_ARCH" >&2; exit 1;
}
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist" | grep -Fx 'com.nexus.desktop'
find "$APP/Contents" -name 'libqcocoa.dylib' -print -quit | grep -q . || {
  echo "Qt Cocoa platform plugin is missing from the app bundle" >&2; exit 1;
}
SMOKE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/nexus-smoke.XXXXXX")"
trap 'rm -rf "$SMOKE_DIR"' EXIT
NEXUS_DATA_DIR="$SMOKE_DIR/data" QT_QPA_PLATFORM=offscreen "$BIN" --smoke-test
echo "Built native $ARCH app bundle: $APP"
