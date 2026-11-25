# Security policy

## Supported versions

NEXUS is currently a pre-release (`1.0.0-rc.1`). Security fixes are handled on the current working version until a stable support policy is published.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. After the project repository is created, use its private security advisory flow. Until then, contact the project owner through the private channel associated with the repository. Do not include credentials, private logs, database files, or personal diagnostics in a report.

Please include the affected version, operating system and architecture, reproduction steps, impact, and a minimal redacted proof of concept.

## Security design

NEXUS is offline-first and collects data locally. Update checks are optional, downloaded installers are checksum-verified, and updates require user approval. Process termination requires explicit confirmation and revalidates process identity. Startup inspection is read-only on macOS; Windows startup registration is opt-in. NEXUS does not request administrator privileges for the normal per-user installation.

The checksum manifest detects corruption but does not authenticate the publisher. Release binaries should be signed and notarized or Authenticode-signed before general distribution.
