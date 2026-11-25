# NEXUS contributor instructions

## Objective and platform
Maintain NEXUS as a local-first desktop monitor and diagnostic tool. Windows 10/11 x64 is the implemented target; macOS is in research/foundation development and must not be advertised as supported before native verification. Keep platform-specific code behind `nexus/platforms` and `nexus/hardware`. The stack is Python 3.11+, PySide6, psutil, pyqtgraph, SQLite, pytest, plus conditional OS dependencies.

## Engineering principles
- Preserve existing behavior and user work; make focused, reversible changes.
- Keep UI, services, metric models, persistence, and platform collection separate.
- Treat unsupported metrics as unavailable (`None`/capability state), never as zero.
- Keep the app offline-first and least-privilege. No telemetry or automatic destructive system actions.
- User confirmation is required before process termination or persistent startup changes.
- Bound chart/history memory, scan work, thread count, and polling frequency. Keep long work off the UI thread and make cancellation/shutdown reliable.
- Catch expected platform errors at boundaries, log diagnostic details locally, and keep optional collectors from taking down the app.
- Check licenses before adding dependencies or reusing code; retain attribution and record dependencies in `docs/THIRD_PARTY_NOTICES.md`.

## Workflow
1. Read this file and relevant docs, then inspect the existing implementation and Git status. A local Git repository was initialized on 2026-11-24 at the user's explicit request. Do not create a remote or push without approval.
2. Keep research/planning separate from implementation whenever the research gate in `docs/PROJECT_SPECIFICATION.md` is active. Do not modify app source until all Phase 0 documents and the gate are complete.
3. Implement one roadmap task at a time. Add deterministic pytest coverage and use mocks for hardware APIs. Run relevant lightweight tests after changes; report tests not run distinctly.
4. Review diffs and update status, changelog, and next steps. Never publish or push without approval.

## Conventions and quality
Use type hints, clear names, Ruff conventions (100-column target), focused modules, structured logging, and understandable UI errors. Avoid busy waits, unbounded work, silent broad exception swallowing, fabricated readings, unnecessary dependencies, and administrator requirements. Definition of done includes real behavior, error handling, acceptance criteria, tests, reasonable resource use, updated docs, and manual verification where needed.

## Persistent references
Product requirements: `docs/PROJECT_SPECIFICATION.md`; research: `docs/OPEN_SOURCE_RESEARCH.md`; architecture: `docs/ARCHITECTURE.md`; MVP: `docs/MVP_SCOPE.md`; roadmap: `docs/DEVELOPMENT_ROADMAP.md`; decisions: `docs/TECHNICAL_DECISIONS.md`; current audit: `docs/DEVELOPMENT_STATUS.md`; competitor review: `docs/COMPETITIVE_ANALYSIS.md`; third-party inventory: `docs/THIRD_PARTY_NOTICES.md`; resume point: `docs/NEXT_STEPS.md`.

macOS research: `docs/MACOS_RESEARCH.md`; architecture: `docs/MACOS_ARCHITECTURE.md`; matrix: `docs/PLATFORM_COMPATIBILITY.md`; roadmap: `docs/MACOS_ROADMAP.md`; native verification checklist: `docs/MACOS_TESTING.md`; signing: `docs/CODE_SIGNING.md`.
