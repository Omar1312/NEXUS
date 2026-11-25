# Release process

Windows and macOS release builds are prepared by GitHub Actions. Ordinary CI builds and uploads artifacts only. The manually dispatched `Prepare and publish approved release` workflow builds both macOS architectures, requires successful signing/notarization, builds Windows, assembles one cross-platform SHA-256 manifest, and publishes only when its confirmation input is exactly `PUBLISH`. Configure a required reviewer for the `macos-release` environment before enabling public releases. This checkout has not been pushed and no workflow has been run.

1. Review source and docs in the project checkout.
2. Run `python -m pytest -o addopts='' -q`, `python -m compileall -q nexus tests scripts`, and `python -m pip check`.
3. Increment the single version in `nexus/__init__.py`, update the changelog and release notes, and verify tag `v<version>`.
4. Run `.github/workflows/macos-build.yml` and verify both unsigned development artifacts and runner logs; manually test on macOS 14.4+ ARM64 and Intel.
5. Configure all required Apple signing/notarization secrets and a required `macos-release` environment reviewer.
6. Dispatch `Prepare and publish approved release` with the matching existing version tag. Review all built artifacts before separately authorizing the publish job.
7. Publish only after explicit project-owner approval. Never commit tokens, certificates, or API keys.

## Local build commands

```powershell
scripts\build_windows.ps1
scripts\build_installer.ps1
scripts\build_release.ps1
```

```sh
bash scripts/build_macos.sh
bash scripts/build_dmg.sh
bash scripts/release_macos.sh  # requires Apple signing/notary secrets
```

The project still has no Windows Authenticode certificate. The Windows installer was compiled locally with Inno Setup 7.1.1, but clean-machine installation, Start Search, upgrade, and uninstall verification remain separate gates. Native Mac app/DMG and signing workflows have not run from this checkout.
