$ErrorActionPreference='Stop'

Write-Host 'Building unsigned AUTOLEDGER R10.3 Windows applications...'
python -m pip install --upgrade pyinstaller

Push-Location 'autoledger-r10-3\work\free'
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon 'assets\AUTOLEDGER_ICON.ico' --add-data 'assets;assets' --name 'AUTOLEDGER Free v2.2.5 R10.3 TEST' free_runner.pyw
if ($LASTEXITCODE -ne 0) { throw 'Free R10.3 build failed' }
Pop-Location

Push-Location 'autoledger-r10-3\work\pro'
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon 'assets\AUTOLEDGER_ICON.ico' --add-data 'assets;assets' --name 'AUTOLEDGER Pro v2.2.5 R10.3 TEST' pro_runner.pyw
if ($LASTEXITCODE -ne 0) { throw 'Pro R10.3 build failed' }
Pop-Location

$iscc='C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (!(Test-Path $iscc)) { choco install innosetup -y --no-progress }
if (!(Test-Path $iscc)) { throw 'Inno Setup 6 not found' }

Remove-Item 'autoledger-r10-3\package' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'autoledger-r10-3\output-unsigned' -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force 'autoledger-r10-3\package\free' | Out-Null
New-Item -ItemType Directory -Force 'autoledger-r10-3\package\pro' | Out-Null
New-Item -ItemType Directory -Force 'autoledger-r10-3\output' | Out-Null
New-Item -ItemType Directory -Force 'autoledger-r10-3\output-unsigned' | Out-Null

Copy-Item 'autoledger-r10-3\work\free\dist\AUTOLEDGER Free v2.2.5 R10.3 TEST\*' 'autoledger-r10-3\package\free' -Recurse -Force
Copy-Item 'autoledger-r10-3\work\pro\dist\AUTOLEDGER Pro v2.2.5 R10.3 TEST\*' 'autoledger-r10-3\package\pro' -Recurse -Force

Push-Location 'autoledger-r10-3'
foreach ($iss in @('free_update.iss','free_full.iss','pro_update.iss','pro_full.iss')) {
  & $iscc $iss
  if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed: $iss" }
}
Pop-Location

Copy-Item 'autoledger-r10-3\output\*.exe' 'autoledger-r10-3\output-unsigned' -Force
@'
AUTOLEDGER v2.2.5 R10.3 UNSIGNED TEST BUILD

This package intentionally skips the final Windows validation/install-validation gates.
It is provided for immediate owner testing while code-signing/domain/certificate work is still pending.
Windows may display Unknown Publisher / SmartScreen warnings because these files are unsigned.

Contains:
- Free Full / Standalone installer
- Free Update installer
- Pro Full / Standalone installer
- Pro Update installer
'@ | Set-Content -Encoding UTF8 'autoledger-r10-3\output-unsigned\README_R10_3_UNSIGNED_TEST.txt'

Get-ChildItem 'autoledger-r10-3\output-unsigned' -Filter '*.exe' | ForEach-Object {
  $h=Get-FileHash $_.FullName -Algorithm SHA256
  "$($h.Hash.ToLower())  $($_.Name)"
} | Set-Content -Encoding ASCII 'autoledger-r10-3\output-unsigned\AUTOLEDGER_v2.2.5_R10_3_UNSIGNED_SHA256.txt'
