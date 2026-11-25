# macOS architecture proposal

Implementation checkpoint 2026-11-24. Native validation remains required. Preserve the current module layout and introduce only a narrow platform boundary.

## Existing architecture audit

Shared: UI widgets/layout, SQLite/history, settings, reports, charts, health scoring, gaming session records, process/storage domain logic. Metric fields can be unavailable. Collection runs on a worker.

Windows-specific hotspots found:

- `nexus/hardware/windows.py`: registry, Windows identity/build metadata, adapter naming and OS helpers.
- `nexus/hardware/pdh.py`: Windows Performance Data Helper.
- `nexus/hardware/cpu.py`, `gpu.py`, `sensors.py`: import Windows helpers; GPU uses NVML only.
- `nexus/core/collectors.py`: now selects a lazy macOS psutil collector or the preserved Windows backend.
- `nexus/app.py`: Windows admin/build helpers are imported only on Windows; the shared app bootstrap now starts on macOS.
- Startup inspection now has a read-only user LaunchAgents scanner; Windows registration remains Windows-only. Shell helpers route to Finder on macOS.
- UI text/actions in dashboard, hardware, optimizer, settings, process, startup, main window/sidebar contain Windows assumptions.
- `nexus/utils/paths.py`: Windows uses LocalAppData; other platforms currently use `~/.nexus`, not macOS Application Support/Logs/Caches.
- `pyproject.toml`: pywin32 is conditional on win32, but NVML is unconditional; package metadata is Windows-specific. Existing installer/build scripts are Windows-only.
- `nexus/services/update_service.py`: Windows installer asset/launch contract.

Safe module import does not guarantee safe construction: collector constructors instantiate PDH, NVML or Win32 helpers. Backend selection must happen before those imports/constructions.

## Target boundary

Keep the existing layers. Introduce a small `nexus/platforms` selector and `nexus/platforms/macos` backend; leave current Windows modules in place. Both backends implement the existing `collect()`, `system_info()`, `capabilities()` and `close()` service contract, producing shared snapshot models. UI remains shared and uses capability/platform descriptors for labels and actions.

```text
UI -> services -> shared Snapshot/metrics
                     |-> Windows collectors (existing)
                     |-> macOS psutil baseline (planned)
shared: database, reports, charts, history, settings, safe score
OS boundary: collectors, paths, process actions, startup inspection, update installer
```

### Contracts

- `platform_id()` yields `windows` or `macos`; unsupported OS gets a clear bootstrap message.
- Platform factory lazily imports the selected backend. Unsupported metrics remain `None` with an availability note, not zero.
- psutil is the baseline for CPU time, memory, I/O/network and process listing; API errors are isolated per metric/row. Any subprocess is bounded and optional.
- macOS settings/database/history: `~/Library/Application Support/NEXUS`; logs: `~/Library/Logs/NEXUS`; disposable caches: `~/Library/Caches/NEXUS`. Preserve environment overrides and never write into the app bundle.
- Process termination stays explicit and validates PID plus creation time; no elevation or privacy bypass.
- Initial startup analyzer is read-only and current-user scoped; no system LaunchDaemons or mutation.
- Update selection uses OS + architecture + channel + version. First macOS update flow is user-confirmed DMG/manual installation; no automated bundle replacement.

## Metric semantics

- CPU uses psutil time deltas. Do not show per-core MHz (psutil documents it unsupported). Delay performance/efficiency cluster split until source and logical mapping are verified.
- Memory shows system RAM once, including Apple Silicon unified memory. No dedicated VRAM capacity. Memory pressure stays unavailable until a supported source is implemented; scoring must not penalize missing telemetry.
- GPU uses no NVML on Mac. Initially show identity only if discovered; utilization, temperature and power unavailable absent validated source. IOReport is private/unstable and excluded from baseline.
- Disk/network use psutil counters with monotonic deltas; APFS volume/container deduplication needs native verification. Selected-folder scanner does not follow symlinks by default.
- Sensor, fan and battery availability is capability-specific. Distinguish not applicable (fanless/no battery) from unsupported or permission denied. Do not require root.
- Recommendations and health score use platform-specific validated inputs. Do not reuse Windows disk busy-time, low-free-memory, NVIDIA VRAM or startup rules on macOS.

## UI behavior

Retain NEXUS dark theme, layouts, cards and pages. Keep Windows UI unchanged. Replace Windows-specific titles, labels, shortcuts and dialogs on Mac; use Command shortcuts, native file dialogs and standard window controls. Verify Retina scaling/accessibility on a Mac. Unsupported actions should explain their state, not show Windows errors.

## Minimum macOS and architectures

Proposed floor: macOS 14.4. Qt 6.12 documents macOS 14.4+ as its target floor. Qt 6.10 and PySide6 6.11.2 support macOS 13.0 for x86_64 and arm64, so macOS 13 could be chosen only after pinning a compatible Qt/PySide line and validating the frozen app. Build separate ARM64 and x86_64 initially. Claim universal2 only after auditing every extension/dylib with `file`/`lipo` and running on both CPU families.

## Failure and testing model

Collector creation is isolated; optional-source failure disables that capability but leaves other metrics alive. Windows-hosted mocks prove dispatch and data mapping only, not macOS API correctness. Native tests on macOS 14+ ARM64 and Intel are release gates.
