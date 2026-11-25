# Technical decisions

Status: proposed from codebase/research audit; revise only with implementation evidence.

## TD-001 Preserve Python + PySide6
Decision: retain the current stack and directory structure. Alternative: rewrite to another toolkit/language. Reason: substantial existing GUI, service, and domain implementation; rewrite would discard work without a demonstrated limitation. Trade-off: binary packaging size and Qt deployment/license review.

## TD-002 Use psutil for portable baseline metrics
Decision: retain psutil for common counters/processes, with platform backends for gaps. Evidence: mature cross-platform API and NEXUS existing dependency. Trade-off: permission and OS semantics vary; provide capability/unavailable status and tests.

## TD-003 Optional sensor backends
Decision: vendor/WMI/NVML collection remains optional and isolated. Evidence: LHM upstream issues/releases show driver and device variability. Trade-off: incomplete sensor coverage is unavoidable; don't make the app fail at startup when one backend is absent.

## TD-004 Threaded collection and bounded UI history
Decision: preserve worker-thread snapshot pattern and bounded graph buffers. Trade-off: added shutdown and signal lifecycle complexity; require cancellation/lifecycle tests.

## TD-005 SQLite local history
Decision: keep local SQLite and configurable retention; no cloud dependency. Trade-off: database initialization/corruption/migration paths need coverage and bounded retention.

## TD-006 Safe-by-default actions
Decision: monitoring/scanning are read-only; process termination and per-user startup registration require explicit confirmation. No automatic cleanup or performance tuning. Trade-off: fewer one-click “optimization” actions, with materially lower data-loss/system risk.

## TD-007 Windows first, macOS later
Decision: validate Windows 10/11 x64 first; define backend boundary now, do not claim macOS support until implemented and tested. Trade-off: some modules remain Windows-specific until extracted at a justified point.

## TD-008 Keep dependencies reviewable
Decision: no new dependency or source reuse until maintenance, platform fit, license and packaging impact are reviewed and recorded. Trade-off: some features arrive later.

## TD-009 Keep one shared app with explicit OS backends
Decision: preserve the existing Windows app and add an explicit platform selector and macOS backend. Shared UI, metric models, services, database, reports and charts stay shared. Rationale: current module structure already separates most responsibilities; a rewrite would increase regression risk. macOS code must not import Windows-only modules during selection. See `MACOS_ARCHITECTURE.md`.

## TD-010 Keep macOS telemetry least-privilege and capability-aware
Decision: use psutil baseline first; do not require root, privileged helpers, private IOReport/SMC APIs, or infer absent metrics. Apple Silicon unified memory is system RAM, not dedicated VRAM. Rationale: sensor availability and permission behavior differ by SoC and macOS release. Revisit optional sensor APIs only with a documented source, license/security review, and native tests.

## TD-011 Initial macOS floor follows current Qt wheel
Decision: propose macOS 14+ while PySide6 remains unconstrained on the current latest line. Qt 6.10/PySide6 6.11 support macOS 13; targeting 13 would require pinning and validating that stack. This is a proposed build target, not a verified compatibility claim.
