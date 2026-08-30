$ErrorActionPreference='Stop'

$env:LOCALAPPDATA = Join-Path $env:RUNNER_TEMP 'r1041-from-r104-localappdata'
$env:APPDATA = Join-Path $env:RUNNER_TEMP 'r1041-from-r104-appdata'
$freeDir = Join-Path $env:LOCALAPPDATA 'Programs\AUTOLEDGER Free'
$proDir = Join-Path $env:LOCALAPPDATA 'Programs\AUTOLEDGER Pro'
$freeData = Join-Path $env:APPDATA 'AUTOLEDGER_V225_TEST_Free'
$proData = Join-Path $env:APPDATA 'AUTOLEDGER_V225_TEST_Pro'

foreach ($p in @($freeDir,$proDir,$freeData,$proData)) {
  Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force $p | Out-Null
}

# Simulate the exact currently-installed predecessor the user is running.
New-Item -ItemType File -Force (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.4 TEST.exe') | Out-Null
New-Item -ItemType File -Force (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.4 TEST.exe') | Out-Null

'{"version":1,"months":{"2026-08":{"used":19}}}' | Set-Content -Encoding UTF8 (Join-Path $freeData 'free_usage_r6.json')
'{"profile":"R10.4 current profile","settings":"preserve","saved_rules":"preserve"}' | Set-Content -Encoding UTF8 (Join-Path $freeData 'r104_profile_rules_marker.json')
'{"version":1,"key":"R10.4-PRO-LICENCE-PRESERVATION-SEED"}' | Set-Content -Encoding UTF8 (Join-Path $proData 'pro_licence_r6.json')
'{"profile":"R10.4 current profile","settings":"preserve","saved_rules":"preserve"}' | Set-Content -Encoding UTF8 (Join-Path $proData 'r104_profile_rules_marker.json')

$freeUsageHash = (Get-FileHash (Join-Path $freeData 'free_usage_r6.json') -Algorithm SHA256).Hash
$freeProfileHash = (Get-FileHash (Join-Path $freeData 'r104_profile_rules_marker.json') -Algorithm SHA256).Hash
$proLicenceHash = (Get-FileHash (Join-Path $proData 'pro_licence_r6.json') -Algorithm SHA256).Hash
$proProfileHash = (Get-FileHash (Join-Path $proData 'r104_profile_rules_marker.json') -Algorithm SHA256).Hash

$freeUpdate = Resolve-Path 'autoledger-r10-4\output\AUTOLEDGER_Free_v2.2.5_R10_4_1_UPDATE_from_OLDER_TEST_Setup.exe'
$proUpdate = Resolve-Path 'autoledger-r10-4\output\AUTOLEDGER_Pro_v2.2.5_R10_4_1_UPDATE_from_OLDER_TEST_Setup.exe'

$p = Start-Process -FilePath $freeUpdate -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "Free R10.4 -> R10.4.1 update failed: $($p.ExitCode)" }
$p = Start-Process -FilePath $proUpdate -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "Pro R10.4 -> R10.4.1 update failed: $($p.ExitCode)" }

if (!(Test-Path (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.4.1 TEST.exe'))) { throw 'Free R10.4.1 executable missing after update' }
if (!(Test-Path (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.4.1 TEST.exe'))) { throw 'Pro R10.4.1 executable missing after update' }
if (Test-Path (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.4 TEST.exe')) { throw 'Old Free R10.4 executable was not retired' }
if (Test-Path (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.4 TEST.exe')) { throw 'Old Pro R10.4 executable was not retired' }

$fc = Get-Content (Join-Path $freeData 'install_context_r10.json') -Raw | ConvertFrom-Json
$pc = Get-Content (Join-Path $proData 'install_context_r10.json') -Raw | ConvertFrom-Json
if ($fc.revision -ne 'R10.4.1' -or $fc.install_kind -ne 'update') { throw 'Free R10.4.1 update context wrong' }
if ($pc.revision -ne 'R10.4.1' -or $pc.install_kind -ne 'update') { throw 'Pro R10.4.1 update context wrong' }

if ((Get-FileHash (Join-Path $freeData 'free_usage_r6.json') -Algorithm SHA256).Hash -ne $freeUsageHash) { throw 'Free usage changed during R10.4 -> R10.4.1 update' }
if ((Get-FileHash (Join-Path $freeData 'r104_profile_rules_marker.json') -Algorithm SHA256).Hash -ne $freeProfileHash) { throw 'Free profile/rules data changed during R10.4 -> R10.4.1 update' }
if ((Get-FileHash (Join-Path $proData 'pro_licence_r6.json') -Algorithm SHA256).Hash -ne $proLicenceHash) { throw 'Pro licence data changed during R10.4 -> R10.4.1 update' }
if ((Get-FileHash (Join-Path $proData 'r104_profile_rules_marker.json') -Algorithm SHA256).Hash -ne $proProfileHash) { throw 'Pro profile/rules data changed during R10.4 -> R10.4.1 update' }

Write-Host 'R10.4 -> R10.4.1 Free/Pro update preservation test passed'
