# GitHub release readiness

Audit date: 2026-11-24. Version: `1.0.0-rc.1`.

## Completed locally

- Windows PyInstaller one-folder build exists and an isolated rebuild smoke-launched successfully.
- Inno Setup 7.1.1 compiled `release/NEXUS-Setup-1.0.0-rc.1-x64.exe` (50,290,001 bytes). The installer uses the permanent AppId, per-user installation, MIT license, mandatory Start Menu shortcut, optional desktop shortcut, and user-data preservation by default.
- Installer build discovery supports Inno Setup 6 and 7, PATH, standard directories, and uninstall registry entries.
- Windows source tests pass: 97 passed, 2 skipped. Compileall, pip check, workflow YAML parsing, and shell syntax checks passed.
- macOS source implementation, architecture-specific `.app`/DMG scripts, and ARM64/Intel workflow definitions are present.
- Update discovery selects platform and architecture assets, verifies SHA-256, and requires user-mediated installation.
- `.gitignore` excludes build outputs, databases, logs, reports, screenshots, virtual environments, secrets, and credentials.
- Security, contributing, conduct, support, Windows installation, source-build, and screenshot guidance are present.

## Incomplete or unverified

- The repository has no remote and no commits. All files are currently untracked.
- GitHub CLI is not installed and no GitHub authentication state is available locally. Repository creation and publication were not attempted.
- Start Menu search, installed-app registration, installer launch, upgrade, and uninstall were not exercised in a disposable Windows environment.
- macOS runners have not been run from this checkout. Native ARM64/Intel app, DMG, GUI, install, and update behavior are unverified.
- macOS artifacts are unsigned/not notarized in the ordinary build workflow. Developer ID signing/notarization requires owner-provided secrets and approval.
- No genuine application screenshots are committed.
- The update source remains intentionally unconfigured until the owner selects the actual repository and publishes releases.

## Known limitations

macOS GPU utilization/memory, thermal, fan, power, CPU frequency/temperature, and memory-pressure metrics are unavailable in the least-privilege baseline. The macOS startup page reads user LaunchAgent plist files but does not claim that launchd has loaded each job. Windows installer signing and clean-machine verification remain pending.

## Publication boundary

No public repository, push, release, upload, account setting, or personal information publication has occurred. The exact source tree can be reviewed locally before any owner-approved GitHub action.
