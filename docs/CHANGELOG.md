# Changelog

## 2026-11-24 - macOS implementation pass (native verification pending)
- Added lazy macOS collector selection for CPU/per-core usage, unified/system memory, swap, disk/network counters, OS details and uptime; unavailable sensor capabilities remain explicit.
- Added read-only current-user LaunchAgents inspection and macOS process protections; adapted shared pages, Settings, shortcuts, recommendations and update download flow for macOS while retaining Windows backend selection.
- Added PyInstaller `.app` spec, native app/DMG scripts, optional Developer ID signing/notarization script, macOS ARM64/Intel build workflow, and an approval-gated cross-platform release workflow.
- Constrained PySide6 to 6.12.x and set macOS 14.4 as the proposed initial floor based on Qt 6.12 documentation.
- Added collector, startup and updater tests; updated installation/build/testing/status guidance.
- Verification on Windows: 97 passed, 2 skipped; compileall, dependency consistency, workflow YAML and shell syntax checks passed. Source and isolated packaged Windows app smoke tests exited cleanly. Native macOS build/CI/device verification has not run; unsigned CI artifacts are development-only. No release or publication occurred.


## 2026-11-24 — Phase 0 research and planning baseline
- Added persistent agent instructions and project specification.
- Added initial open-source research, competitive analysis, architecture, technical decisions, MVP, roadmap, third-party inventory, development status, and next steps.
- Initialized the local Git repository at the user's request; no initial commit because local Git identity is not configured.
- Completed six pinned upstream technical reviews and marked the Phase 0 research gate complete.
- Fixed chart axis/timer enum API compatibility; corrected disk activity rate conversion and reset semantics.
- Updated formatting expectations and added chart/metric regression tests.
- Verification: `python -m pytest` — 43 passed; `python -m pip check` — no broken requirements; offscreen startup stayed running 5s without new logged errors.
- Verified monitoring worker start/stop/restart and initialization recovery, added a bounded shutdown path for slow collection, and expanded lifecycle tests. Current suite: 46 passed.
- Added SQLite schema/query/retention/failure tests, fixed time-bucket aggregation and included WAL bytes in history size. Current suite: 52 passed.
- Added process sampling and termination safety tests; termination now revalidates process creation time to detect same-name PID reuse. Current suite: 58 passed.

- Added temporary-tree tests for storage scan totals, categories, entry limits, cancellation, denied access, and symlink handling; symlink cases skip on this host because creation is unavailable.
- Added optional NVML/WMI backend absence and NVML initialization-failure tests; confirmed base metrics continue.
- Verification: `python -m pytest -q` � 66 passed, 2 skipped; compileall, pip check, and diff whitespace check pass. One earlier full suite run hit a native Qt access violation in slow worker shutdown; clean isolated and full reruns followed.


## 1.0.0-rc.1 - Windows packaging milestone (2026-11-24)

- Centralized version metadata and added reproducible PyInstaller one-folder packaging with NEXUS branding.
- Built and smoke-launched the Windows executable; user data remains in LocalAppData, separate from program files.
- Added Inno Setup installer source/build script, release scripts, CI artifact workflow, and explicitly gated publishing workflow. Installer compilation is pending Inno Setup 6 availability.
- Added optional GitHub Releases update discovery/download UI with semantic version checks, checksum verification, cancellation, and safe shutdown handoff. No release repository is configured.
- Added versioned SQLite migration/backup handling and update/settings preservation tests.
- Refactored monitoring/process QThread ownership after an intermittent native shutdown failure; latest suite and packaged smoke shutdown passed.
- Verification: 82 passed, 2 skipped; compileall, pip check, PyInstaller build and packaged smoke passed. Installer, clean VM, interactive GUI, upgrade and signing checks remain outstanding.


## 1.0.0-rc.1 - macOS groundwork (2026-11-24)

- Added focused macOS open-source research with six deep reviews, pinned upstream snapshots and architecture/compatibility planning. No third-party code was copied or added as a dependency.
- Added platform/architecture normalization helpers and macOS Application Support, Logs and Caches path conventions with test overrides.
- Made NVML dependency conditional on Windows.
- Added mocked platform selection and data-path regression tests.
- Verification: 91 passed, 2 skipped; compileall, pip check and diff check passed. Native macOS collectors, bundle/DMG and runtime verification remain pending.
