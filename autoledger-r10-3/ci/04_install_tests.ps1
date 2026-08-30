$ErrorActionPreference='Stop'
foreach($script in @('autoledger-r10-3\free_update.iss','autoledger-r10-3\pro_update.iss')){
 $txt=Get-Content $script -Raw
 foreach($rev in @('R6','R8','R9','R10','R10.1','R10.2')){if($txt-notmatch[regex]::Escape($rev)){throw "$script does not recognise older $rev installations"}}
}
$freeDir=Join-Path $env:LOCALAPPDATA 'Programs\AUTOLEDGER Free';$proDir=Join-Path $env:LOCALAPPDATA 'Programs\AUTOLEDGER Pro';$freeData=Join-Path $env:APPDATA 'AUTOLEDGER_V225_TEST_Free';$proData=Join-Path $env:APPDATA 'AUTOLEDGER_V225_TEST_Pro'
foreach($p in @($freeDir,$proDir,$freeData,$proData)){Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue}
$update=Resolve-Path 'autoledger-r10-3\output\AUTOLEDGER_Free_v2.2.5_R10_3_UPDATE_from_OLDER_TEST_Setup.exe'
$p=Start-Process -FilePath $update -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
if($p.ExitCode-eq 0){throw 'R10.3 Update unexpectedly installed on a clean PC'}

foreach($p in @($freeDir,$proDir,$freeData,$proData)){Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $p|Out-Null}
New-Item -ItemType File -Force (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.2 TEST.exe')|Out-Null
New-Item -ItemType File -Force (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.2 TEST.exe')|Out-Null
'{"version":1,"months":{"2026-08":{"used":37,"statements":{"seed":{"entries":37}}}}}'|Set-Content -Encoding UTF8 (Join-Path $freeData 'free_usage_r6.json')
'{"version":1,"last_prompted_revision":"R10.2","last_outcome":"completed","last_mode":"update"}'|Set-Content -Encoding UTF8 (Join-Path $freeData 'guided_tutorial_state.json')
'{"version":1,"last_prompted_revision":"R10.2","last_outcome":"completed","last_mode":"update"}'|Set-Content -Encoding UTF8 (Join-Path $proData 'guided_tutorial_state.json')
$sample=(Get-Content 'autoledger-r8\testdata\R6_SAMPLE_ENTITLEMENT_KEY.txt' -Raw).Trim()
Push-Location 'autoledger-r10-3\work\pro'
python -c "import json,sys;from license_crypto import decode_and_verify_key;k=sys.argv[1];p=decode_and_verify_key(k);open(sys.argv[2],'w',encoding='utf-8').write(json.dumps({'version':1,'key':k,'payload':p},indent=2))" $sample (Join-Path $proData 'pro_licence_r6.json')
if($LASTEXITCODE-ne 0){throw 'Could not seed permanent Pro entitlement'}
Pop-Location
$fh=(Get-FileHash (Join-Path $freeData 'free_usage_r6.json') -Algorithm SHA256).Hash;$ph=(Get-FileHash (Join-Path $proData 'pro_licence_r6.json') -Algorithm SHA256).Hash;$fth=(Get-FileHash (Join-Path $freeData 'guided_tutorial_state.json') -Algorithm SHA256).Hash;$pth=(Get-FileHash (Join-Path $proData 'guided_tutorial_state.json') -Algorithm SHA256).Hash
$fu=Resolve-Path 'autoledger-r10-3\output\AUTOLEDGER_Free_v2.2.5_R10_3_UPDATE_from_OLDER_TEST_Setup.exe';$pu=Resolve-Path 'autoledger-r10-3\output\AUTOLEDGER_Pro_v2.2.5_R10_3_UPDATE_from_OLDER_TEST_Setup.exe'
$p=Start-Process -FilePath $fu -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait;if($p.ExitCode-ne 0){throw "Free R10.3 update failed: $($p.ExitCode)"}
$p=Start-Process -FilePath $pu -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait;if($p.ExitCode-ne 0){throw "Pro R10.3 update failed: $($p.ExitCode)"}
$fc=Get-Content (Join-Path $freeData 'install_context_r10.json') -Raw|ConvertFrom-Json;$pc=Get-Content (Join-Path $proData 'install_context_r10.json') -Raw|ConvertFrom-Json
if($fc.revision-ne'R10.3'-or$fc.install_kind-ne'update'){throw 'Free update context wrong'};if($pc.revision-ne'R10.3'-or$pc.install_kind-ne'update'){throw 'Pro update context wrong'}
if((Get-FileHash (Join-Path $freeData 'free_usage_r6.json') -Algorithm SHA256).Hash-ne$fh){throw 'Free usage changed'};if((Get-FileHash (Join-Path $proData 'pro_licence_r6.json') -Algorithm SHA256).Hash-ne$ph){throw 'Pro licence changed'};if((Get-FileHash (Join-Path $freeData 'guided_tutorial_state.json') -Algorithm SHA256).Hash-ne$fth){throw 'Free tutorial history changed'};if((Get-FileHash (Join-Path $proData 'guided_tutorial_state.json') -Algorithm SHA256).Hash-ne$pth){throw 'Pro tutorial history changed'}
$freeExe=Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.3 TEST.exe';$proExe=Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.3 TEST.exe'
if(!(Test-Path $freeExe)-or!(Test-Path $proExe)){throw 'R10.3 update executable missing'};if(Test-Path (Join-Path $freeDir 'AUTOLEDGER Free v2.2.5 R10.2 TEST.exe')){throw 'Old Free R10.2 exe not retired'};if(Test-Path (Join-Path $proDir 'AUTOLEDGER Pro v2.2.5 R10.2 TEST.exe')){throw 'Old Pro R10.2 exe not retired'}
$p=Start-Process -FilePath $freeExe -ArgumentList '--smoke-test' -PassThru -Wait;if($p.ExitCode-ne 0){throw 'Installed Free smoke failed'};$p=Start-Process -FilePath $proExe -ArgumentList '--smoke-test' -PassThru -Wait;if($p.ExitCode-ne 0){throw 'Installed Pro smoke failed'};$p=Start-Process -FilePath $proExe -ArgumentList '--existing-licence-smoke-test' -PassThru -Wait;if($p.ExitCode-ne 0){throw 'Existing Pro entitlement rejected'}

foreach($p in @($freeDir,$proDir,$freeData,$proData)){Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue}
$ff=Resolve-Path 'autoledger-r10-3\output\AUTOLEDGER_Free_v2.2.5_R10_3_FULL_STANDALONE_TEST_Setup.exe';$pf=Resolve-Path 'autoledger-r10-3\output\AUTOLEDGER_Pro_v2.2.5_R10_3_FULL_STANDALONE_TEST_Setup.exe'
$p=Start-Process -FilePath $ff -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait;if($p.ExitCode-ne 0){throw 'Free full install failed'};$p=Start-Process -FilePath $pf -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait;if($p.ExitCode-ne 0){throw 'Pro full install failed'}
$fc=Get-Content (Join-Path $freeData 'install_context_r10.json') -Raw|ConvertFrom-Json;$pc=Get-Content (Join-Path $proData 'install_context_r10.json') -Raw|ConvertFrom-Json
if($fc.revision-ne'R10.3'-or$fc.install_kind-ne'clean'){throw 'Free standalone context wrong'};if($pc.revision-ne'R10.3'-or$pc.install_kind-ne'clean'){throw 'Pro standalone context wrong'}
