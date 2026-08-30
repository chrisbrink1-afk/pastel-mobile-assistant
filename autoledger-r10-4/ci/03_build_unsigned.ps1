$ErrorActionPreference='Stop'

Write-Host 'Building unsigned AUTOLEDGER R10.4 Windows applications...'
python -m pip install --upgrade pyinstaller

Push-Location 'autoledger-r10-4\work\free'
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon 'assets\AUTOLEDGER_ICON.ico' --add-data 'assets;assets' --name 'AUTOLEDGER Free v2.2.5 R10.4 TEST' free_runner.pyw
if ($LASTEXITCODE -ne 0) { throw 'Free R10.4 build failed' }
Pop-Location

Push-Location 'autoledger-r10-4\work\pro'
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon 'assets\AUTOLEDGER_ICON.ico' --add-data 'assets;assets' --name 'AUTOLEDGER Pro v2.2.5 R10.4 TEST' pro_runner.pyw
if ($LASTEXITCODE -ne 0) { throw 'Pro R10.4 build failed' }
Pop-Location

$iscc='C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (!(Test-Path $iscc)) { choco install innosetup -y --no-progress }
if (!(Test-Path $iscc)) { throw 'Inno Setup 6 not found' }

Remove-Item 'autoledger-r10-4\package' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'autoledger-r10-4\output' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'autoledger-r10-4\output-unsigned' -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force 'autoledger-r10-4\package\free' | Out-Null
New-Item -ItemType Directory -Force 'autoledger-r10-4\package\pro' | Out-Null
New-Item -ItemType Directory -Force 'autoledger-r10-4\output' | Out-Null
New-Item -ItemType Directory -Force 'autoledger-r10-4\output-unsigned' | Out-Null

Copy-Item 'autoledger-r10-4\work\free\dist\AUTOLEDGER Free v2.2.5 R10.4 TEST\*' 'autoledger-r10-4\package\free' -Recurse -Force
Copy-Item 'autoledger-r10-4\work\pro\dist\AUTOLEDGER Pro v2.2.5 R10.4 TEST\*' 'autoledger-r10-4\package\pro' -Recurse -Force

Push-Location 'autoledger-r10-4'
foreach ($iss in @('free_update.iss','free_full.iss','pro_update.iss','pro_full.iss')) {
  & $iscc $iss
  if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed: $iss" }
}
Pop-Location

Copy-Item 'autoledger-r10-4\output\*.exe' 'autoledger-r10-4\output-unsigned' -Force
@'
AUTOLEDGER v2.2.5 R10.4 UNSIGNED TEST BUILD

R10.4 tutorial changes:
- instruction bubble automatically moves away from the required control;
- actual interactive fields/buttons are preferred over nearby labels;
- four-sided target highlight remains visible;
- a gentle animated arrow points toward the required control without using a separate tutorial popup;
- Saved Rule Priority guidance remains: 100 normal/default, 200/300 only for intentional overlapping-rule precedence.

Installer rule:
- use UPDATE when AUTOLEDGER is already installed;
- use FULL / Standalone for a clean PC or clean installation;
- R10.4 Update explicitly recognises R10.3 plus supported older R6/R8/R9/R10/R10.1/R10.2 builds;
- existing AppData, Free usage and Pro licence storage are preserved by default.

These files are unsigned and Windows may display Unknown Publisher / SmartScreen warnings until code signing is applied.

Contains:
- Free Full / Standalone installer
- Free Update installer
- Pro Full / Standalone installer
- Pro Update installer
'@ | Set-Content -Encoding UTF8 'autoledger-r10-4\output-unsigned\README_R10_4_UNSIGNED_TEST.txt'

Get-ChildItem 'autoledger-r10-4\output-unsigned' -Filter '*.exe' | ForEach-Object {
  $h=Get-FileHash $_.FullName -Algorithm SHA256
  "$($h.Hash.ToLower())  $($_.Name)"
} | Set-Content -Encoding ASCII 'autoledger-r10-4\output-unsigned\AUTOLEDGER_v2.2.5_R10_4_UNSIGNED_SHA256.txt'
