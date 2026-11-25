#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "build_dmg.sh must run on macOS." >&2
  exit 2
fi
case "$(uname -m)" in
  arm64) ARCH=arm64 ;;
  x86_64) ARCH=x64 ;;
  *) echo "Unsupported macOS architecture: $(uname -m)" >&2; exit 2 ;;
esac
APP="$ROOT/dist/NEXUS.app"
[[ -d "$APP" ]] || { echo "Build dist/NEXUS.app first using scripts/build_macos.sh" >&2; exit 1; }
EXPECTED_MACH_ARCH="$(uname -m)"
ACTUAL_MACH_ARCH="$(lipo -archs "$APP/Contents/MacOS/NEXUS")"
[[ "$ACTUAL_MACH_ARCH" == "$EXPECTED_MACH_ARCH" ]] || {
  echo "Refusing to label $ACTUAL_MACH_ARCH app as a $(uname -m) DMG." >&2; exit 1;
}
VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist")"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/nexus-dmg.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/NEXUS"
ditto "$APP" "$STAGE/NEXUS/NEXUS.app"
ln -s /Applications "$STAGE/NEXUS/Applications"
cat > "$STAGE/NEXUS/INSTALL.txt" <<'EOF'
NEXUS macOS installation

Drag NEXUS.app to Applications, eject this disk image, then launch NEXUS from Applications.
NEXUS requires macOS 14.4 or later. This development build is not signed or notarized.
The application stores user data in ~/Library/Application Support/NEXUS.
EOF
OUT="$ROOT/release"
mkdir -p "$OUT"
DMG="$OUT/NEXUS-${VERSION}-macos-${ARCH}.dmg"
hdiutil create -volname "NEXUS ${VERSION}" -srcfolder "$STAGE/NEXUS" -ov -format UDZO "$DMG"
shasum -a 256 "$DMG" | awk '{print $1 "  " $2}' > "$OUT/SHA256SUMS-${ARCH}.txt"
echo "Built $DMG"
