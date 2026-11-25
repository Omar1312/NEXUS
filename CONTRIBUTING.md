# Contributing to NEXUS

NEXUS is a local-first PySide6 desktop monitor. Contributions should preserve the existing Windows interface and keep platform-specific code behind the platform boundaries.

## Development workflow

1. Create a branch from the current source.
2. Install Python 3.11 or newer and the dependencies in `requirements.txt`.
3. Read `AGENTS.md`, `docs/ARCHITECTURE.md`, and the relevant platform documentation.
4. Make a focused change with deterministic tests and honest capability reporting.
5. Run:

```powershell
python -m pytest -o addopts='' -q
python -m compileall -q nexus tests scripts
python -m pip check
```

6. Review the diff for secrets, personal paths, generated files, and unsupported claims.

## Pull requests

Describe the behavior changed, tests run, platforms verified, and known limitations. Do not include installers, databases, logs, screenshots containing personal data, virtual environments, or credentials. Native macOS claims require macOS runner or device evidence.

## Licensing

NEXUS is distributed under the MIT license. Review `docs/THIRD_PARTY_NOTICES.md` before changing dependencies or packaging.
