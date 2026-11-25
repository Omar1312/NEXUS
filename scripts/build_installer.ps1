[CmdletBinding()]
param(
    [string]$BuildDirectory = 'dist/NEXUS',
    [string]$CompilerPath
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $ProjectRoot

# Resolve the packaged application before compiler discovery so a missing or
# incomplete build gets a direct, actionable message.
$BuildPath = if ([System.IO.Path]::IsPathRooted($BuildDirectory)) {
    $BuildDirectory
} else {
    Join-Path $ProjectRoot $BuildDirectory
}
if (-not (Test-Path -LiteralPath $BuildPath -PathType Container)) {
    throw "Packaged application directory is missing: $BuildPath. Run scripts/build_windows.ps1 first."
}
$BuildRoot = (Resolve-Path -LiteralPath $BuildPath).Path
$RequiredFiles = @(
    (Join-Path $BuildRoot 'NEXUS.exe'),
    (Join-Path $BuildRoot '_internal/assets/nexus.ico'),
    (Join-Path $BuildRoot '_internal/assets/update_config.json'),
    (Join-Path $BuildRoot '_internal/PySide6/plugins/platforms/qwindows.dll')
)
foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Packaged application is incomplete; required file is missing: $RequiredFile"
    }
    if ((Get-Item -LiteralPath $RequiredFile).Length -le 0) {
        throw "Packaged application contains an empty required file: $RequiredFile"
    }
}

function Find-InnoCompiler {
    param([string]$RequestedPath)

    $Candidates = [System.Collections.Generic.List[string]]::new()
    if ($RequestedPath) {
        $Candidates.Add($RequestedPath)
    } else {
        $OnPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($OnPath) { $Candidates.Add($OnPath.Source) }

        # Cover both 64-bit and 32-bit Program Files, per-user installs, and
        # both supported major versions. Inno Setup 7 commonly installs under
        # LocalAppData while Inno Setup 6 commonly uses Program Files (x86).
        $Roots = @(
            $env:ProgramFiles,
            ${env:ProgramFiles(x86)},
            $env:LOCALAPPDATA,
            $env:APPDATA
        ) | Where-Object { $_ } | Select-Object -Unique
        foreach ($Root in $Roots) {
            foreach ($Major in 7, 6) {
                $Candidates.Add((Join-Path $Root "Inno Setup $Major\ISCC.exe"))
            }
        }

        # Finally inspect the standard uninstall registry locations. This
        # handles custom install directories and per-user installations.
        $RegistryRoots = @(
            'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
        )
        foreach ($RegistryRoot in $RegistryRoots) {
            if (-not (Test-Path -LiteralPath $RegistryRoot)) { continue }
            Get-ChildItem -LiteralPath $RegistryRoot -ErrorAction SilentlyContinue | ForEach-Object {
                $Entry = Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
                if ($Entry.DisplayName -like 'Inno Setup 6*' -or $Entry.DisplayName -like 'Inno Setup 7*') {
                    if ($Entry.InstallLocation) {
                        $Candidates.Add((Join-Path ([Environment]::ExpandEnvironmentVariables([string]$Entry.InstallLocation.Trim('"'))) 'ISCC.exe'))
                    }
                    if ($Entry.UninstallString -match '^(?:"(?<path>[^"]+)|(?<path>\S+))') {
                        $Uninstaller = $Matches['path']
                        $Candidates.Add((Join-Path (Split-Path -Parent $Uninstaller) 'ISCC.exe'))
                    }
                }
            }
        }
    }

    foreach ($Candidate in $Candidates) {
        if (-not $Candidate) { continue }
        try {
            $Resolved = (Resolve-Path -LiteralPath $Candidate -ErrorAction Stop).Path
            if (Test-Path -LiteralPath $Resolved -PathType Leaf) { return $Resolved }
        } catch { }
    }
    return $null
}

$CompilerPath = Find-InnoCompiler -RequestedPath $CompilerPath
if (-not $CompilerPath) {
    throw 'Inno Setup 6 or 7 was not found. Install either supported version from the official page: https://jrsoftware.org/inno-setup/downloads'
}
$CompilerVersion = (Get-Item -LiteralPath $CompilerPath).VersionInfo.FileVersion
# ISCC.exe from Inno Setup 7 may carry a 0.0.0.0 Windows file version, so use
# the compiler's own version banner as the authoritative fallback.
if (-not $CompilerVersion -or $CompilerVersion -eq '0.0.0.0') {
    $VersionBanner = (& $CompilerPath --version 2>&1 | Out-String)
    if ($VersionBanner -match 'Inno Setup (?<major>\d+)') {
        $CompilerVersion = $Matches['major'] + '.0'
    } elseif ($VersionBanner -match '(?<version>\d+(?:\.\d+)+)') {
        $CompilerVersion = $Matches['version']
    }
}
if ($CompilerVersion -eq '0.0.0.0' -and $CompilerPath -match 'Inno Setup (?<major>6|7)') {
    $CompilerVersion = $Matches['major'] + '.0'
}
if (-not $CompilerVersion -or $CompilerVersion -notmatch '^(6|7)\.') {
    throw "Unsupported Inno Setup compiler version '$CompilerVersion' at $CompilerPath; expected major version 6 or 7."
}
Write-Host "Using Inno Setup compiler $CompilerVersion at $CompilerPath"

$Version = & python -c 'from nexus import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') {
    throw "Invalid application semantic version: $Version"
}
$Parts = $Version.Split('-')[0].Split('.')
$FileVersion = '{0}.{1}.{2}.0' -f $Parts[0], $Parts[1], $Parts[2]
$IncludePath = Join-Path $ProjectRoot 'installer/version.iss'
$HadInclude = Test-Path -LiteralPath $IncludePath -PathType Leaf
$PreviousInclude = if ($HadInclude) { Get-Content -LiteralPath $IncludePath -Raw } else { $null }
$OutputDirectory = Join-Path $ProjectRoot 'release'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

try {
    @(
        "#define NexusVersion `"$Version`"",
        "#define NexusFileVersion `"$FileVersion`"",
        "#define NexusBuildDir `"$BuildRoot`""
    ) | Set-Content -LiteralPath $IncludePath -Encoding ascii

    $ScriptPath = Join-Path $ProjectRoot 'installer/NEXUS.iss'
    & $CompilerPath $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compiler failed with exit code $LASTEXITCODE."
    }
} finally {
    if ($HadInclude) {
        Set-Content -LiteralPath $IncludePath -Value $PreviousInclude -Encoding ascii -NoNewline
    } else {
        Remove-Item -LiteralPath $IncludePath -Force -ErrorAction SilentlyContinue
    }
}

$Installer = Join-Path $OutputDirectory "NEXUS-Setup-$Version-x64.exe"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
    throw "Installer output was not generated: $Installer"
}
if ((Get-Item -LiteralPath $Installer).Length -le 0) {
    throw "Installer output is empty: $Installer"
}
Write-Host "Installer build succeeded: $Installer"
Write-Host "Install location: %LOCALAPPDATA%\Programs\NEXUS (per-user; no administrator rights required)"
