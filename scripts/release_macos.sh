#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ "$(uname -s)" == "Darwin" ]] || { echo "Release signing requires macOS." >&2; exit 2; }
: "${NEXUS_MACOS_CERT_P12_BASE64:?Missing Developer ID certificate secret}"
: "${NEXUS_MACOS_CERT_PASSWORD:?Missing certificate password secret}"
: "${NEXUS_MACOS_SIGNING_IDENTITY:?Missing Developer ID signing identity}"
: "${NEXUS_APPLE_API_KEY_BASE64:?Missing App Store Connect API key secret}"
: "${NEXUS_APPLE_API_KEY_ID:?Missing App Store Connect key ID}"
: "${NEXUS_APPLE_API_ISSUER_ID:?Missing App Store Connect issuer ID}"
if [[ -n "${NEXUS_RELEASE_REPOSITORY:-}" ]]; then
  [[ "$NEXUS_RELEASE_REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || {
    echo "NEXUS_RELEASE_REPOSITORY must be owner/repository." >&2; exit 2;
  }
  mkdir -p "$ROOT/work"
  python3 - "$ROOT/work/update_config.json" "$NEXUS_RELEASE_REPOSITORY" <<'PY'
import json, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"repository": sys.argv[2]}), encoding="utf-8")
PY
  export NEXUS_UPDATE_CONFIG_FILE="$ROOT/work/update_config.json"
fi

TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/nexus-release.XXXXXX")"
KEYCHAIN="$TEMP_DIR/nexus-signing.keychain-db"
KEYCHAIN_PASSWORD="$(openssl rand -hex 24)"
trap 'security delete-keychain "$KEYCHAIN" >/dev/null 2>&1 || true; rm -rf "$TEMP_DIR"' EXIT
export TEMP_DIR
python3 - <<'PY'
import base64, os
from pathlib import Path
temp = Path(os.environ["TEMP_DIR"])
for env_name, filename in (
    ("NEXUS_MACOS_CERT_P12_BASE64", "developer-id.p12"),
    ("NEXUS_APPLE_API_KEY_BASE64", "AuthKey.p8"),
):
    data = base64.b64decode(os.environ[env_name], validate=True)
    if not data:
        raise SystemExit(f"{env_name} decoded to an empty file")
    (temp / filename).write_bytes(data)
PY

security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security set-keychain-settings -lut 21600 "$KEYCHAIN"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security list-keychains -d user -s "$KEYCHAIN"
security import "$TEMP_DIR/developer-id.p12" -k "$KEYCHAIN" \
  -P "$NEXUS_MACOS_CERT_PASSWORD" -T /usr/bin/codesign >/dev/null
security set-key-partition-list -S apple-tool:,apple:,codesign: -s \
  -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN" >/dev/null
security find-identity -v "$KEYCHAIN" | grep -F "$NEXUS_MACOS_SIGNING_IDENTITY"

bash scripts/build_macos.sh
APP="$ROOT/dist/NEXUS.app"
codesign --force --deep --options runtime --timestamp \
  --keychain "$KEYCHAIN" --sign "$NEXUS_MACOS_SIGNING_IDENTITY" "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"
ditto -c -k --keepParent "$APP" "$TEMP_DIR/app.zip"
xcrun notarytool submit "$TEMP_DIR/app.zip" \
  --key "$TEMP_DIR/AuthKey.p8" \
  --key-id "$NEXUS_APPLE_API_KEY_ID" \
  --issuer "$NEXUS_APPLE_API_ISSUER_ID" \
  --wait
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
bash scripts/build_dmg.sh
VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist")"
case "$(uname -m)" in arm64) ARCH=arm64 ;; x86_64) ARCH=x64 ;; esac
DMG="$ROOT/release/NEXUS-${VERSION}-macos-${ARCH}.dmg"
xcrun notarytool submit "$DMG" \
  --key "$TEMP_DIR/AuthKey.p8" \
  --key-id "$NEXUS_APPLE_API_KEY_ID" \
  --issuer "$NEXUS_APPLE_API_ISSUER_ID" \
  --wait
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"
spctl --assess --type execute --verbose=2 "$APP"
spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG"
shasum -a 256 "$DMG" | awk '{print $1 "  " $2}' > "$ROOT/release/SHA256SUMS-${ARCH}.txt"
cp "$ROOT/release/SHA256SUMS-${ARCH}.txt" "$ROOT/release/SHA256SUMS.txt"
echo "Signed and notarized $DMG"
