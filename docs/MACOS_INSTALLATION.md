# macOS installation

NEXUS macOS support is under native verification. The GitHub Actions workflow can produce architecture-specific unsigned development DMGs; a completed workflow run and physical-device install have not yet been observed from this checkout. The initial OS floor is macOS 14.4, based on Qt 6.12's documented minimum.

When an artifact is available, choose the DMG matching the Mac (`arm64` for Apple Silicon, `x64` for Intel), verify its SHA-256 against the workflow artifact's matching checksum file, open the DMG, drag `NEXUS.app` to Applications, eject the image, and launch NEXUS from Applications. User data stays outside the app bundle in `~/Library/Application Support/NEXUS`; logs and caches use `~/Library/Logs/NEXUS` and `~/Library/Caches/NEXUS`.

**Distribution limitation:** current workflow builds are unsigned and not notarized. GitHub Actions can build them, but this does not complete the trusted macOS distribution path. Do not disable Gatekeeper or bypass security settings. A Developer ID signed and notarized release is required before recommending these artifacts for general installation. See [macOS build instructions](MACOS_BUILD_INSTRUCTIONS.md) and [code signing](CODE_SIGNING.md).
