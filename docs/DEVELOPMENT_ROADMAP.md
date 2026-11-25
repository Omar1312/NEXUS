# Development roadmap

## Completed foundation

NEXUS-001 through NEXUS-008 are complete as documented in `docs/DEVELOPMENT_STATUS.md`. Packaging implementation is active; the installed UI and existing feature set were preserved.

## Prioritized tasks

| ID | Priority / status | Objective | Dependencies / relevant files | Acceptance criteria / tests |
|---|---|---|---|---|
| NEXUS-009 | P2 / deferred | Record lightweight repeatable resource observations | Existing app; monitoring, charts, database | Record observed startup, idle/active CPU, memory, UI/cadence, short DB growth and worker shutdown; no fabricated values or stress testing |
| NEXUS-010 | P1 / in progress | Build and validate Windows installer | NEXUS-001-009; `installer/NEXUS.iss`, `scripts/build_installer.ps1`, `scripts/build_release.ps1` | Compile with Inno Setup 6; install/launch/upgrade/reinstall/uninstall in disposable Windows environment; verify user data preserved by default and shortcuts work |
| NEXUS-011 | P1 / implemented, source unconfigured | Finish update release integration | `nexus/services/update_service.py`, Settings UI, build workflows | Owner chooses repository; controlled release validates stable/prerelease discovery, asset naming, SHA-256, cancellation, failure recovery, and safe installer handoff; no secrets in app |
| NEXUS-012 | P1 / pending | Complete manual Windows packaging verification | Packaged app and installer | Interactive UI/icon, clean-machine runtime, monitoring availability and shutdown verified; document machine/OS and results |
| NEXUS-013 | P1 / pending | Review redistribution readiness | `docs/THIRD_PARTY_NOTICES.md`, signing/release workflow | Review Qt and transitive licenses for chosen distribution; Authenticode signing decision and publisher verification documented |

## Packaging sequence

1. Obtain owner authorization to install the missing Inno Setup 6 prerequisite.
2. Compile the configured installer and run first-install/upgrade/reinstall/uninstall tests on a disposable Windows environment.
3. Complete manual UI/icon and hardware checks; keep tests bounded.
4. Configure and test a trusted release endpoint only after the owner chooses the repository.
5. Complete license and signing review before public distribution.
6. Resume NEXUS-009 lightweight performance observations and update status with measured values.

No release is published automatically. Do not configure an inferred GitHub repository or describe the update service as live until verified against a chosen release source.


## macOS expansion tasks

See `MACOS_ROADMAP.md` for objectives, implementation requirements, dependencies, acceptance criteria and tests for MAC-001 through MAC-017. Current status: MAC-001 helper foundation and MAC-002 path conventions implemented with tests; backend dispatch is not wired. Immediate next task is MAC-003. No native Mac support is claimed.
