# macOS testing

This implementation was made on Windows. The macOS workflow is prepared but has not run from this checkout. Windows-hosted mock tests do not establish native compatibility.

## Required matrix

| Check | ARM64 Mac | Intel Mac |
|---|---|---|
| macOS version/model recorded | Pending | Pending |
| Install/launch from Applications and Retina/window behavior | Pending | Pending |
| CPU/memory/disk/network snapshot and data meaning | Pending | Pending |
| Process permission/race behavior | Pending | Pending |
| Pages, reports, history, settings, shutdown | Pending | Pending |
| DMG copy/eject and data-preserving upgrade/removal | Pending | Pending |
| Update discovery chooses correct architecture | Pending | Pending |
| codesign, Gatekeeper and notarization verification | Pending | Pending |

Test on macOS 14.4+ initially, record hardware/OS/app build, and keep tests bounded. Verify unsupported sensors display unavailable rather than zero. Do not require Full Disk Access or root. Never use an untrusted installer for testing.
