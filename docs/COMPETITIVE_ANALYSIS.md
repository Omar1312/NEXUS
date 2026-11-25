# Competitive analysis

This matrix compares product focus based on upstream project descriptions and targeted repository review. It does not represent exhaustive hands-on testing. NEXUS entries are code-presence observations only; verification is pending as documented in `DEVELOPMENT_STATUS.md`.

| Capability | NEXUS (current code present) | LHM | System Informer | Glances | WinDirStat | MangoHud | Stats (macOS) |
|---|---|---|---|---|---|---|---|
| Live CPU/RAM/disk/network | Yes, collectors/UI | Partial focus | Yes | Yes | No | Overlay subset | Yes |
| Hardware sensors / GPU | Optional Windows collectors | Strong sensor focus | Hardware/process focus | Plugin/API dependent | No | Gaming overlay metrics | Mac sensors |
| Process management | Listing and confirmed graceful termination code | Limited | Strong | Yes, monitor focus | No | No | No |
| Recommendations / health score | Code present; unverified | No | No | Alert/threshold focus | No | No | No |
| Startup analysis | Code present; unverified | No | Windows tools | Plugin dependent | No | No | Login items context |
| Storage analysis | Read-only scanner code | No | Some system insight | Disk metrics | Core strength | No | No |
| Gaming monitoring | Session code present | Sensor focus | Process focus | General | No | Core overlay use | No |
| History/reports | SQLite/history/report code | Sensor logging options | Diagnostics | Export/server options | Scan results | Overlay/logging | Menu bar views |
| Cross-platform | Windows focused; non-Windows warning only | Windows-first | Windows | Linux/macOS/Windows | Windows | Primarily Linux | macOS |
| Offline/local | Intended and code suggests local | Yes | Yes | Local/remote modes | Yes | Yes | Yes |
| Install complexity | Python stack currently | Utility/library | Windows app | Python/package options | Windows app | Linux setup | macOS app |

## Positioning
NEXUS's credible opportunity is a single Windows desktop workflow connecting live overview, optional hardware capability reporting, process inspection, read-only storage exploration, locally retained history, and explanations of suggestions. It cannot claim superior measurements, lower resource use, or more complete coverage until validated against representative systems and alternatives. The differentiator should be transparency: source/capability status, unavailable metrics, measured evidence, and user-controlled actions in one interface.

## Why use NEXUS
Potentially fewer separate windows for routine monitoring and diagnostics, with local history and explainable advisory output. The breadth is visible in code but not yet verified; the MVP should narrow scope to metrics, capability status, safe process inspection, and a small tested recommendation set.

## Gaps and threats
Established tools have deeper hardware support (LHM), stronger process/system inspection (System Informer), mature focused storage visualization (WinDirStat), or specialized in-game overlays (MangoHud). NEXUS should complement these rather than claim to replace every specialist tool. Current repository lacks public-facing README/docs and broad tests; tests cover formatting only.
