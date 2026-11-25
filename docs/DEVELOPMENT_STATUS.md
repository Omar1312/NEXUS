# Development status

Updated 2026-11-24 after the MAC-003 through MAC-016 local implementation pass. See the historical baseline below; the current macOS state is summarized first.

## Current macOS implementation checkpoint

- Platform dispatch now lazily selects a psutil macOS collector while retaining the Windows collector path. Windows-only admin, registry, COM, PDH and NVML code is not constructed by the macOS path.
- macOS snapshot collection provides CPU/per-core usage, unified/system memory and swap, disk capacity/I/O counters, per-interface network counters, OS/architecture/uptime, plus explicit unavailable capabilities. Apple Silicon unified RAM is reported once and no dedicated VRAM is fabricated.
- Process listing/details and explicit graceful termination use the shared psutil service with macOS critical-process protections. The startup page reads only current-user `~/Library/LaunchAgents/*.plist`; it does not inspect system daemons or mutate login state. The scan reports plist presence, not whether launchd has loaded a job.
- Dashboard, Hardware Monitor, Gaming Mode, Startup, Optimization, Process Manager, Settings, title and shortcuts have platform-aware labels/actions. Windows startup registration and UI paths remain selected only on Windows. Storage scanning and other shared pages retain their existing code paths.
- Updates now select the exact Windows installer or architecture-matched macOS DMG; Mac downloads are checksum-verified and handled as user-mediated DMG installs. No auto-replacement of the running app.
- Added a PyInstaller `.app` spec, native app/DMG scripts, and `.github/workflows/macos-build.yml`. CI is configured for `macos-15` ARM64 and `macos-15-intel` x64, tests/compiles/checks dependencies, builds and smoke-launches `.app`, then uploads unsigned DMG/checksum artifacts for 14 days. It does not publish a Release.
- Dependency floor is PySide6 6.12.x; Qt 6.12 documentation lists macOS 14.4+ as its supported target floor. The proposed initial minimum is therefore 14.4, subject to frozen-app verification.
- Local verification on Windows: `python -m pytest -o addopts='' -q` ? **97 passed, 2 skipped**; compileall, pip check, workflow YAML parsing, and Git Bash syntax checks for all three macOS shell scripts passed. The source app ran offscreen and shut down cleanly. A separate PyInstaller Windows build in an isolated `work` output folder smoke-launched successfully.
- `scripts/build_windows.ps1` reran its tests successfully but could not replace the existing `dist/NEXUS` output because a responsive NEXUS process was using a NumPy `.pyd` there. That running app was left untouched. The isolated alternate-output package build and smoke test passed.
- Windows setup wizard source now uses the permanent AppId and per-user install path, always creates the Start Menu shortcut, offers the desktop shortcut as optional, explicitly shows the welcome page, and blocks semantic downgrades including numeric prerelease regressions. `build_installer.ps1` validates NEXUS.exe, app icon/config, and `qwindows.dll`, supports Inno Setup 6/7 discovery and `-BuildDirectory`. Inno Setup 7.1.1 compiled `release/NEXUS-Setup-1.0.0-rc.1-x64.exe` successfully; installation, Start Search, upgrade and uninstall behavior remain unverified.
- Native macOS build, DMG mount/copy, macOS GUI behavior, signing/notarization, and both runner jobs remain **not run**. No macOS results are claimed.
- Remaining distribution blocker: these CI DMGs are unsigned and not notarized. Developer ID signing/notarization and a physical ARM64/Intel install/update review are required before general distribution. No repository remote, GitHub push, Release, or publication was performed.

## Current next steps

1. Add/push the reviewed checkout to its GitHub repository and run **Actions ? macOS tests and native installers** (or `workflow_dispatch`) to obtain the ARM64 and Intel artifacts as described in `MACOS_BUILD_INSTRUCTIONS.md`.
2. Review native logs and test both installers on macOS 14.4+ ARM64 and Intel machines; record exact hardware/OS/results.
3. Obtain owner approval and Apple Developer ID credentials before adding signing/notarization secrets or publishing releases.
4. Re-run Windows regression and packaging from the final source; Inno Setup availability remains a separate Windows installer prerequisite.

## Phase 0 research completion checklist

| Requirement | Status | Evidence |
|---|---|---|
| Relevant open-source candidate scan (10–15) | Complete | 12 candidates in `OPEN_SOURCE_RESEARCH.md` |
| Deep technical analysis of strongest candidates (5–8) | Complete | Six pinned snapshots (psutil, LHM, pyqtgraph, Glances, WinDirStat, System Informer), architecture/source/license/issues in `OPEN_SOURCE_RESEARCH.md` |
| Actual source/docs inspection | Complete | Pinned implementation/API/docs links in `OPEN_SOURCE_RESEARCH.md` |
| Previously solved relevant engineering problems | Complete | Problem register with evidence, NEXUS strategy and required tests in `OPEN_SOURCE_RESEARCH.md` |
| Strengths, weaknesses, adoption and avoidance | Complete | Deep reviews and adoption matrix in `OPEN_SOURCE_RESEARCH.md` |
| License and originality review | Complete for research candidates | Candidate license table, no code copied, distribution review limits in `OPEN_SOURCE_RESEARCH.md` and `THIRD_PARTY_NOTICES.md` |
| Existing code audit without source modification | Complete | Feature inventory and risks below; source untouched during Phase 0 |
| Competitive analysis | Complete | `COMPETITIVE_ANALYSIS.md` |
| Architecture and diagrams | Complete | `ARCHITECTURE.md` |
| Technical decisions | Complete | `TECHNICAL_DECISIONS.md` |
| MVP and acceptance criteria | Complete | `MVP_SCOPE.md` |
| Roadmap with prioritized IDs | Complete | `DEVELOPMENT_ROADMAP.md` |
| Required persistent docs and agent instructions | Complete | `AGENTS.md` and docs listed in `NEXT_STEPS.md` |
| Performance budgets distinguished from results | Complete | Proposed budgets in `ARCHITECTURE.md`; actual baseline facts below |

**Phase 0 research gate: complete.** This authorizes beginning the source implementation cycle. It does not mean the application is complete or that every candidate dependency is approved for adoption.

## Existing project and Git
- Existing project preserved; Python 3.11+ / PySide6 architecture and Windows-specific collectors remain intact.
- Local Git repository initialized as authorized. `.gitignore` excludes Python caches, virtual environments, build outputs, logs, databases, reports/exports, screenshots, and IDE files. No secrets or personal files were identified in the project file inventory; commit candidates are project source/config/docs/tests only.
- No Git user.name or user.email is configured. No initial commit was created and global configuration was not changed. Repository currently has all project files untracked.
- Application changes are now limited to NEXUS-001 and NEXUS-003 fixes described below.

## Environment and baseline
- Python 3.14.7; project metadata allows Python >=3.11.
- Installed: PySide6 6.12.0, psutil 7.2.2, pyqtgraph 0.14.0, NumPy 2.5.3, pywin32 312, nvidia-ml-py 13.615.71, pytest 9.2.0, pytest-qt 4.5.0, PyInstaller 6.22.3.
- Baseline `python -m pytest`: **32 passed, 2 failed**. Failures were stale formatting expectations (150% despite intentional 100% clamp; 2400 MHz despite GHz threshold). NEXUS-002 aligned expectations and added an 800 MHz boundary case.
- Baseline offscreen startup (`QT_QPA_PLATFORM=offscreen`, `python -m nexus --no-wmi-sensors`, 5s): exposed chart label `setText` AttributeError and worker `QTimer.TimerType` AttributeError. NEXUS-001 switched to public `AxisItem.setLabel()` and `Qt.TimerType.CoarseTimer`.
- Post-fix bounded offscreen startup stayed alive through 5 seconds, wrote no new error to the NEXUS log, and was then terminated by the startup-check harness. This confirms event-loop startup in offscreen mode; manual desktop verification remains pending.
- NEXUS-003 synthetic tests caught disk activity double division; corrected percent conversion and changed counter-reset rate to unavailable (`None`) rather than zero. Added CPU, memory, disk, network and rate fixtures.
- NEXUS-004 added an injectable collector factory and tests for worker start/stop/restart, initialization recovery, and bounded wait during blocked collection.
- NEXUS-005 added six database tests, corrected aggregate bucket grouping, and included WAL bytes in history storage size.
- NEXUS-006 added process race/safety fixtures and creation-time validation before an explicitly requested termination.
- NEXUS-007 added temporary-tree scanner tests for totals, categories, entry limits, cancellation, access-denied reporting, and root/entry symlinks. Symlink cases skip on this host; NTFS junction behavior remains a manual check.
- NEXUS-008 added mocked missing NVML/WMI and NVML initialization-failure tests; base metrics remain available when GPU telemetry is unavailable.
- Latest `python -m pytest -q`: **66 passed, 2 skipped**. One earlier full-suite run terminated with an intermittent native Qt access violation in the worker shutdown test; isolated lifecycle tests and the subsequent full suite passed. Monitor on future runs.
- `python -m compileall -q nexus tests`: passed after NEXUS-008.
- `python -m pip check`: **No broken requirements found.**
- Performance budgets are proposed, not measured. No intensive tests or benchmarks run.
- `python -m pip check`: no broken requirements found.

## Historical feature classification before macOS implementation

| Area | Classification | Evidence / remaining verification |
|---|---|---|
| App bootstrap and UI navigation | Offscreen startup verified; manual UI unverified | Offscreen event loop starts after NEXUS-001 fixes; all-page desktop flow not manually checked |
| CPU/memory/disk/network collection | Partially verified | Synthetic CPU/memory/disk/network/rate tests pass; hardware-level readings remain unverified |
| GPU and temperature | Implemented but unverified | NVML/WMI optional path exists; no hardware absence tests |
| Monitoring worker | Partially verified | Start/stop/restart, init failure recovery, and bounded timeout tests pass; real sensor-stall behavior still needs device testing |
| SQLite history | Partially verified | Schema, query/aggregate, retention, initialization mapping, memory DB, and DB+WAL stats tests pass; long-run growth remains unmeasured |
| Process listing/termination | Partially verified | Synthetic race/permission/identity/safety tests pass; real multi-user Windows behavior remains unverified |
| Recommendations/scoring | Implemented but unverified | Domain rules exist; no rules tests |
| Storage scanner | Partially verified | Temp-tree behavior and mocked denied access pass; symlink creation skipped by host, NTFS junction/mount-point behavior remains unverified |
| Startup analysis/registration | Implemented but unverified | Code exists; Windows behavior/consent tests absent |
| Reports/gaming/settings | Implemented but unverified | Code exists; output/settings tests absent |
| Automated tests | Partial | 43 tests pass for formatting, chart construction/bounds, metric/rate fixtures; more system lifecycle and DB/safety coverage remains |
| README, CI, packaging | Missing/unverified | Not present in project listing |
| macOS support | Missing | No macOS backend or runtime verification |

## Active blockers and risks
- Git baseline commit cannot be made until local Git identity exists; user may configure local repository identity, or continue without a commit. No global config changes.
- Existing requested Windows 10/11 behavior is not manually verified. GUI testing was only attempted offscreen; no real desktop interaction was performed.
- Dependency licenses and Qt deployment terms require resolved-version review before public binary packaging.
- One full-suite run hit a native Qt access violation in bounded worker shutdown; two clean lifecycle/full-suite reruns followed. Keep the thread lifecycle under observation.
- Database long-run growth, live GPU/sensor hardware, real multi-user process races, and NTFS scanner junction/mount-point behavior remain unverified.

## Verification log
- Project/docs/source inspection: completed.
- Open-source research: six selected projects researched and pinned to branch-tip hashes in `OPEN_SOURCE_RESEARCH.md`.
- Git: initialized; no commit because local identity absent.
- Tests: baseline 32 passed / 2 stale expectation failures; current `python -m pytest` — 58 passed.
- Startup: initial offscreen launch failed at chart and QTimer API calls; post-fix offscreen process reached and remained in event loop for 5 seconds without logged errors.
- Dependency health: `python -m pip check` — no broken requirements.



## Previous checkpoint - cross-platform groundwork - 2026-11-24

- Verified project version remains `1.0.0-rc.1`; no release decision or version bump made.
- macOS research and planning are recorded in `MACOS_RESEARCH.md`, `MACOS_ARCHITECTURE.md`, `PLATFORM_COMPATIBILITY.md`, and `MACOS_ROADMAP.md`. Six candidate projects were deeply reviewed at explicit branch snapshots. Findings are research only; no source was copied and no new runtime dependency was added.
- MAC-001 foundation: platform/architecture normalization helpers added in `nexus/platforms/selection.py`; selector is not yet wired into app startup/backend dispatch.
- MAC-002: macOS default paths now use `~/Library/Application Support/NEXUS`, `~/Library/Logs/NEXUS`, and `~/Library/Caches/NEXUS`; existing environment overrides remain. Deterministic tests added.
- Added `assets/nexus.icns` by converting the existing NEXUS-branded ICO; the ICNS container is readable on this host. Native Finder appearance remains unverified.
- The app now refuses to start on macOS in this intermediate build with a clear message rather than presenting the Windows collector/UI as working; unsupported non-Windows/non-macOS platforms are rejected by the selector.
- Conditionalized NVML dependency to Windows and included new platform packages in metadata. Windows behavior is not intentionally changed.
- Current proposed macOS floor is 14.0 based on current Qt/PySide wheel support. macOS 13 would require a pinned compatible Qt/PySide build and separate validation. This is a plan, not a tested platform claim.
- Prepared `.github/workflows/macos-tests.yml` for `macos-15` ARM64 and `macos-15-intel` x64; it is test/compile/dependency CI only and has not run from this local checkout. Current GitHub runner docs list both labels; Intel availability is time-limited.
- Latest tests: `python -m pytest -o addopts='' -q` - **91 passed, 2 skipped**; `python -m compileall -q nexus tests scripts` - passed; `python -m pip check` - passed; `git diff --check` - passed.
- No macOS host was available. No macOS collector, app bundle, DMG, native launch, signing, notarization, or macOS CI run has been completed. macOS app startup remains Windows-wired; do not advertise macOS support.
- Windows `scripts/build_windows.ps1` was rerun after the platform groundwork: it rebuilt `dist/NEXUS/NEXUS.exe`, reran tests, staged notices, and completed the bounded offscreen smoke launch. Inno Setup is missing and no installer was compiled.
- No Git identity/commit, remote, or publication was created.

### Previous checkpoint follow-up plan (superseded)

1. MAC-003: decouple Windows-only bootstrap, page and collector imports, retaining Windows UI and behavior.
2. MAC-004: add isolated psutil-based macOS CPU/memory/disk/network snapshot collector; keep unavailable sensors honest.
3. Keep Windows regression tests passing after every platform step; native API correctness remains unproven until real Mac tests.
4. Build scripts, DMG and cross-platform artifact CI are pending until backend selection and app startup are Mac-capable.
5. Windows installer compilation is complete with Inno Setup 7.1.1; installation, Start Search, upgrade, and uninstall verification remain pending.
