# Open-source research and engineering findings

Research checkpoint: 2026-11-24. To avoid downloading whole projects, upstream branch tips were resolved with `git ls-remote`; selected implementation/docs pages were inspected at the commit IDs below. These are precise snapshots of the inspected branch tips on this date, not immutable release recommendations. No third-party scripts, installers, or application source were executed. No external code was copied.

## Candidate scan (12 repositories)

| Project | URL | License checked | Why relevant / selection |
|---|---|---|---|
| psutil | https://github.com/giampaolo/psutil | BSD-3-Clause | Cross-platform metrics/process API; deep review |
| LibreHardwareMonitor | https://github.com/LibreHardwareMonitor/LibreHardwareMonitor | MPL-2.0 | Windows sensor backend and hardware variation; deep review |
| pyqtgraph | https://github.com/pyqtgraph/pyqtgraph | MIT | Current NEXUS plotting dependency; deep review |
| Glances | https://github.com/nicolargo/glances | LGPL-3.0-only | Python/psutil collectors and plugin architecture; deep review |
| WinDirStat | https://github.com/windirstat/WinDirStat | GPL-3.0-or-later at reviewed snapshot | Windows file traversal and storage UX; deep review |
| System Informer | https://github.com/winsiderss/systeminformer | MIT at reviewed snapshot | Process/system inspection; deep review |
| OpenHardwareMonitor | https://github.com/openhardwaremonitor/openhardwaremonitor | MPL-2.0 | Historical hardware-monitor architecture; candidate only |
| Mission Center | https://gitlab.com/mission-center-devs/mission-center | GPL-3.0 (upstream metadata) | Native Linux system monitor; platform/UX comparison |
| btop | https://github.com/aristocratos/btop | Apache-2.0 | Compact resource monitor; interaction comparison |
| Netdata | https://github.com/netdata/netdata | GPL-3.0 | Metric lifecycle, retention, observability; scale contrast |
| BleachBit | https://github.com/bleachbit/bleachbit | GPL-3.0 | Cleaner actions and safety boundary |
| MangoHud | https://github.com/flightlessmango/MangoHud | MIT | Gaming overlay and session metrics |

License values above are repository-level metadata or upstream license text reviewed for candidates; they do not imply code reuse. For projects where only candidate screening was done, verify the exact selected release license before dependency or source adoption. The macOS app Stats was listed in earlier candidate notes but excluded from the final set in favor of System Informer, a closer Windows/process comparison.

## Deep reviews and exact snapshots

### psutil — `a00aa9ef6c9b01c248663a425905e35599f276f3`
License: BSD-3-Clause (`LICENSE`). Inspected `psutil/__init__.py`, Windows backend `_pswindows.py`, CPU system tests, and API docs. The public CPU percentage method compares counter snapshots: a nonblocking first call is a meaningless 0.0 baseline, and docs recommend spacing samples for accuracy. Windows backend converts OS errors to `NoSuchProcess` or `AccessDenied`; its `process_iter` and Windows process implementations anticipate process churn and access restrictions. `memory_physical()` documents that “used”/“available” semantics differ by platform; Windows CPU frequency does not support per-CPU frequency. References: [implementation](https://github.com/giampaolo/psutil/blob/a00aa9ef6c9b01c248663a425905e35599f276f3/psutil/__init__.py), [Windows backend](https://github.com/giampaolo/psutil/blob/a00aa9ef6c9b01c248663a425905e35599f276f3/psutil/_pswindows.py), [CPU tests](https://github.com/giampaolo/psutil/blob/a00aa9ef6c9b01c248663a425905e35599f276f3/tests/test_system.py), [license](https://github.com/giampaolo/psutil/blob/a00aa9ef6c9b01c248663a425905e35599f276f3/LICENSE), [API docs](https://psutil.readthedocs.io/en/latest/#psutil.cpu_percent).

Verified problem/lesson: first sample cannot represent a real interval; process rows race with exit and permissions. NEXUS CPU collector primes psutil and samples from a persistent worker; process manager catches per-process failures. Improvement proposed: model warm-up explicitly for all rate collectors, keep time deltas monotonic, add fake-counter tests, and test process identity revalidation under PID reuse. Do not normalize cross-platform fields as if identical.

### LibreHardwareMonitor — `9e2d677cefff5c614ecc38da88fbc447eb478e2a`
License: Mozilla Public License 2.0. Inspected repository/license, release notes and issue/PR evidence. [PR #933](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/pull/933) fixed incorrect total CPU load on Windows 11 22H2. Release notes record avoiding a crash when NVML is unavailable and multiple sensor/backend corrections. [Issue #2536](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/issues/2536) reports duplicate sensor keys causing dictionary exceptions. References: [license](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/blob/9e2d677cefff5c614ecc38da88fbc447eb478e2a/LICENSE), [release history](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases), [PR #933](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/pull/933), [issue #2536](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/issues/2536).

Verified problem/solution: Windows changes can invalidate CPU-load assumptions; optional NVML failure must not crash monitoring; sensor keys are not always unique. NEXUS uses optional NVML/WMI and separate collector modules, and the aggregate collector isolates failures. Adopt optional initialization, capability reporting, unique composite identities, and sanity/absence tests. Avoid claiming universal sensor coverage or importing the MPL library/source without licensing and packaging review.

### pyqtgraph — `3fbfd734ce866b1084b472ed14989929ff8a96a6`
License: MIT (`LICENSE.txt`). Inspected `examples/scrollingPlots.py`, `PlotItem` downsampling API, changelog, and issue #3301. The example recommends fixed arrays and demonstrates downsampling/clipping to reduce draw work; docs define peak/mean/subsample downsampling. Issue [#3301](https://github.com/pyqtgraph/pyqtgraph/issues/3301) reports slow average/peak downsampling on large datasets: downsampling is not a universal cure. References: [scrolling example](https://github.com/pyqtgraph/pyqtgraph/blob/3fbfd734ce866b1084b472ed14989929ff8a96a6/pyqtgraph/examples/scrollingPlots.py), [PlotItem API](https://github.com/pyqtgraph/pyqtgraph/blob/3fbfd734ce866b1084b472ed14989929ff8a96a6/pyqtgraph/graphicsItems/PlotItem/PlotItem.py), [issue #3301](https://github.com/pyqtgraph/pyqtgraph/issues/3301), [license](https://github.com/pyqtgraph/pyqtgraph/blob/3fbfd734ce866b1084b472ed14989929ff8a96a6/LICENSE.txt).

NEXUS `TimeSeriesChart` already uses bounded deques (default 180 samples), clips to view and updates existing curves. Keep that pattern; profile redraw cost and avoid repeated full history plot updates. Do not assume downsampling helps at all history sizes.

### Glances — `68760f16bbbba188d8bd3d69eec8986ee6c18bf1`
License: LGPL-3.0-only (`pyproject.toml`/license text). Inspected Python API docs, plugin documentation/architecture, release notes and issue/PR listings. Its API allows selection of plugins, background collection and read-only mapped plugin data; plugin fields can expose descriptions, thresholds, levels and histories. A recent release note documents restoring a history CLI option that had been silently ignored, with plugin tests added to make focused regression checks possible. Windows sensor support is pursued as optional LHM integration (PR #3613 listed in upstream PRs). References: [Python API](https://github.com/nicolargo/glances/blob/68760f16bbbba188d8bd3d69eec8986ee6c18bf1/docs/api/python.rst), [plugin architecture](https://github.com/nicolargo/glances/blob/develop/.claude/docs/architecture.md), [release notes](https://github.com/nicolargo/glances/releases), [PR listing](https://github.com/nicolargo/glances/pulls), [license metadata](https://github.com/nicolargo/glances/blob/develop/pyproject.toml).

Adopt explicit per-metric metadata and independently testable collector boundaries. Avoid its broad exporters/server/plugin surface for the offline desktop MVP; breadth increases packaging and verification work. The history-flag regression supports testing settings-to-service wiring, not just a model function.

### WinDirStat — `832a63b514a9d8b7f4e61c48e4aff0c134ef3976`
License: GPL-3.0-or-later (`LICENSE.md`, application; read README for more lenient terms on some components). Inspected `FinderBasic.cpp`, `WinDirStatModel.cpp`, README and changelog. Source reads reparse tags and distinguishes mount points from junctions; options govern which reparse points are followed. Changelog reports reparse enumeration fixes, scan stalls on unresponsive mappings, a file watcher race, and safety correction so “Remove Empty Folders” does not remove reparse targets. References: [FinderBasic.cpp](https://github.com/windirstat/WinDirStat/blob/832a63b514a9d8b7f4e61c48e4aff0c134ef3976/windirstat/FinderBasic.cpp), [model](https://github.com/windirstat/WinDirStat/blob/832a63b514a9d8b7f4e61c48e4aff0c134ef3976/windirstat/WinDirStatModel.cpp), [changelog](https://github.com/windirstat/WinDirStat/blob/832a63b514a9d8b7f4e61c48e4aff0c134ef3976/CHANGELOG.md), [license](https://github.com/windirstat/WinDirStat/blob/832a63b514a9d8b7f4e61c48e4aff0c134ef3976/LICENSE.md).

Adopt explicit reparse-point handling and separate scanning from cleanup. NEXUS's scanner intentionally skips reparse points, reports inaccessible paths, checks cancellation and limits retained errors; verify on NTFS junctions and volume mount points. Do not copy GPL code into the MIT project without resolving license compatibility; inspiration only.

### System Informer — `b365d1a89e104abe014ff2d853e8b91807d0defd`
License: MIT (`LICENSE.txt`) at the inspected commit (older snapshots differ; always pin the version). Inspected exported API declarations including `PhEnumProcesses`, project README and issue tracker. The project exposes a broad process/system API surface and uses native Windows facilities; this is a Windows-specific engineering reference, not a Python dependency. Issue [#3110](https://github.com/winsiderss/systeminformer/issues/3110) reports a CPU usage display crash on ARM64, a reminder that architecture-specific paths need validation. References: [API export declarations](https://github.com/winsiderss/systeminformer/blob/b365d1a89e104abe014ff2d853e8b91807d0defd/SystemInformer/SystemInformer.def), [license](https://github.com/winsiderss/systeminformer/blob/b365d1a89e104abe014ff2d853e8b91807d0defd/LICENSE.txt), [issue #3110](https://github.com/winsiderss/systeminformer/issues/3110), [project](https://github.com/winsiderss/systeminformer).

Adopt its lesson that process/system inspection is a deep platform concern and permission/architecture boundaries are real. Keep NEXUS on psutil plus narrow Windows APIs for MVP. Avoid importing its breadth or using undocumented/native APIs without a demonstrated gap and dedicated tests.

## NEXUS problem register: evidence, strategy, verification

| Problem and cause | Evidence / established response | NEXUS strategy | Tests required |
|---|---|---|---|
| CPU utilization is a delta, not an instantaneous sensor; first sample is baseline | psutil docs/source and tests; LHM PR #933 also shows Windows version changes can affect totals | Persistent collector; discard/mark warm-up unavailable; monotonic deltas for own rates; define total/per-core semantics | Fake counters, first sample, reset, idle/load; Windows 10/11 manual cross-check |
| Cross-platform metric meaning differs | psutil API marks platform availability and semantics, e.g. memory available/used and Windows frequency | Metric unit/source/platform capability in model; avoid sharing OS-specific assumptions | Contract tests per simulated backend and Windows manual tests |
| GPU vendors/driver APIs differ | LHM optional NVML fix/release history; Glances PR requests LHM Windows temperatures | MVP NVIDIA NVML optional, report unsupported/unavailable; later explicit AMD/Intel backend exploration | NVML absent, driver absent, API exception, multiple GPU tests |
| Missing temperature/sensors and duplicate names | LHM issues #2536 and wide board-specific fixes | `None`/capability explanation; identity composite; isolate sensor exceptions | duplicate IDs, missing/invalid/range tests; hardware manual checks |
| Disk/network rates need counter deltas; adapter/device disappearance or reset | psutil counter APIs; NEXUS `RateTracker` uses monotonic time | Keep first/reset rate unavailable; remove stale adapter baseline; validate deltas | first sample, zero elapsed, counter reset, interface changes, no counters |
| Chart performance and memory | pyqtgraph fixed buffers; #3301 shows downsampling itself can be costly | Keep bounded chart buffers and update frequency; measure real redraw instead of relying on auto downsampling | bounded buffer, NaN gap, repeated update, manual responsiveness |
| Worker shutdown/UI responsiveness | Qt worker ownership in existing NEXUS; no sourced proof that one thread is sufficient for every backend | Stop timers/collectors on owning thread, bounded join, visible failure state; isolate slow optional sensor if measurements justify | stop before/after start, worker exceptions, slow fake collector, no UI-thread blocking |
| Process enumeration races/permissions/PID reuse | psutil wraps OS errors into `NoSuchProcess`/`AccessDenied`; System Informer exposes native APIs and architecture-specific failures | Per-process isolation, revalidate PID/name/create time before action; explicit confirm, graceful terminate | exits during read, denied access, PID reuse, protected processes, termination timeout |
| SQLite growth and retention | NEXUS repository already has WAL, timestamp index, retention cleanup, range limits and aggregation; Glances history regression shows wiring can fail | Keep local retention; measure DB+WAL growth; cleanup in bounded transaction; test failure fallback | retention delete, WAL checkpoint policy, corruption fallback, volume growth estimate |
| Directory traversal, reparse loops, inaccessible paths | WinDirStat source/change log shows reparse-point fixes, hangs, and cleanup hazards; Microsoft's reparse point docs | User-selected root; skip reparse points; cancellable iterative scan; bounded results/errors; read-only | junction to ancestor/outside, symlink, mount point, denied path, cancellation, large tree |
| Graceful error recovery | psutil error conversion; Glances optional plugin boundaries; LHM optional backend crash history | Collector-level exception isolation, clear unavailable states, local logs without sensitive payloads | injected backend errors, repeated failures, recovery on later sample |

CPU, chart and filesystem findings above are verified upstream. Worker and SQLite improvements are NEXUS-specific proposals inferred from inspected implementation and have to be validated locally; they are not claimed as upstream solved defects.

## Adoption matrix

| Technique | Source | Benefit | Cost / disadvantage | Decision |
|---|---|---|---|---|
| psutil baseline collectors, per-process exception handling | psutil | Mature common metrics, platform implementations | semantics/availability vary | Adopt, add NEXUS tests |
| Optional hardware backend and capability model | LHM issues/releases | Extra sensors without hard requirement | vendor/driver/permission variability | Adopt boundary; no dependency/code copy yet |
| Bounded plot points and queued updates | pyqtgraph example + NEXUS | Resource bound and responsive UI | bounded timeline limits detail | Preserve, measure |
| Isolated collector/plugin contracts | Glances | One optional failure need not collapse the app | dynamic plugin system overkill | Adopt narrow interface only |
| Explicit reparse-point policy, scan/cleanup separation | WinDirStat source/changes | Avoid loops and data outside root | unsupported path types omitted | Preserve safe skip behavior |
| Conservative Windows process abstraction | System Informer | Understand edge cases and OS semantics | native complexity/licensing concerns | Study only; use psutil first |

## Licensing / originality
Current NEXUS license is MIT. No code was copied or adapted. Candidate licenses vary: MPL-2.0 (LHM), LGPL-3.0-only (Glances), GPL-3.0-or-later (WinDirStat), MIT (pyqtgraph and reviewed System Informer snapshot), BSD-3-Clause (psutil). Keep all as research-only. For distribution, resolve exact dependency versions, include notices, and review PySide6/Qt distribution terms. Review license changes across versions; System Informer specifically demonstrates why version pinning matters. See `THIRD_PARTY_NOTICES.md` for NEXUS's dependency inventory.
