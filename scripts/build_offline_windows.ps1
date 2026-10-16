# Build and run an unauthenticated socket smoke test on native Windows x64.
# Run from PowerShell on Windows with Python 3.12 x64 installed for the builder.
param([switch]$KeepBuildEnvironment)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo
$dirty = @(git status --porcelain=v1)
if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) {
    throw 'Commit all source changes before the Windows build so its SHA is reproducible.'
}
$notes = Join-Path $env:TEMP "njit-offline-windows-smoke-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Force -Path $notes | Out-Null
$venv = Join-Path $notes 'venv'
$python = Join-Path $venv 'Scripts\python.exe'
$pyinstaller = Join-Path $venv 'Scripts\pyinstaller.exe'
$profile = Join-Path $notes 'profile'
$stdout = Join-Path $notes 'launcher.stdout.txt'
$stderr = Join-Path $notes 'launcher.stderr.txt'
$result = Join-Path $notes 'result.txt'
$exe = Join-Path $repo 'dist\NJIT Thesis Auditor\NJIT Thesis Auditor.exe'
$process = $null
$oldLocalAppData = $env:LOCALAPPDATA

try {
    if (-not (Test-Path $python)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.12-64 -m venv $venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv $venv
        } else {
            throw 'Python 3.12 x64 is required for this native build.'
        }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python build environment.' }
    }
    & $python -c "import struct,sys; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8"
    if ($LASTEXITCODE -ne 0) { throw 'The build environment must use Python 3.12 x64.' }
    & $python -m pip install -c packaging/offline-build-constraints.txt -e . pyinstaller
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & $pyinstaller --noconfirm --clean packaging/offline_desktop.spec
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) { throw 'PyInstaller build failed.' }

    $expected = @(
        'src\njit_auditor\offline_templates\index.html',
        'src\njit_auditor\templates\_macros.html',
        'src\njit_auditor\templates\base.html',
        'src\njit_auditor\templates\help.html',
        'src\njit_auditor\templates\job.html',
        'src\njit_auditor\templates\problem_group.html',
        'src\njit_auditor\templates\rules.html',
        'data\processed\rules\project_added_rules.json',
        'data\specs\ester_warning_wording_map.json',
        'assets\fonts\DejaVuSans.ttf',
        'assets\fonts\DejaVu-LICENSE.txt'
    )
    $internal = Join-Path (Split-Path $exe) '_internal'
    foreach ($relative in $expected) {
        if (-not (Test-Path (Join-Path $internal $relative))) {
            throw "Missing packaged resource: $relative"
        }
    }
    $projectRoots = @(
        (Join-Path $internal 'src\njit_auditor'),
        (Join-Path $internal 'data'),
        (Join-Path $internal 'assets')
    )
    $projectFiles = Get-ChildItem -Path $projectRoots -Recurse -File |
        ForEach-Object { $_.FullName.Substring($internal.Length + 1) }
    $extra = @($projectFiles | Where-Object { $expected -notcontains $_ })
    if ($extra.Count -gt 0) { throw "Unexpected project resource(s): $($extra -join ', ')" }
    & $python scripts/inspect_offline_bundle.py (Split-Path $exe)
    if ($LASTEXITCODE -ne 0) { throw 'Whole-bundle privacy/resource inspection failed.' }

    New-Item -ItemType Directory -Force -Path $profile | Out-Null
    $env:LOCALAPPDATA = $profile
    $process = Start-Process -FilePath $exe -ArgumentList '--headless', '--no-browser' `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    $listener = $null
    for ($i = 0; $i -lt 100; $i++) {
        if ($process.HasExited) { throw "Launcher exited early with code $($process.ExitCode)." }
        $listener = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -eq $process.Id }
        if ($listener) { break }
        Start-Sleep -Milliseconds 100
    }
    if (-not $listener) { throw 'No listening socket appeared.' }
    $addresses = @($listener | Select-Object -ExpandProperty LocalAddress -Unique)
    if ($addresses.Count -ne 1 -or $addresses[0] -ne '127.0.0.1') {
        throw "Unexpected listener address: $($addresses -join ', ')"
    }
    $port = $listener[0].LocalPort
    $base = "http://127.0.0.1:$port"
    foreach ($path in @('/', '/audits/test/pdf', '/audits/test/download/json',
            '/audits/test/highlighted-page.pdf?page=1')) {
        $code = & curl.exe --noproxy '*' -s -o NUL -w '%{http_code}' "$base$path"
        if ($code -ne '403') { throw "Unauthenticated $path returned $code, expected 403." }
    }
    $badHost = & curl.exe --noproxy '*' -s -o NUL -w '%{http_code}' -H 'Host: attacker.example' "$base/"
    if ($badHost -ne '403') { throw "Invalid Host returned $badHost, expected 403." }
    $hash = (Get-FileHash -Algorithm SHA256 $exe).Hash
    $bundleRoot = Split-Path $exe
    $manifest = Join-Path $notes 'bundle-sha256.txt'
    Get-ChildItem -Path $bundleRoot -Recurse -File |
        ForEach-Object {
            $relative = $_.FullName.Substring($bundleRoot.Length + 1)
            "$relative`t$((Get-FileHash -Algorithm SHA256 $_.FullName).Hash)"
        } | Sort-Object | Set-Content -Encoding UTF8 $manifest
    $packageHash = (Get-FileHash -Algorithm SHA256 $manifest).Hash
    @(
        "Native Windows socket smoke PASS",
        "Git SHA: $(git rev-parse HEAD)",
        "Executable SHA256: $hash",
        "Full-folder manifest SHA256: $packageHash",
        "Listener: 127.0.0.1:$port",
        'Unauthorized PDF/report/page requests: HTTP 403',
        'Invalid Host: HTTP 403',
        'Authenticated browser, PDF audit, Delete, and Quit require acceptance checklist.'
    ) | Set-Content $result
    Write-Output "Evidence directory: $notes"
    Get-Content $result
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
    $env:LOCALAPPDATA = $oldLocalAppData
    if (-not $KeepBuildEnvironment -and (Test-Path $venv)) {
        Remove-Item -Recurse -Force $venv
    }
}
