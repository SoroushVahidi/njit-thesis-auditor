# Run on native Windows x64 with Python 3.12 x64 installed.
# Builds a local one-folder candidate; this script does not distribute it.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot
try {
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw 'A native Windows x64 host is required.'
    }
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw 'Run this build on native Windows, not a compatibility layer.'
    }
    & py -3.12-64 -c 'import platform, struct; assert platform.system() == "Windows" and struct.calcsize("P") == 8'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 x64 is required.' }

    & py -3.12-64 -m venv .venv-build
    if ($LASTEXITCODE -ne 0) { throw 'Could not create build environment.' }
    $python = Join-Path $repoRoot '.venv-build\Scripts\python.exe'
    & $python -m pip install -c packaging/offline-build-constraints.txt -e . pyinstaller
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & $python -m PyInstaller --noconfirm --clean packaging/offline_desktop.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

    $exe = Join-Path $repoRoot 'dist\NJIT Thesis Auditor\NJIT Thesis Auditor.exe'
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Expected executable missing: $exe"
    }
    Get-FileHash -LiteralPath $exe -Algorithm SHA256
    Write-Host "Candidate folder: $(Split-Path -Parent $exe)"
    Write-Host 'Complete the native Windows smoke checklist before any distribution.'
}
finally {
    Pop-Location
}
