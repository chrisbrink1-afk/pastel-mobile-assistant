$ErrorActionPreference='Stop'

foreach ($script in @('autoledger-r10-4\free_update.iss','autoledger-r10-4\pro_update.iss')) {
  $txt = Get-Content $script -Raw
  foreach ($rev in @('R6','R8','R9','R10','R10.1','R10.2','R10.3')) {
    if ($txt -notmatch [regex]::Escape($rev)) { throw "$script does not recognise older $rev installations" }
  }
}

$env:LOCALAPPDATA = Join-Path $env:RUNNER_TEMP 'r104-localappdata'
$env:APPDATA = Join-Path $env:RUNNER_TEMP 'r104-appdata'
New-Item -ItemType Directory -Force $env:LOCALAPPDATA,$env:APPDATA | Out-Null
$freeDir = Join-Path $env:LOCALAPPDATA 'Programs\AUTOLEDGER Free'
$proDir = Join-Path $env:LOCALAPPDATA 'Programs\AUTOLEDGER Pro'
$freeData = Join-Path $env:APPDATA 'AUTOLEDGER_V225_TEST_Free'
$proData = Join-Path $env:APPDATA 'AUTOLEDGER_V225_TEST_Pro'

foreach ($p in @($freeDir,$proDir,$freeData,$proData)) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
$freeUpdate = Resolve-Path 'autoledger-r10-4\output\AUTOLEDGER_Free_v2.2.5_R10_4_UPDATE_from_OLDER_TEST_Setup.exe'
$p = Start-Process -FilePath $freeUpdate -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if ($p.ExitCode -eq 0) { throw 'R10.4 Update unexpectedly installed on a clean PC' }

foreach ($p in @($freeDir,$proDir,$freeData,$proData)) { New-Item -ItemType Directory -Force $p | Out-Null }
New-Item -ItemType File -Force (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.3 TEST.exe') | Out-Null
New-Item -ItemType File -Force (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.3 TEST.exe') | Out-Null

'{"version":1,"months":{"2026-08":{"used":37,"statements":{"seed":{"entries":37}}}}}' | Set-Content -Encoding UTF8 (Join-Path $freeData 'free_usage_r6.json')
'{"profile":"R10.3 seed","setting":"preserve me"}' | Set-Content -Encoding UTF8 (Join-Path $freeData 'r104_preservation_marker.json')
'{"version":1,"key":"R10.3-PRO-LICENCE-SEED","payload":{"customer":"Existing R10.3 customer"}}' | Set-Content -Encoding UTF8 (Join-Path $proData 'pro_licence_r6.json')
'{"profile":"R10.3 pro seed","setting":"preserve me"}' | Set-Content -Encoding UTF8 (Join-Path $proData 'r104_preservation_marker.json')

$freeUsageHash = (Get-FileHash (Join-Path $freeData 'free_usage_r6.json') -Algorithm SHA256).Hash
$freeMarkerHash = (Get-FileHash (Join-Path $freeData 'r104_preservation_marker.json') -Algorithm SHA256).Hash
$proLicenceHash = (Get-FileHash (Join-Path $proData 'pro_licence_r6.json') -Algorithm SHA256).Hash
$proMarkerHash = (Get-FileHash (Join-Path $proData 'r104_preservation_marker.json') -Algorithm SHA256).Hash

$proUpdate = Resolve-Path 'autoledger-r10-4\output\AUTOLEDGER_Pro_v2.2.5_R10_4_UPDATE_from_OLDER_TEST_Setup.exe'
$p = Start-Process -FilePath $freeUpdate -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "Free R10.4 update failed: $($p.ExitCode)" }
$p = Start-Process -FilePath $proUpdate -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "Pro R10.4 update failed: $($p.ExitCode)" }

$fc = Get-Content (Join-Path $freeData 'install_context_r10.json') -Raw | ConvertFrom-Json
$pc = Get-Content (Join-Path $proData 'install_context_r10.json') -Raw | ConvertFrom-Json
if ($fc.revision -ne 'R10.4' -or $fc.install_kind -ne 'update') { throw 'Free R10.4 update context wrong' }
if ($pc.revision -ne 'R10.4' -or $pc.install_kind -ne 'update') { throw 'Pro R10.4 update context wrong' }

if ((Get-FileHash (Join-Path $freeData 'free_usage_r6.json') -Algorithm SHA256).Hash -ne $freeUsageHash) { throw 'Free usage changed during R10.4 update' }
if ((Get-FileHash (Join-Path $freeData 'r104_preservation_marker.json') -Algorithm SHA256).Hash -ne $freeMarkerHash) { throw 'Free local settings marker changed during R10.4 update' }
if ((Get-FileHash (Join-Path $proData 'pro_licence_r6.json') -Algorithm SHA256).Hash -ne $proLicenceHash) { throw 'Pro licence data changed during R10.4 update' }
if ((Get-FileHash (Join-Path $proData 'r104_preservation_marker.json') -Algorithm SHA256).Hash -ne $proMarkerHash) { throw 'Pro local settings marker changed during R10.4 update' }

if (!(Test-Path (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.4 TEST.exe'))) { throw 'Free R10.4 executable missing after update' }
if (!(Test-Path (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.4 TEST.exe'))) { throw 'Pro R10.4 executable missing after update' }
if (Test-Path (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.3 TEST.exe')) { throw 'Old Free R10.3 executable was not retired' }
if (Test-Path (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.3 TEST.exe')) { throw 'Old Pro R10.3 executable was not retired' }

# Clean-PC Full / Standalone path.
foreach ($p in @($freeDir,$proDir,$freeData,$proData)) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
$freeFull = Resolve-Path 'autoledger-r10-4\output\AUTOLEDGER_Free_v2.2.5_R10_4_FULL_STANDALONE_TEST_Setup.exe'
$proFull = Resolve-Path 'autoledger-r10-4\output\AUTOLEDGER_Pro_v2.2.5_R10_4_FULL_STANDALONE_TEST_Setup.exe'
$p = Start-Process -FilePath $freeFull -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if ($p.ExitCode -ne 0) { throw 'Free R10.4 full install failed' }
$p = Start-Process -FilePath $proFull -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if ($p.ExitCode -ne 0) { throw 'Pro R10.4 full install failed' }
$fc = Get-Content (Join-Path $freeData 'install_context_r10.json') -Raw | ConvertFrom-Json
$pc = Get-Content (Join-Path $proData 'install_context_r10.json') -Raw | ConvertFrom-Json
if ($fc.revision -ne 'R10.4' -or $fc.install_kind -ne 'clean') { throw 'Free R10.4 standalone context wrong' }
if ($pc.revision -ne 'R10.4' -or $pc.install_kind -ne 'clean') { throw 'Pro R10.4 standalone context wrong' }
