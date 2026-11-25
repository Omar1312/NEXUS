# NEXUS product specification

## Vision
NEXUS is a local-first desktop application for understanding a computer's live resource use, hardware capabilities, process activity, performance history, and safe diagnostic recommendations. It should provide a coherent overview without implying that it can read every sensor or safely automate system tuning.

## Product requirements
- Current priority: Windows 10/11 64-bit. Future macOS support must use separate platform backends and be explicitly tested before being advertised.
- Support varied CPU, GPU, RAM, storage, and network configurations by capability discovery; do not hardcode devices or fabricate unsupported readings.
- Operate offline, with local data by default, least privilege, no hidden telemetry, and no automatic file deletion, process termination, registry edits, or security changes.
- Keep the interface responsive; isolate collectors and scans from the UI, bound buffers/history, make long scans cancellable, and shut workers down cleanly.
- Explain recommendations with observed evidence and uncertainty. Separate advisory scores from direct hardware facts.

## Current codebase context
The existing Python/PySide6 project contains modules for monitoring, hardware collection, history, processes, storage scans, startup analysis, recommendations, reports, gaming sessions, settings, and a ten-page GUI. Presence of code is not proof of completion: see `DEVELOPMENT_STATUS.md`.

## Research and implementation gate
Before changing application source, complete the research, audit, architecture, MVP, and roadmap deliverables and verify all items in section 42 of the supplied Project NEXUS master specification. Keep detailed evidence in `OPEN_SOURCE_RESEARCH.md`. If an item is missing, continue research/planning rather than implement.

## Long-term feature direction
Real-time CPU/RAM/disk/network metrics; optional GPU/sensor readings with explicit availability; safe process inspection; explainable recommendations; user-initiated startup review; read-only cancellable storage analysis; optional performance history and export; future platform-specific backends. Advanced cleanup or automatic optimization is outside the safe default scope.
