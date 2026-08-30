$ErrorActionPreference = 'Stop'

python -m pip install --upgrade pyinstaller

Push-Location 'autoledger-r10-3\work\free'
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon 'assets\AUTOLEDGER_ICON.ico' --add-data 'assets;assets' --name 'AUTOLEDGER Free v2.2.5 R10.3 TEST' free_runner.pyw
if ($LASTEXITCODE -ne 0) { throw 'Free R10.3 build failed' }
Pop-Location

Push-Location 'autoledger-r10-3\work\pro'
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon 'assets\AUTOLEDGER_ICON.ico' --add-data 'assets;assets' --name 'AUTOLEDGER Pro v2.2.5 R10.3 TEST' pro_runner.pyw
if ($LASTEXITCODE -ne 0) { throw 'Pro R10.3 build failed' }
Pop-Location

$env:APPDATA = Join-Path $env:RUNNER_TEMP 'r103-bundled-smoke'
Remove-Item $env:APPDATA -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $env:APPDATA | Out-Null
$free = Resolve-Path 'autoledger-r10-3\work\free\dist\AUTOLEDGER Free v2.2.5 R10.3 TEST\AUTOLEDGER Free v2.2.5 R10.3 TEST.exe'
$pro = Resolve-Path 'autoledger-r10-3\work\pro\dist\AUTOLEDGER Pro v2.2.5 R10.3 TEST\AUTOLEDGER Pro v2.2.5 R10.3 TEST.exe'

$p = Start-Process -FilePath $free -ArgumentList '--smoke-test' -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "Free R10.3 smoke failed: $($p.ExitCode)" }
$p = Start-Process -FilePath $pro -ArgumentList '--smoke-test' -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "Pro R10.3 smoke failed: $($p.ExitCode)" }

$iscc = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (!(Test-Path $iscc)) { choco install innosetup -y --no-progress }
if (!(Test-Path $iscc)) { throw 'Inno Setup 6 not found' }

Remove-Item 'autoledger-r10-3\package','autoledger-r10-3\output' -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force 'autoledger-r10-3\package\free','autoledger-r10-3\package\pro','autoledger-r10-3\output' | Out-Null
Copy-Item 'autoledger-r10-3\work\free\dist\AUTOLEDGER Free v2.2.5 R10.3 TEST\*' 'autoledger-r10-3\package\free' -Recurse -Force
Copy-Item 'autoledger-r10-3\work\pro\dist\AUTOLEDGER Pro v2.2.5 R10.3 TEST\*' 'autoledger-r10-3\package\pro' -Recurse -Force

Push-Location 'autoledger-r10-3'
foreach ($iss in @('free_update.iss','free_full.iss','pro_update.iss','pro_full.iss')) {
  & $iscc $iss
  if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed: $iss" }
}
Pop-Location
