# Update system

## Configuration and status

Update selection now checks OS and architecture. Windows expects `NEXUS-Setup-<version>-x64.exe`; macOS expects `NEXUS-<version>-macos-arm64.dmg` or `NEXUS-<version>-macos-x64.dmg`. macOS downloads are checksum-verified and opened as DMGs for manual drag-to-Applications installation; no bundle replacement is automated. Native update/install behavior remains pending macOS runner/device verification.

The update client is deliberately unconfigured until the publisher supplies `-ReleaseRepository owner/repository` to the Windows/release build scripts. The resulting `assets/update_config.json` is embedded in that particular build; no repository URL is guessed or embedded by default. A runtime `NEXUS_RELEASE_REPOSITORY` environment override is also supported for development/troubleshooting. Public GitHub API access needs no token. Updates are optional; all local monitoring, diagnostics, analysis, settings and history continue offline.

The Settings page displays the installed version, check status, release notes, and an explicit Check for Updates action. An optional once-daily check preference is disabled by default. Finding an update never installs it automatically.

## Release contract

GitHub Releases must use semantic version tags (optionally prefixed with `v`) and include:

- `NEXUS-Setup-MAJOR.MINOR.PATCH-x64.exe` (prerelease suffixes are preserved in the filename)
- `SHA256SUMS.txt` with a line containing the installer SHA-256 and exact filename

Stable checks use the GitHub latest-release endpoint. The client supports opt-in prerelease comparison at its service layer; the Settings page currently checks stable releases only. It uses semantic version comparison, validates expected asset names, rejects non-HTTPS or untrusted download hosts, caps download sizes, supports cancellation, checks metadata size and SHA-256, and deletes incomplete or invalid downloads. A checksum distributed beside an installer detects mismatch/corruption but does not authenticate the publisher. Configure Authenticode signing and verify the publisher signature before treating releases as authenticated.

After the user approves, the verified installer launches its normal interactive wizard. The app then exits through its normal shutdown path, flushing history and closing SQLite; Inno Setup detects files in use and asks before closing applications. The downloaded Windows installer is never launched until its checksum and size pass. macOS DMGs are opened only after their checksum and size pass, then the user completes installation manually.

## Failure recovery and data

Network, rate-limit, malformed release, missing asset, cancellation, size mismatch and checksum failures are reported in Settings and do not replace the installed app. If an installer fails, run the downloaded installer again manually or reinstall the previous trusted installer. User settings and databases remain outside the application directory (`%LOCALAPPDATA%\Nexus` on Windows and `~/Library/Application Support/NEXUS` on macOS).

SQLite schema migrations use monotonically increasing versions. Before a migration, NEXUS creates an SQLite-consistent `*.pre-migration-*.db` backup beside the database. Each migration is transactional. A newer-than-supported database is refused; do not install an older build against a database after an incompatible migration. Restore the pre-migration backup only while NEXUS is closed.

No release repository is configured, no public release endpoint has been tested, and downloads are not Authenticode signed. Update delivery is therefore implemented but not operational for end users yet.
