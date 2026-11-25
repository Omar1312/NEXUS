# MVP scope

The repository already contains code for many proposed functions, but none is classified complete until acceptance criteria and tests verify it. MVP goal: a trustworthy Windows desktop monitor with a small set of genuinely working, understandable capabilities.

## Must have

| Feature | Acceptance criteria | Complexity / risks |
|---|---|---|
| Launch, navigation, settings | On clean Windows 10/11 x64 standard-user account, cold start reaches interactive dashboard in <=5s on documented reference machine; all 10 pages load; invalid settings do not crash; normal shutdown completes <=3s and no worker survives | Medium; Qt lifecycle |
| CPU, memory, disk and network live metrics | CPU and memory update every configured interval (default 2s); disk/network rates use monotonic deltas and first/reset sample is unavailable; units documented; metrics match API within rounding on synthetic fixtures and representative manual checks | Medium; counter semantics |
| Capability and error status | Absent NVIDIA driver/NVML and missing CPU sensor show “Unavailable” plus explanation; injected optional backend failure does not stop CPU/RAM/disk/network | Medium; hardware variability |
| Bounded charts | Every series has finite max points (default 180); missing sample creates a gap; charts receive <=1 update per new snapshot and UI input p95 stays <=100ms under ordinary load | Low/medium |
| Local history | Schema/version initializes; temp DB writes and queries exact values/ranges; retention removes older rows; history storage target <=100MiB for 30 days at default sample interval or target is revised from measured growth; DB failure fallback remains usable | Medium; DB/migrations |
| Safe process view | Enumeration survives exit/access-denied races; sort/search deterministic; termination requires confirmation, revalidates PID/name/create time, sends graceful request only, and reports timeout honestly | Medium/high; safety |
| Tested recommendation rules | Every displayed recommendation identifies measured evidence and threshold; missing data suppresses rule; rule fixtures cover boundaries; no automatic system change | Medium; false positives |
| Logs and docs | Local rotated logs, accurate supported-platform and limitation statements | Low |

## Should have
Read-only storage scan for user-selected path with progress/cancel and reparse-point protections; startup entry inspection and optional per-user startup toggle; CSV history export. Proposed acceptance: cancellation acknowledged within 1 second at the next directory boundary; scan never follows symlink, junction or mount point and never starts without user action. Windows edge-case tests are required before release.

## Could have
Gaming session summary, report generation, GPU telemetry for installed/available NVIDIA backend, configurable themes.

## Future release
Advanced startup impact scoring, richer sensor backends, history aggregation, HTML report polish, installer/signing, macOS support after dedicated implementation and tests.

## Out of MVP
Automatic cleanup, registry edits, automated process termination, security/antivirus changes, overclocking/fan control, remote telemetry, cloud accounts, full-drive scan by default, universal GPU/temperature claims.

## Release acceptance
Install/run on clean Windows 10 and 11 x64 standard-user environments; pass deterministic tests; manually exercise missing GPU backend, denied process/path, cancel scan, DB fallback, and shutdown; document measured overhead method and results only after actually measuring. No screenshots/benchmarks fabricated.
