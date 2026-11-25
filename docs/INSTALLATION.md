# Windows installation and uninstallation

Build the NEXUS setup executable with Inno Setup 6 or 7:

```powershell
.\scripts\build_installer.ps1
```

The wizard installs to `%LOCALAPPDATA%\Programs\NEXUS` by default, uses the NEXUS icon and project MIT license, creates a Start Menu shortcut named **NEXUS** in the NEXUS program group, offers an optional desktop shortcut, and has a final option to launch NEXUS. Installation is per-user and does not require administrator privileges. The standalone package includes the executable, runtime files, assets, and Qt Windows platform plugin; it does not require Python, PowerShell, the source tree, or a virtual environment.

After setup, press the Windows key and type **NEXUS**. Select the NEXUS Start Menu result to launch the installed copy. The shortcut points to the installed `NEXUS.exe`, not the development checkout.

The permanent Inno Setup AppId is `{A8F713A4-82E7-44C9-A5B7-44548D6511D0}`. Future installers using this AppId and previous install directory upgrade the existing per-user installation and reuse its Start Menu shortcut. The script reads the version from `nexus/__init__.py` and blocks lower semantic versions, including numeric prerelease downgrades.

Settings, SQLite performance and gaming history, logs, and default exports stay in `%LOCALAPPDATA%\Nexus`, separately from program files. Upgrade and uninstall preserve this data by default. The uninstaller is available through **Windows Settings > Apps > Installed apps** or its Start Menu entry and asks before removing NEXUS data. Custom export locations outside `%LOCALAPPDATA%\Nexus` are not removed.

## Current build status

The installer was compiled successfully with Inno Setup 7.1.1. The current output is `release\NEXUS-Setup-1.0.0-rc.1-x64.exe` (about 50 MB). The standalone package includes `NEXUS.exe`, the embedded NEXUS icon and update configuration, and `qwindows.dll`. The existing executable is currently running from `dist\NEXUS` and was left untouched. The recent isolated package was selected with:

```powershell
.\scripts\build_installer.ps1 -BuildDirectory work\windows-regression-dist\NEXUS
```

After compiling, install the setup executable and verify its shortcuts, installed launch, Installed Apps registration, upgrade behavior, and data preservation. Start Search behavior is not claimed as tested until the installer is installed and exercised.
