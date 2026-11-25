# Platform compatibility matrix

Based on source audit and research as of 2026-11-24. macOS implementation is present locally; native CI/build/device verification remains pending and no installers have been published.

| Feature | Windows 10/11 x64 | macOS ARM64 planned | macOS x86_64 planned | Permission/limits |
|---|---|---|---|---|
| UI/navigation/charts/theme | Implemented; owner accepted appearance | Shared UI adapted, native menu/shortcut/Retina review pending | Shared UI, native review pending | No extra permission |
| Dashboard CPU/per-core/history | Implemented and tested | Implemented psutil baseline; E/P split deferred | psutil baseline; no E/P split | No root; native tests needed |
| CPU model/frequency/temp | Registry/PDH, optional WMI | Model via sysctl/psutil; frequency/temp initially unavailable | Same baseline | No private API/elevation initially |
| GPU | NVIDIA NVML; other adapters partial | Identity if discoverable; metrics unavailable initially | Identity if discoverable; metrics unavailable initially | No NVML on Mac |
| RAM/health score | Windows memory semantics | Unified RAM, no dedicated VRAM; pressure unavailable | System RAM and platform-specific pressure | No missing-metric penalty |
| Disk | Windows capacity/activity counters | psutil mounts/counters; APFS duplicates require validation | psutil mounts/counters | Selected paths only; honor access limits |
| Network | Implemented | psutil counters | psutil counters | Interface churn/disconnect handling |
| Hardware Monitor | Windows info, NVML/WMI | Model/OS/RAM/storage/network; battery optional; sensors not initially | Same baseline | Device-dependent sensors; no root |
| Process Manager | List/detail and confirmed graceful close | psutil list/details, permission aware | Same | Confirm and revalidate before signal |
| Optimization Center | Windows-specific rules | New validated rules required | New validated rules required | No destructive action |
| Startup Applications | Registry/folders read-only | Read-only current-user LaunchAgent plist scan; active Login Items state not queried | Same | System daemons unsupported initially |
| Storage Analyzer | Scanner; junction behavior still unverified | Selected folder; APFS/packages/cloud placeholder checks pending | Selected folder | No Full Disk Access by default |
| Gaming Mode | Manual session and metrics | Manual session/history; GPU/thermal initially unavailable | Same | No FPS claim or tuning |
| History/database/reports | Shared SQLite, migrations, exports | Shared schema; add platform/capability metadata safely | Same | Migration required if schema changes |
| Settings/logs/exports | `%LOCALAPPDATA%\Nexus` | `~/Library/Application Support/NEXUS`, Logs, Caches planned | Same | Outside app bundle |
| Startup registration | Explicit Windows user registry | Unsupported initially; may open Login Items | Same | No silent changes |
| Update discovery/download | Implemented, repo unconfigured | Architecture-specific updater asset selection and manual DMG install; unsigned until credentials | x64 DMG, manual install | Require trusted auth before executing downloaded update |
| Packaging | PyInstaller folder built; Inno installer pending | `.app`/ARM64 DMG build scripts and CI; native run pending | `.app`/x64 DMG build scripts and CI; native run pending | Real Mac required |
| Signing | Windows executable unsigned | Unsigned/notarized status | Unsigned/notarized status | Developer ID and notary flow for public distribution |

Unavailable sensors must be reported as unavailable, never zero. No Mac hardware was available for testing.
