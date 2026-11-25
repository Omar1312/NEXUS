[CmdletBinding()]
param(
    [string]$ReleaseRepository = $env:NEXUS_RELEASE_REPOSITORY
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $ProjectRoot

& (Join-Path $PSScriptRoot 'build_windows.ps1') -ReleaseRepository $ReleaseRepository
if ($LASTEXITCODE -ne 0) { throw "Windows executable build failed with exit code $LASTEXITCODE." }
& (Join-Path $PSScriptRoot 'build_installer.ps1')
if ($LASTEXITCODE -ne 0) { throw "Installer build failed with exit code $LASTEXITCODE." }

$Version = & python -c 'from nexus import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Could not read the NEXUS version.' }
$Exe = Join-Path $ProjectRoot 'dist/NEXUS/NEXUS.exe'
$Setup = Join-Path $ProjectRoot "release/NEXUS-Setup-$Version-x64.exe"
foreach ($Artifact in @($Exe, $Setup)) {
    if (-not (Test-Path -LiteralPath $Artifact -PathType Leaf)) { throw "Required artifact is missing: $Artifact" }
    if ((Get-Item -LiteralPath $Artifact).Length -le 0) { throw "Artifact is empty: $Artifact" }
}
$Output = Join-Path $ProjectRoot 'release'
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$Hash = (Get-FileHash -LiteralPath $Setup -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $(Split-Path -Leaf $Setup)" | Set-Content -LiteralPath (Join-Path $Output 'SHA256SUMS.txt') -Encoding ascii
$Notes = Join-Path $ProjectRoot 'docs/RELEASE_NOTES.md'
if (-not (Test-Path -LiteralPath $Notes -PathType Leaf)) {
    throw "Create $Notes with the release notes before preparing a release."
}
Copy-Item -LiteralPath $Notes -Destination (Join-Path $Output 'RELEASE_NOTES.md') -Force
$Summary = @"
NEXUS $Version release artifacts prepared locally.
Installer: $Setup
SHA-256: $Hash
Executable folder: $(Split-Path $Exe)
This script does not publish or upload artifacts.
"@
$Summary | Set-Content -LiteralPath (Join-Path $Output 'BUILD_SUMMARY.txt') -Encoding utf8
Write-Host "Release artifacts prepared in $Output"
Write-Host "Installer: $Setup"
Write-Host "SHA256: $Hash"
