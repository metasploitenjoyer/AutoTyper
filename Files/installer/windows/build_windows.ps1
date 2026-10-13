# Builds the Windows release:
#   AutoTyper\AutoTyper-SetupWindows.exe       (installer, next to the Files folder)
#   Files\build\AutoTyper-Portable.zip         (no-install version)
# Run:  powershell -ExecutionPolicy Bypass -File Files\installer\windows\build_windows.ps1
# Optional: $env:SKIP_TESTS = "1"  /  $env:SKIP_SELFTEST = "1"
#           $env:AUTOTYPER_NO_PRUNE = "1"   build WITHOUT the size optimizations (to measure before/after)
#           $env:AUTOTYPER_UPX = "1"        experimental UPX packing (off by default)
$ErrorActionPreference = "Stop"
$files = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path       # ...\AutoTyper\Files
$repo  = (Resolve-Path (Join-Path $files "..")).Path                  # ...\AutoTyper
Set-Location $files

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10+ is required to BUILD the installer (people who install AutoTyper need nothing). Get it from https://www.python.org/downloads/"
}

Step "Creating build environment"
python -m venv .venv-build
$py = Join-Path $files ".venv-build\Scripts\python.exe"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

$version = (& $py -c "import sys; sys.path.insert(0,'src'); import autotyper; print(autotyper.__version__)").Trim()
Write-Host "Building AutoTyper $version"

if (-not (Test-Path "assets\icons\icon.ico")) { & $py assets\make_icons.py }

if ($env:SKIP_TESTS -ne "1") {
    Step "Running tests"
    $env:QT_QPA_PLATFORM = "offscreen"
    & $py -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
    Remove-Item Env:QT_QPA_PLATFORM
}

Step "Packaging the app with PyInstaller (bundles Python + PySide6)"
& $py -m PyInstaller --noconfirm --clean --distpath build\dist --workpath build\work installer\AutoTyper.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
$exe = Join-Path $files "build\dist\AutoTyper\AutoTyper.exe"
if (-not (Test-Path $exe)) { throw "build\dist\AutoTyper\AutoTyper.exe was not created" }

Step "Size of the packaged app (biggest files first)"
$tag = if ($env:AUTOTYPER_NO_PRUNE -eq "1") { "before" } else { "after" }
& $py installer\size_report.py build\dist\AutoTyper --top 15 --save "build\size-$tag.json"
if ((Test-Path "build\size-before.json") -and (Test-Path "build\size-after.json")) {
    Write-Host "`nBefore / after optimization:"
    & $py installer\size_report.py --compare build\size-before.json build\size-after.json
}

if ($env:SKIP_SELFTEST -ne "1") {
    Step "Checking that the packaged app contains all its dependencies"
    $qtPrev = $env:QT_QPA_PLATFORM
    $env:QT_QPA_PLATFORM = "offscreen"
    try {
        $p = Start-Process -FilePath $exe -ArgumentList "--self-test" -Wait -PassThru
        if ($p.ExitCode -ne 0) {
            Get-Content (Join-Path $env:TEMP "AutoTyper-selftest.log") -ErrorAction SilentlyContinue
            throw "Self-test of the packaged app failed (see log above). To check whether the size pruning is the cause, set AUTOTYPER_NO_PRUNE=1 and build again, then tell me what the log says."
        }
    }
    finally {
        if ($null -eq $qtPrev) {
            Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
        } else {
            $env:QT_QPA_PLATFORM = $qtPrev
        }
    }
    Write-Host "Self-test passed" -ForegroundColor Green
}

Step "Creating the portable ZIP"
$zip = Join-Path $files "build\AutoTyper-Portable.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path (Join-Path $files "build\dist\AutoTyper") -DestinationPath $zip
Write-Host "Portable ZIP: $zip"

Step "Building the installer with Inno Setup"
function Find-Iscc {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    return $null
}
$iscc = Find-Iscc
if (-not $iscc -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "Inno Setup not found - installing it with winget..."
    winget install -e --id JRSoftware.InnoSetup --silent --accept-package-agreements --accept-source-agreements
    $iscc = Find-Iscc
}
if (-not $iscc) { throw "Inno Setup 6 not found. Install it from https://jrsoftware.org/isdl.php and run this script again." }

& $iscc "/DAppVersion=$version" (Join-Path $files "installer\windows\AutoTyper.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

$built = Join-Path $files "build\AutoTyper-SetupWindows.exe"
if (-not (Test-Path $built)) { throw "Inno Setup did not produce $built" }
Copy-Item $built (Join-Path $repo "AutoTyper-SetupWindows.exe") -Force

$setupMb = [math]::Round((Get-Item $built).Length / 1MB, 1)
$zipMb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "`nDONE. Installer: $(Join-Path $repo 'AutoTyper-SetupWindows.exe')" -ForegroundColor Green
Write-Host "Installer size: $setupMb MB    Portable ZIP: $zipMb MB    (target: under 25 MB)"
if ($setupMb -ge 25) { Write-Host "NOTE: the installer is 25 MB or more. Check the size report above for what is still large." -ForegroundColor Yellow }
