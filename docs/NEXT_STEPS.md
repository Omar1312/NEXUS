# Next steps

## Current checkpoint: macOS implementation complete locally; Windows setup source ready

The MAC-003 through MAC-016 implementation pass is complete in this checkout. Current source includes the lazy platform collector dispatch, psutil macOS baseline, read-only LaunchAgents review, platform-aware shared pages, architecture-specific DMG updater selection, native packaging scripts, and a macOS ARM64/Intel CI workflow. See `DEVELOPMENT_STATUS.md` for actual local test results and limits.

## Required next verification

1. Install the generated `release/NEXUS-Setup-1.0.0-rc.1-x64.exe` and verify shortcuts, Start Search, Installed Apps registration, upgrade, and data retention. The build was completed with Inno Setup 7.1.1.
2. Push this source to the chosen GitHub repository or open a pull request, then run **Actions > macOS tests and native installers**. It uploads separate `NEXUS-macOS-arm64` and `NEXUS-macOS-x64` artifacts for 14 days and does not create a Release. Manual dispatch is also available. See `MACOS_BUILD_INSTRUCTIONS.md`.
3. Review both runner results and test the app/DMG on macOS 14.4+ ARM64 and Intel hardware. This Windows host cannot verify native macOS behavior.
4. Obtain owner approval and Apple Developer ID credentials before any signing/notarization release. The ordinary CI outputs are unsigned development builds; do not bypass Gatekeeper.
5. Re-run `scripts/build_windows.ps1` after final changes. The normal `dist/NEXUS` target is currently locked by an already-running NEXUS process; it was left untouched.

No GitHub publication or Release creation has been performed.
