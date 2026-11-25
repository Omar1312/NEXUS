[CmdletBinding()]
param(
    [switch]$SkipTests,
    [string]$ReleaseRepository = $env:NEXUS_RELEASE_REPOSITORY
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $ProjectRoot
$env:PYTHONPATH = $ProjectRoot

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $Program $($Arguments -join ' ')"
    }
}

if ($env:OS -ne 'Windows_NT') { throw 'This packaging script must run on Windows.' }
if ([IntPtr]::Size -ne 8) { throw 'A 64-bit Python interpreter is required.' }
$Python = (Get-Command python -ErrorAction Stop).Source
$PythonVersion = & $Python -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))"
if ($LASTEXITCODE -ne 0 -or [version]$PythonVersion -lt [version]'3.11') {
    throw "Python 3.11 or newer is required; found $PythonVersion."
}

$Required = @('PySide6', 'psutil', 'pyqtgraph', 'numpy', 'packaging', 'PyInstaller', 'pynvml', 'win32com.client')
foreach ($Module in $Required) {
    & $Python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$Module') else 1)"
    if ($LASTEXITCODE -ne 0) { throw "Required build dependency '$Module' is unavailable in $Python." }
}
Invoke-Checked $Python @('-m', 'pip', 'check')
$Version = & $Python -c 'from nexus import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') {
    throw "Invalid application semantic version: $Version"
}
Write-Host "Building NEXUS $Version with $Python"
if (-not $SkipTests) { Invoke-Checked $Python @('-m', 'pytest', '-q') }
Invoke-Checked $Python @('-m', 'compileall', '-q', 'nexus')
Invoke-Checked $Python @('scripts/write_version_info.py')
$env:NEXUS_VERSION_INFO = Join-Path $ProjectRoot 'work/nexus_version_info.txt'
if ($ReleaseRepository) {
    if ($ReleaseRepository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
        throw 'ReleaseRepository must use owner/repository format.'
    }
    @{ repository = $ReleaseRepository } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ProjectRoot 'work/update_config.json') -Encoding ascii
    $env:NEXUS_UPDATE_CONFIG_FILE = Join-Path $ProjectRoot 'work/update_config.json'
} else {
    $env:NEXUS_UPDATE_CONFIG_FILE = Join-Path $ProjectRoot 'assets/update_config.json'
}
Invoke-Checked $Python @('-m', 'PyInstaller', '--clean', '--noconfirm', 'nexus.spec')
Invoke-Checked $Python @('scripts/collect_licenses.py')
$Exe = Join-Path $ProjectRoot 'dist/NEXUS/NEXUS.exe'
if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Expected executable was not created: $Exe" }
$Icon = Join-Path $ProjectRoot 'dist/NEXUS/_internal/assets/nexus.ico'
if (-not (Test-Path -LiteralPath $Icon -PathType Leaf)) { throw "Expected bundled icon was not created: $Icon" }
$UpdateConfig = Join-Path $ProjectRoot 'dist/NEXUS/_internal/assets/update_config.json'
if (-not (Test-Path -LiteralPath $UpdateConfig -PathType Leaf)) { throw "Expected update configuration was not bundled: $UpdateConfig" }
$OldQpa = $env:QT_QPA_PLATFORM
$OldDataDir = $env:NEXUS_DATA_DIR
$env:QT_QPA_PLATFORM = 'offscreen'
$env:NEXUS_DATA_DIR = Join-Path $ProjectRoot ("work/packaged-smoke-" + [guid]::NewGuid().ToString('N'))
try {
    $SmokeProcess = Start-Process -FilePath $Exe -ArgumentList @('--no-wmi-sensors', '--smoke-test') -PassThru -WindowStyle Hidden
    if (-not $SmokeProcess.WaitForExit(20000)) {
        Stop-Process -Id $SmokeProcess.Id -Force
        throw 'Packaged application did not complete its bounded startup/shutdown smoke test within 20 seconds.'
    }
    if ($SmokeProcess.ExitCode -ne 0) { throw "Packaged smoke test exited with code $($SmokeProcess.ExitCode)." }
    $SmokeLog = Join-Path $env:NEXUS_DATA_DIR 'logs/nexus.log'
    if (-not (Test-Path -LiteralPath $SmokeLog -PathType Leaf)) { throw 'Packaged smoke test did not write a diagnostic log.' }
    if (-not (Select-String -LiteralPath $SmokeLog -Pattern 'NEXUS stopped \(clean=True\)' -Quiet)) {
        throw "Packaged smoke test did not log clean shutdown. Inspect $SmokeLog"
    }
} finally {
    $env:QT_QPA_PLATFORM = $OldQpa
    $env:NEXUS_DATA_DIR = $OldDataDir
}
Write-Host "Build succeeded: $Exe"
Write-Host "Output directory: $(Split-Path $Exe)"
