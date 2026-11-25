# macOS monitoring research

Research checkpoint: 2026-11-24. These repositories are research inputs, not approved dependencies. Branch hashes below were queried from the GitHub API on this date. No third-party source was copied or executed.

## Candidate scan

| Project | Identity / license | Snapshot and relevance |
|---|---|---|
| [Stats](https://github.com/exelban/stats) | Native macOS menu-bar monitor; MIT | `78bfd3b62bcd5cf5b61feddaa49dd44fe89b3332`; broad CPU/GPU/memory/sensor/battery modules |
| [btop](https://github.com/aristocratos/btop) | Cross-platform terminal monitor; Apache-2.0 | `5d03929a45e0720a4c8e2d189360ff1eb9ce1731`; explicit `src/osx` backend; x86_64/ARM64 releases |
| [Glances](https://github.com/nicolargo/glances) | Python cross-platform monitor; LGPL-3.0 | `68760f16bbbba188d8bd3d69eec8986ee6c18bf1`; develop snapshot; stable release reported as 4.5.9 |
| [psutil](https://github.com/giampaolo/psutil) | Python system/process library; BSD-3-Clause | `a00aa9ef6c9b01c248663a425905e35599f276f3`; existing NEXUS dependency |
| [asitop](https://github.com/tlkh/asitop) | Apple Silicon CLI using powermetrics; MIT | `74ebe2cbc23d5b1eec874aebb1b9bacfe0e670cd`; ARM-only, Monterey, sudo requirement |
| [macmon](https://github.com/vladkens/macmon) | Apple Silicon monitor; MIT | `f8311a0c7ab09053841d52dec4ab9915e60494c2`; releases address new SoC and OS changes |
| [osx-cpu-temp](https://github.com/lavoiesl/osx-cpu-temp) | SMC sensor utility; GPL-2.0 | `57aadd7690638022f5f3908f131144170559eebc`; historical sensor reference |
| [Netdata macOS collector](https://github.com/netdata/netdata/tree/master/src/collectors/macos.plugin) | Native collector; GPL-3.0 project | Docs cover system, battery, IOReport, SMC/IOHID, powermetrics and NVMe |
| [gptop Apple backend](https://github.com/evilsocket/gptop/blob/main/docs/backends/apple.md) | Apple Silicon GPU backend; GitHub API has no asserted SPDX license | `9265a8c260c9c80252da8742bab4043ac0833b63`; not an adoption candidate until license review |
| [iStats](https://github.com/Chris911/iStats) | Ruby CLI for Mac sensors/battery; MIT | `15813fe211e31425f7d0ad0e1018ef3102d16664`; distinct from the Stats GUI; no dependency planned |

“Stats Menu” resolves to exelban Stats; no separate authoritative upstream was identified. The supplied candidate `ashishb/istats` returned GitHub API 404; the identifiable iStats project is Chris911/iStats. iStats was identified as a Ruby sensor command-line tool but was not deeply analyzed. Discovery-level findings only for candidates other than the six deep reviews below.

## Deep technical reviews

### psutil

Inspected `master` snapshot `a00aa9ef6c9b01c248663a425905e35599f276f3`; BSD-3-Clause. Sources: [macOS backend](https://github.com/giampaolo/psutil/blob/a00aa9ef6c9b01c248663a425905e35599f276f3/psutil/_psosx.py), [license](https://github.com/giampaolo/psutil/blob/a00aa9ef6c9b01c248663a425905e35599f276f3/LICENSE), [changelog](https://github.com/giampaolo/psutil/blob/a00aa9ef6c9b01c248663a425905e35599f276f3/docs/changelog.rst), [docs](https://psutil.readthedocs.io/).

**Findings:** Its common API hides OS-specific collectors. `_psosx.py` explicitly documents unsupported per-CPU frequency. Process fields can fail independently due to exit races or permissions. Changelog records macOS-specific process errors and distinct Intel/arm64 wheel floors. This demonstrates that shared API does not guarantee equal semantics or availability.

**Apply:** Use psutil for baseline CPU time deltas, memory, I/O/network counters and process listing. Preserve unavailable values; never invent frequency/GPU data. Catch `AccessDenied`, `NoSuchProcess`, `ZombieProcess` per field. Test counter reset/first sample and permission/disappearance with fakes and native two-sample checks on Intel and ARM64.

### Stats

Inspected `master` snapshot `78bfd3b62bcd5cf5b61feddaa49dd44fe89b3332`; MIT. Sources: [README](https://github.com/exelban/stats/blob/78bfd3b62bcd5cf5b61feddaa49dd44fe89b3332/README.md), [license](https://github.com/exelban/stats/blob/78bfd3b62bcd5cf5b61feddaa49dd44fe89b3332/LICENSE), [issues](https://github.com/exelban/stats/issues), [privileged helper advisory](https://github.com/exelban/stats/security/advisories/GHSA-qwhf-px96-7f6v), [new-device sensor issue](https://github.com/exelban/stats/issues/3759).

**Findings:** Modular native app covering CPU/GPU/memory/sensors/battery/network. README says it is primarily maintained by one person and unsolicited PRs generally are not accepted. A recent issue reports zero sensor power on a new device; security advisory documents client verification risk in a privileged helper able to perform elevated operations. Hardware channels vary and helper boundaries need strict validation.

**Apply:** Adopt modular optional collectors and graceful absence. Avoid helper tools, fan control, elevated command execution, and interpreting zero as valid without API/range checks. Test missing/zero/error sensor values; native device matrix remains required.

### btop

Inspected `main` snapshot `5d03929a45e0720a4c8e2d189360ff1eb9ce1731`; Apache-2.0. Sources: [`src/osx`](https://github.com/aristocratos/btop/tree/5d03929a45e0720a4c8e2d189360ff1eb9ce1731/src/osx), [sensor implementation](https://github.com/aristocratos/btop/blob/5d03929a45e0720a4c8e2d189360ff1eb9ce1731/src/osx/sensors.cpp), [releases](https://github.com/aristocratos/btop/releases).

**Findings:** Explicit per-OS backend; x86_64 and ARM64 macOS distribution. Sensor source uses IOKit/IOHID and guards declarations by OS availability. Release history contains macOS crash/swap fixes. Some sensor/GPU/power paths across platforms require extra capabilities.

**Apply:** Isolate platform collection and gate optional APIs. Do not copy its low-level code or adopt privileged capabilities. Test graceful API absence and native crash/resource behavior before sensor support.

### Glances

Inspected `develop` snapshot `68760f16bbbba188d8bd3d69eec8986ee6c18bf1`; stable release at research time reported 4.5.9; LGPL-3.0. Sources: [repository snapshot](https://github.com/nicolargo/glances/tree/68760f16bbbba188d8bd3d69eec8986ee6c18bf1), [releases](https://github.com/nicolargo/glances/releases), [macOS filesystem alias issue](https://github.com/nicolargo/glances/issues/3370).

**Findings:** Python monitor with psutil baseline and optional plugin architecture. Release notes document cross-platform fixes. Issue #3370 documents a macOS filesystem alias failure, showing generic path logic can miss platform behavior. Its broad optional server/plugin surface adds dependency and license review burden.

**Apply:** Reuse capability-focused modularity, not server/cloud features. Explicitly model aliases, mounts and permissions in the scanner. Test path fixtures, symlink loops, mount boundaries, denied access and APFS natively.

### asitop

Inspected `main` snapshot `74ebe2cbc23d5b1eec874aebb1b9bacfe0e670cd`; MIT. Sources: [README](https://github.com/tlkh/asitop/blob/74ebe2cbc23d5b1eec874aebb1b9bacfe0e670cd/README.md), [source](https://github.com/tlkh/asitop/tree/74ebe2cbc23d5b1eec874aebb1b9bacfe0e670cd/asitop), [issues](https://github.com/tlkh/asitop/issues).

**Findings:** Apple Silicon-only. Uses `powermetrics` for utilization/frequency/power; psutil for memory/swap; sysctl for CPU identity/count; system_profiler for GPU cores. It states sudo is required and notes counters removed by Apple. This is unsuitable as an ordinary least-privilege GUI baseline.

**Apply:** Do not prompt for sudo or assume counters exist. Use psutil/sysctl baseline; leave GPU/thermal/power unavailable unless a tested, supported nonprivileged API exists. If subprocess sampling is later added, bound runtime and parse versioned fixtures.

### macmon

Inspected `main` snapshot `f8311a0c7ab09053841d52dec4ab9915e60494c2`; MIT; inspected release history included v0.12.0. Sources: [snapshot](https://github.com/vladkens/macmon/tree/f8311a0c7ab09053841d52dec4ab9915e60494c2), [release history](https://github.com/vladkens/macmon/releases), [license](https://github.com/vladkens/macmon/blob/f8311a0c7ab09053841d52dec4ab9915e60494c2/LICENSE).

**Findings:** Apple Silicon focused; release fixes include new SoC frequency detection and power readings under changed macOS permission behavior. This confirms non-static support across SoCs/OS releases.

**Apply:** Use model-aware capabilities and keep sensor cadence/data age explicit. Do not parse a separate CLI's display as a stable API or rely on undocumented channels without compatibility tests.

## Engineering problem register

| Problem/cause | NEXUS strategy | Test |
|---|---|---|
| CPU first-sample/reset semantics and per-core APIs vary | psutil time deltas; first/reset unavailable; no per-core MHz | deterministic delta fixtures and native Intel/ARM64 two-sample comparison |
| P/E clusters don't map to logical indexes | Defer cluster split until stable supported source and mapping exist | only enable with model-specific native fixture and live check |
| Unified memory is shared by CPU/GPU | Show total system RAM once; no dedicated VRAM; don't penalize missing GPU memory | scoring fixture with unavailable VRAM |
| Free/cache/reclaimable memory differ from Windows | Use validated pressure semantics; do not carry Windows low-free threshold | controlled pressure-state native dataset and rules fixtures |
| GPU/temp/fan/power vary; private APIs and privilege used by peers | Initially unavailable; no NVML, root helper or private API in baseline | missing/denied/unsupported/zero fixtures; native matrix before enabling |
| APFS aliases/container sharing and mount duplication | Selected folder scans, stable volume identity, no symlink following by default | duplicate volume, symlink loop, permission, APFS native checks |
| Network/disk interface changes and counter resets | psutil counters keyed by device/interface; reject negative/reset rates | mocked add/remove/reset and native hotplug checks |
| Process exit/access restrictions | Isolate each psutil field, no elevation; revalidate identity before user-confirmed close | race/permission fixtures and native user tests |
| Login Items vs LaunchAgents/Daemons differ in scope | Initial read-only current-user subset; no system daemon mutation | parser fixtures, permission errors, native inspection |
| Sensor polling is slow and may log heavily | cache static info, bounded workers, rate-limit slow sensors | worker cancellation/shutdown and bounded-cadence tests |
| Gatekeeper trust and privileged helper attack surface | Signed/notarized public app; no privileged helper in MVP | codesign/spctl/stapler verification on Mac |

## Platform/version evidence

Qt 6.10 documents macOS 13+ for x86_64 and arm64. PySide6 6.11.2 publishes a universal2 macOS 13 wheel, while PySide6 6.12 wheel metadata says macOS 14+. Therefore minimum OS depends on pinned packaging dependencies. Current proposal is 14.0 to align with the current unconstrained PySide6 line; targeting 13 requires pinning a compatible release and testing the full frozen bundle.

Apple recommends notarizing Developer ID software for distribution outside the App Store; hardened runtime is required for notarization workflows. Sources: [Qt matrix](https://doc.qt.io/qt-6.10/macos.html), [PySide6 6.11.2](https://pypi.org/project/PySide6/6.11.2/), [PySide6 current wheel](https://pypi.org/project/PySide6/), [Developer ID](https://developer.apple.com/developer-id/), [notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution/), [distribution](https://developer.apple.com/documentation/technologyoverviews/distribution).

This is research, not a compatibility claim. No macOS hardware was available to test. LGPL/GPL projects were not incorporated; all source snapshots are for technical study only.
