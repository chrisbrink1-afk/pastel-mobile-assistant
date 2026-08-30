$ErrorActionPreference = 'Stop'

Remove-Item 'autoledger-r10-3\source-release' -Recurse -Force -ErrorAction SilentlyContinue
foreach ($subpath in @('free\application\assets','free\build','pro\application\assets','pro\build')) {
  New-Item -ItemType Directory -Force (Join-Path 'autoledger-r10-3\source-release' $subpath) | Out-Null
}

foreach ($edition in @('free','pro')) {
  Get-ChildItem "autoledger-r10-3\work\$edition" -File | Where-Object { $_.Extension -in @('.py','.pyw') } | Copy-Item -Destination "autoledger-r10-3\source-release\$edition\application" -Force
  Copy-Item "autoledger-r10-3\work\$edition\assets\*" "autoledger-r10-3\source-release\$edition\application\assets" -Force
  Copy-Item 'autoledger-r10-3\EULA.txt' "autoledger-r10-3\source-release\$edition\EULA.txt" -Force
  foreach ($file in @("${edition}_update.iss","${edition}_full.iss")) {
    Copy-Item (Join-Path 'autoledger-r10-3' $file) "autoledger-r10-3\source-release\$edition\build" -Force
  }
  foreach ($file in @(
    'autoledger-r10\r10_common_transform.py',
    'autoledger-r10-1\r10_1_common_transform.py',
    'autoledger-r10-2\r10_2_common_transform.py',
    'autoledger-r10-3\r10_3_common_transform.py',
    'autoledger-r8\r8_core_transform.py'
  )) {
    Copy-Item $file "autoledger-r10-3\source-release\$edition\build" -Force
  }
}

Copy-Item 'activation-service' 'autoledger-r10-3\source-release\pro\activation-service' -Recurse -Force
'AUTOLEDGER Free v2.2.5 R10.3 COMPLETE SOURCE - exact effective source used for this validated build.' | Set-Content -Encoding UTF8 'autoledger-r10-3\source-release\free\README_SOURCE.txt'
'AUTOLEDGER Pro v2.2.5 R10.3 COMPLETE SOURCE - exact effective source used for this validated build. Permanent private ALP225R6 signing material is intentionally excluded.' | Set-Content -Encoding UTF8 'autoledger-r10-3\source-release\pro\README_SOURCE.txt'

foreach ($required in @('r103_curriculum.py','r103_targets.py','r103_overlay.py','inline_walkthrough_r103.py')) {
  if (!(Test-Path (Join-Path 'autoledger-r10-3\source-release\free\application' $required))) { throw "Free source missing $required" }
  if (!(Test-Path (Join-Path 'autoledger-r10-3\source-release\pro\application' $required))) { throw "Pro source missing $required" }
}

Compress-Archive -Path 'autoledger-r10-3\source-release\free\*' -DestinationPath 'autoledger-r10-3\output\AUTOLEDGER_Free_v2.2.5_R10_3_COMPLETE_SOURCE.zip' -Force
Compress-Archive -Path 'autoledger-r10-3\source-release\pro\*' -DestinationPath 'autoledger-r10-3\output\AUTOLEDGER_Pro_v2.2.5_R10_3_COMPLETE_SOURCE.zip' -Force

@'
AUTOLEDGER v2.2.5 R10.3 TEST — INLINE HIGHLIGHT GUIDED WALKTHROUGH

R10.3 removes the separate tutorial window used by R10.2. The walkthrough runs inside AUTOLEDGER, highlights the exact control to use, and shows a nearby hint bubble with Back, Next and Skip Tutorial. There is no pulsing/bouncing tutorial pointer.

Required actions remain action-gated. Saved Rule Priority guidance: leave normal rules at 100; use 200/300 only when a more specific overlapping rule must take precedence over a broader rule; higher numbers are considered first.

Installers: Free Full/Standalone, Free Update, Pro Full/Standalone, Pro Update. Update validation covers R10.2 -> R10.3 and preserves Free usage, tutorial history and permanent ALP225R6 Pro entitlement. Update installers refuse clean PCs. Full installers work on clean PCs.

These TEST builds remain unsigned pending the AUTOLEDGER SYSTEMS PTY LTD code-signing certificate.
'@ | Set-Content -Encoding UTF8 'autoledger-r10-3\output\README_R10_3_TEST.txt'

Get-ChildItem 'autoledger-r10-3\output' -File | Where-Object { $_.Extension -in @('.exe','.zip') } | ForEach-Object {
  $hash = Get-FileHash $_.FullName -Algorithm SHA256
  "$($hash.Hash.ToLower())  $($_.Name)"
} | Set-Content -Encoding ASCII 'autoledger-r10-3\output\AUTOLEDGER_v2.2.5_R10_3_SHA256.txt'
