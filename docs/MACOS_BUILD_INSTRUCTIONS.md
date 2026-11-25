# macOS build instructions

The native application and DMG must be built on macOS. The project now contains `nexus_macos.spec`, `scripts/build_macos.sh`, `scripts/build_dmg.sh`, and `.github/workflows/macos-build.yml`. The workflow builds separate native ARM64 and Intel x64 artifacts on `macos-15` and `macos-15-intel` runners. A separate manually dispatched release workflow uses `scripts/release_macos.sh` to sign the app, notarize/staple the app and DMG, verify Gatekeeper assessments, then attach both DMGs with a combined SHA-256 manifest. That path fails closed unless the Apple secrets documented in `CODE_SIGNING.md` are set. It runs the full pytest suite, compileall and pip check before building and smoke-launching the `.app`, then uploads the DMG and SHA-256 file as a workflow artifact. It does not publish a GitHub Release.

## Local native build

On macOS 14.4 or later, Python 3.11+:

```sh
python3 -m pip install -e '.[dev,build]'
bash scripts/build_macos.sh
bash scripts/build_dmg.sh
```

The build is architecture-native and emits `release/NEXUS-<version>-macos-arm64.dmg` on Apple Silicon or `release/NEXUS-<version>-macos-x64.dmg` on Intel. The workflow matrix has one runner per architecture. Qt 6.12 documents macOS 14.4 as the minimum target; PySide6 is constrained to the 6.12 line in `pyproject.toml`. Verify installed wheel metadata and frozen app behavior in CI before treating 14.4 as a released support promise.

These are unsigned development builds. Public distribution still requires Developer ID signing, hardened runtime, notarization and stapling. Do not disable Gatekeeper to run them.

## Obtain artifacts from GitHub Actions

1. Add this project to a GitHub repository and push the branch containing `.github/workflows/macos-build.yml` (or open a pull request against `main`/`master`). No release is created by this workflow.
2. In the repository, open **Actions** and select **macOS tests and native installers**.
3. Open the completed run. Confirm both `macOS arm64 tests and DMG` and `macOS x64 tests and DMG` succeeded.
4. Download `NEXUS-macOS-arm64` or `NEXUS-macOS-x64` from the run?s **Artifacts** section. Each includes its architecture-specific DMG and SHA256SUMS file. Artifacts expire after 14 days.
5. Verify the downloaded file hash against its matching `SHA256SUMS-<arch>.txt`. The hash detects corruption; it does not authenticate NEXUS as publisher.

To run on demand, open **Actions ? macOS tests and native installers ? Run workflow**, select the branch, and start it. The same artifacts appear when it finishes. GitHub repository publication, pushing and creating releases have not been performed from this Windows checkout.
