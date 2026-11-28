param(
    [string]$Python = 'python',
    [string]$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
function Check-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)" }
}
Push-Location $repoRoot
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
        $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'Native Windows x64 required.' }
    & $Python -c "import sys, struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8"
    Check-Exit 'Python 3.12 x64 validation'
    if (git status --porcelain) { throw 'Build from a clean committed checkout.' }
    if (-not (Test-Path -LiteralPath $Iscc)) { throw 'Inno Setup 6 ISCC.exe is required on the builder.' }
    if (Test-Path -LiteralPath '.venv-build') { throw 'Use a fresh build checkout.' }
    & $Python -m venv .venv-build
    Check-Exit 'Build environment'
    $builder = Join-Path $repoRoot '.venv-build\Scripts\python.exe'
    & $builder -m pip install -c packaging/offline-build-constraints.txt -e . pyinstaller
    Check-Exit 'Pinned dependencies'
    & $builder -m PyInstaller --noconfirm --clean packaging/offline_desktop.spec
    Check-Exit 'Windows application build'
    $bundle = Join-Path $repoRoot 'dist\NJIT Thesis Auditor'
    if (-not (Test-Path -LiteralPath "$bundle\NJIT Thesis Auditor.exe")) { throw 'Missing application.' }
    $buildInfo = Get-Content -LiteralPath (Join-Path $bundle '_internal\desktop-build-info.json') -Raw | ConvertFrom-Json
    $version = $buildInfo.build_version
    if ($buildInfo.commit -ne (git rev-parse HEAD) -or $version -notmatch '\+g[0-9a-f]{12}$') {
        throw 'Bundle provenance does not match the Windows candidate checkout.'
    }
    Check-Exit 'Version lookup'
    $fileVersion = & $builder -c "from njit_auditor.desktop_metadata import FILE_VERSION; print('.'.join(map(str, FILE_VERSION)))"
    Check-Exit 'Numeric version lookup'
    & $builder scripts/verify_windows_bundle.py $bundle
    Check-Exit 'Complete NJIT bundle validation'
    $output = Join-Path $repoRoot 'dist\installers'
    & $Iscc "/DAppVersion=$version" "/DFileVersion=$fileVersion" "/DBundleDir=$bundle" "/DOutputDir=$output" packaging/windows_installer.iss
    Check-Exit 'Graphical installer build'
    & $builder scripts/windows_release_metadata.py --installer "$output\NJIT-Thesis-Auditor-Setup-$version.exe" --bundle "$bundle"
    Check-Exit 'Installer metadata'
    Write-Host "Candidate installer: $output\NJIT-Thesis-Auditor-Setup-$version.exe"
    Write-Host 'New beta build. Publish with the actual smoke-test results and testing limits.'
}
finally { Pop-Location }
