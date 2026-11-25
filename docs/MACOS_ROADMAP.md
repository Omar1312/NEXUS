# macOS implementation roadmap

Implementation pass completed locally 2026-11-24. Native macOS build/runtime results remain pending GitHub Actions and physical-device checks.

| ID | Priority/status | Objective | Dependencies/files | Acceptance/tests |
|---|---|---|---|---|
| MAC-001 | P0 / implemented, native pending | Platform identification/backend selection | app, new `nexus/platforms`, collector coordinator | Identifier helpers and lazy collector dispatch wired; selector tests pass |
| MAC-002 | P0 / implemented, native pending | macOS user data/log/cache paths | `nexus/utils/paths.py`, logging/settings/db | Application Support/Logs/Caches rules and env overrides added; mocked path tests pass; native filesystem verification pending |
| MAC-003 | P0 / implemented, CI pending | Remove unconditional Windows imports from bootstrap/pages | app, core collectors, hardware, startup/settings integration | App/UI smoke path and import separation are prepared; verify on both native runners; Windows regression suite stays green |
| MAC-004 | P0 / implemented, native pending | psutil-based CPU/memory/disk/network collectors | new Mac backend, existing metrics | Real snapshot contract, explicit unavailable/reset/permission handling; mocks and native ARM64/Intel checks |
| MAC-005 | P0 / shared implementation + Mac protections, native pending | Process listing and safe actions | process service/core/UI | Race/permission safe; confirm + creation-time identity validation for close; mock/native tests |
| MAC-006 | P1 / implemented, native UI review pending | Adapt platform labels/actions/keyboard | dashboard, hardware, main window, sidebar, optimizer, settings | No Windows claims/actions on Mac; Windows appearance unchanged; Qt and native review |
| MAC-007 | P1 / platform-aware shared rules, native review pending | Platform-aware scoring/recommendations | scoring/recommendations/optimizer | Missing VRAM/fan/sensor does not penalize; tested evidence-based rules |
| MAC-008 | P1 / implemented read-only user LaunchAgents, native pending | Read-only macOS startup analyzer | startup analyzer/page, Mac module | Current-user subset only; parser/permission tests; no mutation |
| MAC-009 | P1 / shared scanner used, native APFS review pending | macOS-safe storage scan | storage scanner/page | Selected folder, no symlink loop/duplicate traversal/cloud fetch; mocked and APFS checks |
| MAC-010 | P1 / baseline decision implemented; sensors unavailable | Decide optional GPU/thermal/battery sources | research + hardware backend | Least-privilege default; no private API without explicit review; real model/OS validation |
| MAC-011 | P1 / implemented; dependency matrix CI pending | Platform metadata/dependencies | pyproject, requirements, notices | pywin32 win32-only, NVML Windows-only/optional; Qt floor pinned; dependency install on all targets |
| MAC-012 | P1 / script and spec implemented, native build pending | `.app` build | `scripts/build_macos.sh`, PyInstaller spec, ICNS | Native Mac build verifies Qt/plugins/assets and Finder launch; separate ARM64/x64 |
| MAC-013 | P1 / script implemented, native DMG pending | Branded DMG | `scripts/build_dmg.sh` | App + Applications alias + instructions; mount/copy/launch/eject verified |
| MAC-014 | P1 / implemented, release asset not yet published | OS/architecture-aware updates | update service/tests/release docs | Reject wrong platform asset; preserve repo-unconfigured state; hash/publisher verification |
| MAC-015 | P1 / implemented, workflow run pending | Cross-platform CI | GitHub Actions | Supported runner labels confirmed; pinned actions; least privilege; artifact upload only |
| MAC-016 | P1 / signing/notary script implemented, secrets and native run pending | Signing/notarization | signing docs/workflow | Developer ID, hardened runtime, notarize/staple, verify with codesign/spctl; secrets outside repo |
| MAC-017 | P1 / native runner and device review pending | Native release verification | macOS testing docs | macOS 14.4+ ARM64 and Intel feature/install/update checklist; exact devices/OS recorded |

## Order and gates

Local implementation is in place through the packaging and workflow tasks. Remaining gates are a successful ARM64/Intel macOS workflow run, native GUI/install/update review, and Developer ID signing/notarization credentials for public distribution. Optional GPU utilization, thermals, fan and memory pressure stay unavailable until supported sources are validated. No publication has occurred.
