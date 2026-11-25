# Windows installation

The Windows release is an x64 per-user installer. Download the latest `NEXUS-Setup-<version>-x64.exe` from the project's GitHub Releases page after publication.

1. Download the setup executable and the matching `SHA256SUMS.txt`.
2. Verify the SHA-256 hash with `Get-FileHash .\NEXUS-Setup-<version>-x64.exe -Algorithm SHA256`.
3. Open the installer. Read the welcome and MIT license pages.
4. Keep the default location (`%LOCALAPPDATA%\Programs\NEXUS`) or choose another writable directory.
5. Leave the desktop shortcut unchecked unless you want one.
6. Complete setup and use the final launch option if desired.

NEXUS creates a Start Menu shortcut named **NEXUS**. Press the Windows key, type `NEXUS`, and select the installed application. The shortcut targets the installed executable, not the development folder.

The current binaries are unsigned. Windows SmartScreen may show a warning for an unsigned pre-release; verify the source and checksum before deciding whether to continue. Do not disable Defender or other security protections.

Future installers use the same permanent AppId and installation location to upgrade the existing installation. User settings, history, logs, and reports remain under `%LOCALAPPDATA%\Nexus`. Uninstall from **Settings > Apps > Installed apps** or the generated uninstaller; data is preserved by default and removal is offered separately.

If setup fails, confirm that the downloaded file matches its checksum, close a running NEXUS instance, retry from a writable directory, and retain the installer log for a redacted support report.
