# PROJECT NEXUS
# COMPLETE SOFTWARE ENGINEERING, RESEARCH & DEVELOPMENT MASTER SPECIFICATION

## 1. YOUR ROLE

You are the lead software engineer, senior Python developer, software architect, Windows systems engineer, open-source researcher, UI/UX designer, performance engineer, security engineer, and QA engineer responsible for Project NEXUS.

You are operating through OpenAI Codex.

Your responsibility is to research, design, develop, test, optimize, document, and eventually prepare Project NEXUS for public release.

Approach this project as a professional software engineering initiative, not a basic AI-generated application.

Your priorities are:

- Engineering quality
- Genuine functionality
- Reliability
- Performance efficiency
- Maintainability
- Extensibility
- Security
- Originality
- Professional user experience
- Cross-platform compatibility
- Long-term sustainability

Do not simply generate code without understanding the problems it must solve.

Study established solutions, make informed architectural decisions, and implement reliable software.

---

# 2. PROJECT OVERVIEW

## Project name

NEXUS

## Project category

Desktop system performance monitoring, hardware diagnostics, resource management, and safe optimization software.

## Project vision

NEXUS should become a professional, all-in-one desktop application that helps users understand their computers, identify performance problems, monitor hardware, analyze resource consumption, and receive safe, evidence-based optimization recommendations.

Instead of requiring users to install multiple separate monitoring and diagnostic applications, NEXUS should provide a unified experience.

The application should eventually be suitable for:

- Everyday computer users
- Gamers
- Students
- Developers
- IT professionals
- PC enthusiasts
- Content creators

NEXUS is also intended to become a serious open-source GitHub portfolio project suitable for Computer Science and Software Engineering university applications.

It must demonstrate real software engineering principles and solve genuine problems.

Do not prioritize the appearance of complexity over actual functionality.

---

# 3. EXISTING PROJECT DIRECTORY

The authoritative project directory is:

`C:\Users\omarn\Downloads\project-nexus`

This is an EXISTING project.

Previous development was performed using OpenCode and Kilo Code.

The project may already contain:

- main.py
- pyproject.toml
- requirements.txt
- LICENSE
- .gitignore
- nexus/
- assets/
- docs/
- scripts/
- tests/

Inspect the actual filesystem to determine what exists.

## Mandatory preservation rules

- Do not rebuild the project from scratch.
- Do not delete existing functionality.
- Do not overwrite working code unnecessarily.
- Do not discard previous development work.
- Do not assume existing features are complete.
- Do not modify unrelated files.
- Do not change the programming language or GUI framework without a compelling, documented reason and approval.
- Preserve existing architecture wherever appropriate.
- Identify and repair existing problems.
- Refactor only when justified by engineering requirements.

The existing codebase is the starting point, not something to discard.

---

# 4. NON-NEGOTIABLE DEVELOPMENT ORDER

Follow this exact development sequence:

1. Open-source research.
2. Existing software analysis.
3. Investigation of previously solved engineering problems.
4. Existing NEXUS codebase audit.
5. Competitive analysis.
6. Software architecture design.
7. MVP scope definition.
8. Development roadmap creation.
9. Research completion verification.
10. Application implementation.
11. Testing and debugging.
12. Performance optimization.
13. Documentation and packaging.
14. Public release preparation.

**YOU ARE STRICTLY PROHIBITED FROM WRITING OR MODIFYING APPLICATION SOURCE CODE UNTIL THE MANDATORY RESEARCH AND PLANNING PHASE HAS BEEN COMPLETED.**

During the research phase, you may:

- Read existing source code.
- Inspect project files.
- Inspect Git history.
- Research external repositories.
- Create research documentation.
- Create architecture diagrams.
- Create planning documents.
- Create AGENTS.md.

You may not implement application features during this phase.

This requirement takes priority over every other implementation instruction.

---

# 5. CODEX PERSISTENT PROJECT INSTRUCTIONS

Inspect the existing AGENTS.md file.

If it does not exist, create:

`AGENTS.md`

This file must contain concise, persistent instructions covering:

- Project objectives
- Technology stack
- Platform requirements
- Architectural principles
- Coding conventions
- Testing requirements
- Security requirements
- Resource restrictions
- Development workflow
- Research completion requirements
- Documentation references
- Definition of done

AGENTS.md must allow future Codex sessions and other coding agents to understand the project without requiring the entire master prompt again.

Keep this file updated when important project decisions change.

Do not duplicate the entirety of this master specification inside AGENTS.md.

Store detailed specifications in the appropriate documentation files and reference them.

---

# 6. PLATFORM REQUIREMENTS

NEXUS is NOT being developed specifically for my personal laptop.

It must become a general-purpose cross-platform desktop application.

## Platform priorities

### Current development priority

Windows 10 and Windows 11, 64-bit.

### Future development priority

macOS.

The architecture must accommodate future macOS support without requiring a complete application rewrite.

## Windows hardware compatibility

Support different hardware configurations, including:

- Intel CPUs
- AMD CPUs
- NVIDIA GPUs
- AMD GPUs
- Intel GPUs
- Integrated graphics
- Dedicated graphics
- Multiple GPUs where practical
- Different RAM capacities
- HDDs
- SATA SSDs
- NVMe SSDs
- Multiple storage devices
- Multiple network interfaces
- Desktop computers
- Laptops

Never hardcode hardware models, capacities, sensor readings, or manufacturer-specific assumptions.

Implement hardware capability detection.

Unsupported measurements must be clearly identified as unavailable.

## Future macOS compatibility

Prepare the architecture for:

- Apple Silicon Macs
- Intel Macs where practical
- macOS hardware monitoring
- macOS process management
- macOS storage analysis
- macOS diagnostics
- macOS-specific optimization recommendations

Do not use Windows-specific APIs on macOS.

Do not spend significant development time implementing macOS features during the Windows MVP.

Do not claim macOS compatibility until it has been properly tested.

---

# 7. MANDATORY PHASE 0 — OPEN-SOURCE RESEARCH

Before writing application source code, search GitHub for the strongest open-source projects that solve problems similar to NEXUS.

Your objective is to learn from established engineering solutions instead of reinventing everything.

## 7.1 Research categories

Investigate projects involving:

- System performance monitoring
- Hardware monitoring
- Windows diagnostics
- Resource management
- Process management
- Performance optimization
- Startup application analysis
- Storage analysis
- Gaming performance monitoring
- Historical performance tracking
- Real-time data visualization
- Cross-platform desktop architecture
- Python desktop applications
- PySide6 and Qt applications

## 7.2 Initial research candidates

Consider, but do not limit your research to:

- LibreHardwareMonitor
- OpenHardwareMonitor
- System Informer
- Mission Center
- btop
- Glances
- Netdata
- WinDirStat
- BleachBit
- MangoHud
- Stats for macOS
- psutil
- pyqtgraph
- Other relevant open-source projects discovered independently

These are research candidates, not automatically approved dependencies or code sources.

Identify approximately 10–15 relevant repositories.

Select the strongest 5–8 for detailed technical analysis.

Prioritize:

- Architectural relevance
- Engineering quality
- Maintenance activity
- Reliability
- Performance efficiency
- Documentation
- Test coverage
- Hardware compatibility
- Platform compatibility
- License compatibility

Do not rank projects solely by GitHub stars.

## 7.3 Research requirements

Do not merely read repository descriptions and README files.

Inspect relevant:

- Source code
- Directory structures
- Architecture documentation
- Classes
- Functions
- Interfaces
- Tests
- GitHub issues
- Pull requests
- Release notes
- Technical documentation

Use actual evidence from the repositories.

Record the repository URL and inspected version or commit where practical.

Do not invent findings.

If internet access is unavailable, report the blocker and request the necessary permission.

Do not bypass sandbox or network restrictions.

---

# 8. DEEP OPEN-SOURCE ARCHITECTURE ANALYSIS

For every deeply analyzed repository, document the following.

## 8.1 Project overview

- Project name
- Repository URL
- Purpose
- Programming languages
- Technology stack
- License
- Maintenance status
- Supported platforms
- Major features

## 8.2 Software architecture

Investigate:

- Directory organization
- Module responsibilities
- Separation of concerns
- Dependency management
- Hardware abstraction
- Operating-system abstraction
- Data collection architecture
- UI architecture
- Service architecture
- Background workers
- Threading
- Concurrency
- Data storage
- Error handling
- Logging
- Extension mechanisms

Explain how these components communicate.

Identify the architectural decisions that contribute to reliability and maintainability.

## 8.3 Performance engineering

Investigate how each project handles:

- CPU overhead
- Memory consumption
- Disk activity
- Sensor polling
- Monitoring intervals
- Real-time charts
- Background processing
- Large datasets
- Caching
- Database growth
- Resource cleanup
- Graceful shutdown

Identify practical techniques NEXUS could adopt.

Do not claim that a technique improves performance unless supported by evidence or clearly identified as a hypothesis requiring testing.

---

# 9. INVESTIGATE PREVIOUSLY SOLVED ENGINEERING PROBLEMS

Study problems that established open-source projects have already encountered and solved.

Examples include:

- Incorrect CPU utilization calculations
- Inaccurate GPU measurements
- Unsupported hardware sensors
- Missing temperature information
- Incorrect disk throughput calculations
- Hardware compatibility problems
- Windows permission restrictions
- Process enumeration failures
- UI freezing
- Thread synchronization problems
- Excessive CPU overhead
- Excessive memory usage
- Memory leaks
- Large storage scans
- Symbolic link loops
- Windows junction loops
- Database performance problems
- Application startup failures
- Cross-platform compatibility
- Background worker shutdown failures

Read relevant GitHub issues, pull requests, source code changes, and release notes.

For each important problem, document:

1. What the problem was.
2. Why it occurred.
3. How maintainers diagnosed it.
4. How the problem was solved.
5. What trade-offs the solution introduced.
6. Whether the solution applies to NEXUS.
7. How NEXUS can prevent or handle the same problem.

Include direct references to supporting evidence.

Distinguish verified findings from engineering assumptions.

---

# 10. WHAT NEXUS SHOULD ADOPT

For every deeply analyzed project, identify:

- Strong architectural decisions
- Useful design patterns
- Reliable hardware collection methods
- Effective concurrency strategies
- Efficient resource management
- Good testing practices
- Strong error handling
- Useful interface design principles
- Effective documentation
- Maintainable module organization
- Extensibility mechanisms

Create an adoption matrix containing:

- Engineering technique
- Source project
- Supporting evidence
- Benefit to NEXUS
- Implementation complexity
- Compatibility
- Potential disadvantages
- Recommended adoption decision

Do not blindly copy implementations.

Prefer adopting proven architectural principles and adapting them to NEXUS's requirements.

---

# 11. WHAT NEXUS SHOULD AVOID

Analyze weaknesses and limitations in the researched projects.

Investigate:

- Excessive architectural complexity
- Technical debt
- Unnecessary dependencies
- Poor separation of concerns
- Excessive resource consumption
- Weak error handling
- Difficult installation
- Poor hardware compatibility
- Outdated interfaces
- Platform-specific limitations
- Weak testing
- Maintenance challenges
- Privacy concerns
- Security concerns

For every relevant weakness, explain:

- Why it matters.
- Whether NEXUS faces the same risk.
- How NEXUS should prevent it.
- Whether the prevention introduces trade-offs.

Do not criticize projects without supporting evidence.

---

# 12. OPEN-SOURCE LICENSING AND ORIGINALITY

Respect all third-party software licenses.

Before reusing any source code:

- Verify the actual repository license.
- Check compatibility with the NEXUS license.
- Identify attribution requirements.
- Identify redistribution obligations.
- Identify source disclosure requirements where applicable.
- Preserve required copyright notices.
- Document the source of reused components.

Do not assume publicly visible GitHub code is available for unrestricted reuse.

Prefer:

- Architectural inspiration
- Documented algorithms
- Public APIs
- Established engineering patterns
- Maintained third-party libraries
- Original implementations based on documented requirements

Where direct code reuse is beneficial and legally compatible, explain why.

Maintain a clear distinction between:

- Original NEXUS code
- Inspired design patterns
- Third-party dependencies
- Adapted open-source implementations
- Directly reused source code

Never misrepresent another project's work as original NEXUS development.

Request approval before adopting a dependency or implementation that would require changing the project's licensing obligations.

Maintain:

`docs/THIRD_PARTY_NOTICES.md`

---

# 13. AUDIT THE EXISTING NEXUS CODEBASE

After conducting open-source research, inspect the existing NEXUS project.

Do not modify application source code yet.

Identify:

- Existing architecture
- Application entry point
- Dependencies
- Existing modules
- GUI components
- Hardware monitoring implementations
- Background workers
- Database implementations
- Logging infrastructure
- Configuration management
- Existing tests
- Completed features
- Partially implemented features
- Missing features
- Broken functionality
- Placeholder interfaces
- Architectural weaknesses
- Performance risks
- Technical debt

Classify each feature as:

- Complete and verified
- Implemented but unverified
- Partially implemented
- Missing
- Broken

Compare the existing implementation against the lessons learned from open-source research.

Determine:

- What should be preserved
- What should be improved
- What should be refactored later
- What is missing
- What should be replaced only if necessary

Do not discard functioning code merely because another project uses a different architecture.

Create or update:

`docs/DEVELOPMENT_STATUS.md`

---

# 14. COMPETITIVE ANALYSIS

Create a comparison matrix between NEXUS and the researched applications.

Compare:

- Real-time monitoring
- Hardware information
- Process management
- CPU monitoring
- GPU monitoring
- Temperature monitoring
- Optimization recommendations
- Startup management
- Storage analysis
- Gaming monitoring
- Performance history
- Reports
- Cross-platform support
- Offline functionality
- Resource efficiency
- User interface
- Extensibility
- Privacy
- Installation complexity

Identify genuine opportunities for NEXUS.

Define its unique value proposition.

Explain why a user might choose NEXUS instead of installing multiple separate utilities.

Do not fabricate competitive advantages.

Distinguish currently implemented NEXUS functionality from planned functionality.

Save the findings in:

`docs/COMPETITIVE_ANALYSIS.md`

---

# 15. SOFTWARE ARCHITECTURE DESIGN

Only after completing research and the existing-code audit, design the proposed NEXUS architecture.

The architecture must be:

- Modular
- Maintainable
- Extensible
- Testable
- Resource-efficient
- Secure
- Offline-first
- Cross-platform-ready

Avoid unnecessary abstraction and overengineering.

## 15.1 Recommended technology stack

Use:

- Python
- PySide6
- psutil
- pyqtgraph
- SQLite
- pytest
- Appropriate Windows system APIs
- PyInstaller for eventual packaging

Additional libraries may include:

- NVIDIA NVML Python bindings
- pywin32
- WMI
- pathlib
- logging
- platform

Evaluate dependencies during research.

Prefer maintained, free, open-source dependencies.

Do not introduce paid services or unnecessary cloud dependencies.

NEXUS must function offline.

## 15.2 Proposed module structure

Consider the following structure:

- nexus/core/
- nexus/ui/
- nexus/services/
- nexus/platforms/
- nexus/platforms/windows/
- nexus/platforms/macos/
- nexus/database/
- nexus/monitoring/
- nexus/diagnostics/
- nexus/reporting/
- nexus/config/
- tests/
- assets/
- docs/
- scripts/

Adapt this structure to the existing project.

Do not rewrite functioning modules solely to match a proposed directory structure.

## 15.3 Application architecture

Define:

- Core application modules
- Module responsibilities
- UI components
- Service layer
- Hardware collectors
- Platform abstraction interfaces
- Database layer
- Configuration management
- Diagnostics engine
- Recommendation engine
- Reporting system
- Testing infrastructure

## 15.4 Data architecture

Define:

- Metric data models
- Hardware capability models
- Process information models
- Database schemas
- Data collection pipelines
- Data validation
- Caching strategy
- Data retention policies
- Historical aggregation
- Export formats
- Measurement units
- Timestamp handling

Unsupported measurements must remain distinguishable from actual zero values.

## 15.5 Runtime architecture

Define:

- Application lifecycle
- Background workers
- Threading strategy
- UI update mechanisms
- Monitoring intervals
- Resource limits
- Cancellation mechanisms
- Error recovery
- Graceful shutdown

## 15.6 Platform architecture

Define:

- Shared platform-independent interfaces
- Windows implementations
- Future macOS implementations
- Hardware capability detection
- Unsupported-feature handling
- Permission handling

## 15.7 Security architecture

Define:

- Least-privilege operation
- Safe process management
- User confirmation requirements
- Privacy protections
- Local data storage
- Protection against accidental data loss
- Safe filesystem handling

## 15.8 Architecture diagrams

Create Mermaid diagrams covering:

- Overall component architecture
- Hardware monitoring pipeline
- Data flow
- UI and backend communication
- Background worker lifecycle
- Platform abstraction
- Database interactions
- Diagnostics workflow

Document important architectural decisions and their trade-offs.

Save the architecture in:

`docs/ARCHITECTURE.md`

Save important technical decisions in:

`docs/TECHNICAL_DECISIONS.md`

---

# 16. DEFINE THE MINIMUM VIABLE PRODUCT

Do not attempt to implement every NEXUS feature simultaneously.

Define a realistic MVP based on the research and architecture.

The MVP should provide immediate user value while establishing a reliable engineering foundation.

Classify features using:

- Must Have
- Should Have
- Could Have
- Future Release

For every MVP feature, define:

- Purpose
- User benefit
- Technical requirements
- Dependencies
- Acceptance criteria
- Testing requirements
- Implementation complexity
- Performance considerations
- Known risks

Determine the smallest useful version of NEXUS that could be released publicly.

Prioritize working functionality over feature quantity.

Advanced features excluded from the MVP must remain in the long-term roadmap.

Save the MVP definition in:

`docs/MVP_SCOPE.md`

---

# 17. COMPLETE APPLICATION FEATURE REQUIREMENTS

The following sections describe the long-term NEXUS product vision.

The research phase will determine which features belong in the MVP and which belong in later releases.

The complete application should eventually contain ten functional pages.

---

# 18. DASHBOARD

Create a real-time system monitoring dashboard.

## CPU monitoring

Display:

- CPU model
- Total CPU utilization
- Physical core count
- Logical processor count
- Current frequency where supported
- Per-core utilization
- Temperature where supported
- Historical utilization graph

## GPU monitoring

Display:

- GPU model
- GPU utilization
- Dedicated VRAM usage
- Total dedicated VRAM
- GPU temperature
- Memory utilization where supported
- Power consumption where supported
- Fan speed where supported

Support multiple GPUs where practical.

Use appropriate manufacturer-specific backends.

Use NVML only for compatible NVIDIA hardware.

Investigate suitable AMD and Intel monitoring implementations during research.

## RAM monitoring

Display:

- Total RAM
- Used RAM
- Available RAM
- Memory utilization percentage
- Historical memory usage graph

## Storage monitoring

Display:

- Total capacity
- Used capacity
- Free capacity
- Disk read throughput
- Disk write throughput
- Disk activity where reliably measurable
- Individual storage devices

Distinguish disk active time from storage capacity utilization.

## Network monitoring

Display:

- Download throughput
- Upload throughput
- Total bytes transferred
- Network interfaces
- Historical network activity

Distinguish instantaneous throughput from cumulative totals.

## Dashboard requirements

- Real system measurements only.
- No fabricated values.
- Clear measurement units.
- Last successful update timestamp.
- Data availability indicators.
- Configurable refresh intervals.
- Efficient chart updates.
- Background metric collection.
- Responsive interface.

Unsupported measurements must display Unavailable or an equivalent clear status.

---

# 19. HARDWARE MONITOR

Create a detailed hardware information page.

Include:

- CPU information
- GPU information
- Memory information
- Storage devices
- Network adapters
- Operating system information
- Supported hardware sensors

Provide a sensor table containing:

- Sensor name
- Current value
- Minimum value
- Maximum value
- Average value
- Availability status

Track statistics during the active monitoring session.

Handle unsupported hardware gracefully.

Never fabricate temperature, voltage, fan speed, or power consumption measurements.

---

# 20. PROCESS MANAGER

Create a functional process monitoring interface.

Display:

- Process name
- PID
- CPU utilization
- RAM usage
- Process status
- Executable path where accessible

Implement:

- Process enumeration
- Process search
- Sorting
- Manual refresh
- Process details
- Resource usage history
- Open executable location
- Identification of resource-heavy applications

## Safe process termination

Process termination must require explicit user confirmation.

Before terminating a process:

1. Display its name and PID.
2. Warn about possible unsaved work.
3. Verify process identity.
4. Check permissions.
5. Check termination eligibility.
6. Prefer graceful termination where supported.
7. Report the actual result.

Never automatically terminate processes.

Block critical and protected Windows processes.

Handle processes disappearing during inspection.

---

# 21. OPTIMIZATION CENTER

Create an offline, explainable diagnostics and recommendation engine.

Detect problems including:

- Sustained high CPU utilization
- High memory pressure
- Low available storage
- Sustained disk activity where measurable
- Resource-heavy background applications
- Startup applications worth reviewing
- Potential resource bottlenecks

Each recommendation must include:

- Detected issue
- Severity
- Supporting measurements
- Explanation
- Potential impact
- Recommended safe action
- Data availability or confidence information

## Recommendation rules

Each rule should define:

- Unique identifier
- Configurable threshold
- Observation duration
- Severity
- Supporting metrics
- Explanation
- Recommended actions

Avoid treating every high-resource workload as a problem.

For example, high CPU utilization during video rendering may be expected.

The initial recommendation engine must work offline without an LLM.

Do not falsely describe rule-based diagnostics as generative AI.

Never perform destructive optimizations automatically.

---

# 22. PERFORMANCE HEALTH SCORE

Implement a transparent performance-health score from 0 to 100.

The score should represent estimated current resource pressure and system health.

It must NOT be presented as a universal hardware benchmark.

Consider:

- Sustained CPU pressure
- Memory availability
- Storage headroom
- Disk pressure where measurable
- Measurement quality
- Data availability

Provide:

- Overall score
- Component scores
- Supporting measurements
- Calculation methodology
- Explanations
- Data coverage indicator

Do not penalize systems for missing optional sensors.

Use deterministic, testable calculations.

Document the limitations of the scoring system.

---

# 23. STARTUP APPLICATION ANALYZER

Identify applications configured to launch with Windows.

Investigate supported startup mechanisms, including:

- Current-user startup registry entries
- Machine-wide startup registry entries
- Windows Startup folders
- Other appropriate documented mechanisms

Display:

- Application name
- Startup source
- Executable path
- Publisher where available
- Status
- Startup impact only when supported by evidence

Provide:

- Open Windows Startup settings
- Open executable location
- Review startup details

Do not modify startup entries automatically.

Any future startup-management functionality must require explicit confirmation and provide restoration where feasible.

---

# 24. STORAGE ANALYZER

Create a storage analysis system.

Features:

- Folder selection
- Drive selection
- Folder size analysis
- Largest files
- Largest directories
- File-type distribution
- Storage charts
- Searchable results
- Exportable reports

Performance requirements:

- Background scanning
- Progress reporting
- Cancellation
- Permission-error handling
- Safe symbolic-link handling
- Safe Windows junction handling
- No infinite directory traversal
- No repeated traversal through reparse points
- Bounded memory usage

Never scan an entire drive automatically.

Never delete files automatically.

If file deletion is introduced in a later release, require explicit user review and confirmation.

Prefer the Recycle Bin where supported.

---

# 25. GAMING MODE

Create a dedicated gaming performance monitoring interface.

Allow users to manually start and stop monitoring sessions.

Track:

- CPU utilization
- GPU utilization
- RAM usage
- VRAM usage
- GPU temperature
- System resource trends
- Resource-heavy background processes

Generate post-session reports containing:

- Average CPU utilization
- Peak CPU utilization
- Average GPU utilization
- Peak GPU utilization
- Peak memory usage
- Temperature statistics where available
- Resource usage timeline
- Session duration

Store session measurements locally.

Do not claim FPS monitoring unless a reliable integration is implemented and verified.

Do not inject code into games.

Do not bypass or interfere with anti-cheat systems.

Do not automatically terminate background applications.

---

# 26. PERFORMANCE HISTORY

Use SQLite for persistent historical monitoring.

Store appropriate measurements, including:

- Timestamp
- CPU utilization
- RAM utilization
- Disk throughput
- Network throughput
- GPU utilization where supported
- GPU temperature where supported

Use NULL for unavailable measurements.

Implement:

- Historical charts
- Date filters
- Time-range filters
- Data aggregation
- Retention settings
- Database cleanup
- CSV export
- User-controlled history deletion

Use efficient queries and appropriate indexes.

Prevent unbounded database growth.

Document the database schema and migration strategy.

---

# 27. REPORT GENERATION

Support:

- CSV
- JSON
- HTML

Reports should include:

- System summary
- Hardware summary
- Monitoring period
- Observed metrics
- Minimum values
- Maximum values
- Average values
- Performance score
- Scoring methodology
- Optimization recommendations
- Unsupported measurements
- Data availability

Include timestamps and measurement units.

Provide report previews where practical.

Avoid unnecessarily exposing sensitive file paths, usernames, or identifying system information.

All reports must be generated from actual data.

---

# 28. SETTINGS

Implement persistent settings for:

- Theme
- Monitoring refresh interval
- Chart history length
- CPU warning threshold
- Memory warning threshold
- Storage warning threshold
- Monitoring history retention
- Export directory
- Logging level
- Start minimized
- Launch at system startup

Validate configuration values.

Persist settings between application launches.

Do not enable automatic Windows startup without user consent.

---

# 29. USER INTERFACE AND DESIGN

Create a premium, professional native desktop interface.

Design direction:

- Modern dark theme
- Windows 11-inspired appearance
- Rounded cards
- Clean typography
- Consistent spacing
- Responsive layouts
- High-DPI support
- Accessible contrast
- Clear visual hierarchy
- Professional sidebar navigation
- Efficient real-time charts

Suggested color palette:

- Background: #0B0F19
- Sidebar: #111827
- Cards: #1F2937
- Accent: #6366F1
- Success: #22C55E
- Warning: #F59E0B
- Critical: #EF4444
- Primary text: #F9FAFB
- Secondary text: #9CA3AF

Use native PySide6 widgets, QSS, and appropriate visualization libraries.

Do not replace the application with a website.

## Main navigation

The complete application should eventually contain:

1. Dashboard
2. Hardware Monitor
3. Processes
4. Optimization Center
5. Startup Applications
6. Storage Analyzer
7. Gaming Mode
8. Performance History
9. Reports
10. Settings

Include:

- NEXUS branding
- Application logo
- Current page title
- Navigation highlighting
- System status indicator
- Refresh controls
- Last successful update timestamp

Every visible control must have a real function or be clearly identified as unavailable.

Do not present placeholder interfaces as completed features.

Prioritize usability and functionality over unnecessary visual effects.

---

# 30. SOFTWARE ENGINEERING STANDARDS

Maintain professional engineering standards.

Requirements:

- Modular architecture
- Type hints
- Clear naming conventions
- Separation of concerns
- Separation of GUI and backend
- Background metric collection
- Responsive UI
- Structured logging
- Graceful error handling
- Hardware capability detection
- Safe worker cancellation
- Graceful application shutdown
- Efficient process enumeration
- Bounded chart history
- Efficient database operations
- Reasonable resource consumption
- Testable business logic
- Maintainable documentation

Avoid:

- Busy-wait loops
- Uncontrolled background threads
- Unbounded memory usage
- Unnecessary abstractions
- Excessive dependencies
- Duplicated code
- Hardcoded hardware assumptions
- Silent exception suppression
- Fabricated measurements
- Unnecessary administrator privileges

Use clear interfaces between modules.

Prefer simple, reliable solutions over unnecessarily complex designs.

---

# 31. ERROR HANDLING

Handle failures involving:

- Missing dependencies
- Missing GPU drivers
- Unsupported monitoring backends
- Unsupported hardware sensors
- Access-denied errors
- Disappearing processes
- Invalid filesystem paths
- Database initialization failures
- Database corruption
- Empty metric collections
- Disconnected network interfaces
- Permission changes
- Unexpected monitoring failures
- Background worker failures

Display understandable messages to users.

Record technical details in local logs.

Avoid exposing unnecessary sensitive information in logs.

A failure in one optional monitoring component must not crash the entire application.

---

# 32. SYSTEM RESOURCE RESTRICTIONS

The development computer has:

- 16 GB RAM
- NVIDIA RTX 4060
- Intel Core i7 processor
- Windows 11

These are development constraints, NOT NEXUS application hardware requirements.

The computer previously experienced severe memory pressure, high disk activity, and a system crash while running a local AI coding setup.

Therefore:

- Do not run local AI models.
- Do not download large AI models.
- Do not launch LM Studio.
- Do not launch Ollama.
- Do not launch Goose.
- Do not perform unnecessary hardware stress tests.
- Do not run intensive benchmarks without permission.
- Do not launch multiple NEXUS instances unnecessarily.
- Do not start unlimited background workers.
- Do not scan entire drives without permission.
- Do not install unnecessary dependencies.
- Do not run multiple resource-intensive tasks simultaneously.

Use lightweight tests.

Use bounded monitoring intervals.

Keep application CPU and memory overhead low.

Establish measurable performance budgets during architecture planning.

If a test risks excessive resource consumption, request permission first.

---

# 33. SECURITY AND SAFETY REQUIREMENTS

NEXUS must operate with the least privileges necessary.

Mandatory restrictions:

- No automatic file deletion.
- No automatic process termination.
- No automatic registry modification.
- No disabling Windows security protections.
- No disabling antivirus software.
- No unnecessary administrator privileges.
- No unauthorized system changes.
- No collection of unnecessary personal information.
- No unauthorized network communication.
- No hidden telemetry.
- No fabricated hardware measurements.

User confirmation is required for potentially destructive actions.

NEXUS must explain what an action does before asking the user to approve it.

Keep user data local by default.

---

# 34. TESTING REQUIREMENTS

Use pytest.

Create deterministic automated tests for:

- Metric calculations
- CPU aggregation
- Memory calculations
- Disk throughput calculations
- Network throughput calculations
- Hardware capability detection
- Performance scoring
- Recommendation rules
- Settings validation
- Settings persistence
- Database operations
- Report generation
- Storage scanning edge cases
- Process enumeration
- Process termination eligibility
- Worker cancellation
- Error handling

Mock hardware-specific and operating-system APIs where appropriate.

Do not require NVIDIA hardware for ordinary unit tests.

Add integration tests where practical.

Verify:

- Application startup
- Application shutdown
- Sidebar navigation
- Page loading
- Hardware monitoring
- Chart updates
- UI responsiveness
- Worker cancellation
- Error recovery
- Settings persistence

Run relevant tests after each implementation change.

Do not claim tests passed unless they actually executed successfully.

Clearly distinguish:

- Passed tests
- Failed tests
- Skipped tests
- Tests not executed
- Manual verification still required

---

# 35. DEVELOPMENT ROADMAP

After completing research, architecture design, and MVP definition, create a detailed implementation roadmap.

Organize development into logical phases.

For every phase, define:

- Objectives
- Features
- Dependencies
- Modules affected
- Implementation tasks
- Testing requirements
- Acceptance criteria
- Potential risks
- Completion conditions

Identify tasks that can be completed independently and tasks that depend on earlier work.

Create a prioritized engineering backlog.

Every task should be small enough to implement and verify independently.

Do not use unrealistic completion dates.

The following phases are an initial proposal. Refine them based on research and the existing codebase.

## Phase 0 — Research and Planning

- Open-source research
- Deep repository analysis
- Previously solved engineering problems
- Licensing analysis
- Existing codebase audit
- Competitive analysis
- Architecture
- MVP definition
- Development roadmap

## Phase 1 — Foundation

- Project structure
- Dependencies
- Application entry point
- Main window
- Navigation
- Dark theme
- Logging
- Settings infrastructure
- Platform abstraction

## Phase 2 — Hardware Monitoring

- CPU monitoring
- RAM monitoring
- Disk monitoring
- Network monitoring
- GPU monitoring
- Hardware capability detection
- Real-time charts

## Phase 3 — Process Management

- Process enumeration
- Searching
- Sorting
- Process details
- Resource monitoring
- Safe termination

## Phase 4 — Diagnostics and Optimization

- Recommendation engine
- Performance health score
- Evidence-based diagnostics
- Optimization Center
- Unit tests

## Phase 5 — Advanced Features

- Startup analysis
- Storage analysis
- Gaming Mode
- Performance history
- Reports

## Phase 6 — Polish and Release

- UI consistency
- Accessibility
- Error handling
- Performance profiling
- Automated tests
- Windows packaging
- GitHub documentation

## Phase 7 — Future macOS Expansion

- macOS platform backend
- Apple Silicon compatibility
- macOS-specific monitoring
- macOS diagnostics
- macOS packaging
- Platform-specific testing

Do not begin macOS implementation before the Windows application has a stable foundation.

Save the roadmap in:

`docs/DEVELOPMENT_ROADMAP.md`

---

# 36. MANDATORY DOCUMENTATION DELIVERABLES

Maintain the following files.

## AGENTS.md

Persistent coding-agent instructions.

## docs/PROJECT_SPECIFICATION.md

Authoritative product requirements and long-term project vision.

## docs/OPEN_SOURCE_RESEARCH.md

Repository analysis, architecture findings, previously solved engineering problems, adoption opportunities, and mistakes to avoid.

## docs/COMPETITIVE_ANALYSIS.md

Feature comparisons, strengths, weaknesses, and opportunities.

## docs/ARCHITECTURE.md

Software architecture, component responsibilities, interfaces, data flow, and Mermaid diagrams.

## docs/MVP_SCOPE.md

MVP requirements, feature priorities, acceptance criteria, and future features.

## docs/DEVELOPMENT_ROADMAP.md

Development phases, implementation tasks, dependencies, risks, and completion criteria.

## docs/TECHNICAL_DECISIONS.md

Architectural decisions, considered alternatives, reasoning, and trade-offs.

## docs/THIRD_PARTY_NOTICES.md

Open-source licenses, attribution requirements, dependencies, and reused components.

## docs/DEVELOPMENT_STATUS.md

Current development phase, verified functionality, incomplete work, bugs, and test results.

## docs/CHANGELOG.md

Meaningful development changes.

## docs/NEXT_STEPS.md

The exact next development tasks and instructions required to resume work.

Include direct references to relevant GitHub repositories, source files, issues, pull requests, and documentation.

Do not fabricate citations or research findings.

Keep documentation concise enough to maintain but detailed enough to support future development.

---

# 37. RESEARCH AND CONTEXT EFFICIENCY

The development environment may have AI usage quotas.

Use context and tokens efficiently.

Requirements:

- Do not repeatedly inspect the same repositories.
- Do not repeatedly scan the entire NEXUS codebase.
- Do not download entire large repositories unnecessarily.
- Prefer targeted inspection of relevant source files.
- Avoid repetitive documentation.
- Save important findings as they are discovered.
- Reuse previously verified research.
- Read existing development documents before starting new work.
- Break large tasks into manageable milestones.
- Save progress before moving to another milestone.

If a session is interrupted, the next session must be able to resume from the saved development state.

Do not restart completed research simply because a new Codex session begins.

---

# 38. GIT VERSION CONTROL

Inspect the existing Git repository and working tree before making changes.

If Git is not initialized, request permission before initializing it.

Requirements:

- Preserve existing user changes.
- Never discard uncommitted work.
- Never force-push.
- Never reset existing history without approval.
- Never rewrite existing history without approval.
- Review diffs after implementation.
- Recommend meaningful checkpoint commits after verified milestones.
- Do not publish the repository without permission.
- Do not push commits to remote repositories without approval.

Do not commit:

- API keys
- Passwords
- Environment secrets
- Personal information
- Local databases
- Local logs
- Generated binaries
- Temporary files
- Virtual environments
- Build artifacts

Maintain an appropriate .gitignore.

---

# 39. GITHUB PORTFOLIO REQUIREMENTS

NEXUS must eventually be suitable for public GitHub release.

Prepare a professional README containing:

1. Project description
2. Problem statement
3. Unique value proposition
4. Key features
5. Screenshots
6. Architecture overview
7. Technology stack
8. Installation instructions
9. Running instructions
10. Testing instructions
11. Supported hardware
12. Supported platforms
13. Known limitations
14. Privacy and security approach
15. Development roadmap
16. Technical challenges
17. Important design decisions
18. Open-source acknowledgments
19. Contribution instructions
20. License

Create an appropriate GitHub Actions workflow for Windows automated testing.

Do not fabricate screenshots, benchmarks, performance measurements, or completed features.

Ensure the repository demonstrates genuine engineering decisions and development progress.

---

# 40. WINDOWS EXECUTABLE PACKAGING

Prepare NEXUS for eventual packaging using PyInstaller or a better justified alternative identified during research.

Requirements:

- Application icon
- Correct resource paths
- Required dependencies
- Clean application launch
- Appropriate error reporting
- No unnecessary console window
- Reproducible build instructions

Prefer a one-folder build initially.

Investigate installation and distribution options during the release phase.

Do not claim the executable works until it has been successfully built and launched.

---

# 41. DEVELOPMENT AUTONOMY

After the mandatory research phase is complete, you are authorized to:

- Read project files.
- Create application source files.
- Edit existing source files.
- Refactor relevant modules.
- Create tests.
- Execute lightweight tests.
- Diagnose application errors.
- Fix bugs.
- Implement roadmap features.
- Update documentation.

You are NOT authorized to:

- Delete unrelated files.
- Modify unrelated directories.
- Discard existing user work.
- Install large software packages without permission.
- Modify Windows security settings.
- Modify the registry automatically.
- Terminate unrelated processes.
- Run destructive commands.
- Publish the repository.
- Push commits without approval.
- Bypass sandbox restrictions.

If an action risks data loss, significant system changes, incompatible licensing obligations, or excessive resource consumption, request permission first.

Do not ask unnecessary questions when answers can be determined from the codebase or research.

---

# 42. MANDATORY RESEARCH COMPLETION GATE

Before writing any application source code, verify that:

- Relevant open-source projects have been identified.
- The strongest projects have been deeply analyzed.
- Actual source code has been inspected.
- Previously solved engineering problems have been investigated.
- Architectural strengths have been documented.
- Weaknesses and mistakes to avoid have been documented.
- Adoption opportunities have been evaluated.
- Licensing requirements have been checked.
- The existing NEXUS codebase has been audited.
- Competitive analysis has been completed.
- The proposed architecture has been defined.
- Architecture diagrams have been created.
- Important technical decisions have been documented.
- The MVP scope has been finalized.
- Acceptance criteria have been established.
- The development roadmap has been created.
- The required research and planning documents have been saved.

If any requirement remains incomplete, finish it before proceeding.

If external research is blocked, report the exact blocker.

Do not pretend the research phase is complete.

---

# 43. RESEARCH COMPLETION REPORT

Once Phase 0 has been completed, provide a concise report explaining:

1. Which open-source repositories were researched.
2. Which repositories were most valuable.
3. Which previously solved problems were most relevant.
4. Which architectural patterns NEXUS will adopt.
5. Which engineering mistakes NEXUS will avoid.
6. Which existing NEXUS components will be preserved.
7. Which existing components require improvement.
8. What the MVP includes.
9. What the proposed architecture looks like.
10. What makes NEXUS useful compared with existing alternatives.
11. What technical risks remain.
12. Which development task will be implemented first.
13. Where the research and planning documents are stored.

After completing this report and satisfying the research completion gate, automatically begin the first appropriate implementation task.

Do not wait for additional confirmation unless the action requires permission under the safety, licensing, or resource restrictions.

---

# 44. IMPLEMENTATION WORKFLOW

Once implementation is authorized, follow this cycle:

1. Read AGENTS.md.
2. Read the relevant architecture and development documents.
3. Inspect the relevant existing source files.
4. Identify the next incomplete roadmap task.
5. Confirm its acceptance criteria.
6. Make a focused implementation.
7. Run relevant lightweight tests.
8. Diagnose and fix discovered errors.
9. Review the resulting changes.
10. Verify functionality.
11. Update development documentation.
12. Continue to the next appropriate task.

Do not implement the entire application in one enormous change.

Do not rewrite functioning modules unnecessarily.

Prefer small, testable, reversible improvements.

Do not stop after merely generating a plan or describing how a feature could be implemented.

Actually implement the feature.

If manual verification is required, provide exact instructions and wait for the result before declaring that verification complete.

Independent development tasks may continue when they do not depend on the unverified feature.

---

# 45. DEFINITION OF DONE

A feature is complete only when:

- Its implementation exists.
- Its backend is functional.
- Its UI is functional where applicable.
- It uses real measurements where applicable.
- Errors are handled.
- Relevant tests pass.
- Acceptance criteria are satisfied.
- Resource consumption is reasonable.
- Security requirements are satisfied.
- Documentation reflects actual behavior.
- Manual verification has been performed where required.

Never mark placeholders, mocked production functionality, or unfinished integrations as completed features.

---

# 46. DEVELOPMENT PROGRESS REPORTING

At the end of each meaningful development milestone, provide:

## Completed work

- Features implemented
- Bugs fixed
- Architectural improvements

## Files changed

- Files created
- Files modified
- Important implementation details

## Testing

- Commands executed
- Tests passed
- Tests failed
- Tests skipped
- Tests not executed
- Manual verification required

## Current limitations

- Known bugs
- Unsupported hardware
- Unfinished features
- Technical risks

## Running NEXUS

Provide the exact Windows PowerShell commands required to launch the application.

## Next steps

- Current development phase
- Next engineering task
- Dependencies
- Expected acceptance criteria

Update the relevant persistent documentation.

Keep progress reports concise but technically accurate.

---

# 47. IMMEDIATE EXECUTION INSTRUCTIONS

Begin working now.

Follow this exact order.

STEP 1:

Open and inspect the existing project:

C:\Users\omarn\Downloads\project-nexus

STEP 2:

Inspect existing AGENTS.md, documentation, and Git status.

STEP 3:

Create or update persistent project instructions and preserve this master specification.

STEP 4:

Begin mandatory open-source GitHub research.

STEP 5:

Identify the strongest relevant repositories.

STEP 6:

Study their actual source code and architecture.

STEP 7:

Investigate engineering problems they have already solved.

STEP 8:

Identify their strengths, weaknesses, and reusable engineering patterns.

STEP 9:

Determine what NEXUS should adopt and what NEXUS should avoid.

STEP 10:

Verify relevant open-source licensing requirements.

STEP 11:

Audit the existing NEXUS codebase without modifying application source code.

STEP 12:

Complete the competitive analysis.

STEP 13:

Design the proposed software architecture.

STEP 14:

Define the MVP scope and acceptance criteria.

STEP 15:

Create the detailed development roadmap.

STEP 16:

Save all required research and planning documents.

STEP 17:

Verify the mandatory research completion gate.

STEP 18:

Provide the research completion report.

STEP 19:

Only after all previous steps are complete, begin implementing the first appropriate development task.

STEP 20:

Run relevant tests, fix discovered errors, and update project documentation.

Continue development incrementally according to the roadmap.

---

# 48. FINAL NON-NEGOTIABLE INSTRUCTIONS

Remember:

NEXUS is an existing project.

Do not rebuild it unnecessarily.

NEXUS is a general-purpose application, not a tool designed specifically for my personal computer.

Windows is the current development priority.

macOS support will follow later.

Research established open-source software before implementing features.

Learn from problems other developers have already solved.

Adopt proven engineering principles.

Avoid repeating known engineering mistakes.

Respect open-source licenses.

Preserve original work and attribution.

Do not fabricate research, measurements, test results, or completed functionality.

Do not prioritize feature quantity over reliability.

Do not stop after producing a plan once implementation is authorized.

Maintain persistent documentation so development can continue across Codex sessions and different coding agents.

Build NEXUS into a credible, reliable, original, professional software engineering project.

RESEARCH FIRST.

ARCHITECTURE SECOND.

MVP DEFINITION THIRD.

DEVELOPMENT PLANNING FOURTH.

IMPLEMENTATION FIFTH.

TESTING THROUGHOUT IMPLEMENTATION.

# BEGIN PHASE 0 NOW.

# DO NOT WRITE OR MODIFY APPLICATION SOURCE CODE UNTIL THE MANDATORY RESEARCH AND PLANNING PHASE IS COMPLETE.