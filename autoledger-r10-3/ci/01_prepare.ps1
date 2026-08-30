$ErrorActionPreference='Stop'

Push-Location 'activation-service'
node test.mjs
if ($LASTEXITCODE -ne 0) { throw 'Activation-service tests failed' }
Pop-Location

python desktop/tutorial_ci_diagnostic.py
if ($LASTEXITCODE -ne 0) { throw 'Original v2.2 reconstruction/regression suite failed' }
if (!(Test-Path 'desktop\diag_v22_clean.pyw')) { throw 'Reconstructed source was not produced' }

Push-Location 'autoledger-r8'
python test_licensing_vectors.py
if ($LASTEXITCODE -ne 0) { throw 'Permanent R6 entitlement compatibility test failed' }
Pop-Location

python -m pip install --quiet pillow
python autoledger-r8/generate_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Asset generation failed' }

Remove-Item 'autoledger-r10-3\work' -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force 'autoledger-r10-3\work\free\assets' | Out-Null
New-Item -ItemType Directory -Force 'autoledger-r10-3\work\pro\assets' | Out-Null

Copy-Item 'desktop\diag_v22_clean.pyw' 'autoledger-r10-3\work\free\autoledger_core.py' -Force
Copy-Item 'desktop\diag_v22_clean.pyw' 'autoledger-r10-3\work\pro\autoledger_core.py' -Force
python 'autoledger-r8\r8_core_transform.py' 'autoledger-r10-3\work\free\autoledger_core.py'
python 'autoledger-r8\r8_core_transform.py' 'autoledger-r10-3\work\pro\autoledger_core.py'

Copy-Item 'autoledger-r8\autoledger_common.py' 'autoledger-r10-3\work\free\autoledger_common.py' -Force
Copy-Item 'autoledger-r8\autoledger_common.py' 'autoledger-r10-3\work\pro\autoledger_common.py' -Force
python 'autoledger-r10\r10_common_transform.py' 'autoledger-r10-3\work\free\autoledger_common.py'
python 'autoledger-r10\r10_common_transform.py' 'autoledger-r10-3\work\pro\autoledger_common.py'

foreach ($edition in @('free','pro')) {
  $dest = "autoledger-r10-3\work\$edition"
  Copy-Item 'autoledger-r9\help_topics.py' "$dest\help_topics.py" -Force
  Copy-Item 'autoledger-r10\guided_tutorial.py' "$dest\guided_tutorial.py" -Force
  Copy-Item 'autoledger-r10-1\tutorial_render_fix.py' "$dest\tutorial_render_fix.py" -Force
  Copy-Item 'autoledger-r10-2\guided_walkthrough_r102.py' "$dest\guided_walkthrough_r102.py" -Force
  foreach ($m in @('r103_curriculum.py','r103_targets.py','r103_overlay.py','inline_walkthrough_r103.py')) {
    Copy-Item (Join-Path 'autoledger-r10-3' $m) (Join-Path $dest $m) -Force
  }
  Copy-Item 'autoledger-r8\assets\*' "$dest\assets" -Force
}
Copy-Item 'autoledger-r8\free_runner.pyw' 'autoledger-r10-3\work\free\free_runner.pyw' -Force
Copy-Item 'autoledger-r8\pro_runner.pyw' 'autoledger-r10-3\work\pro\pro_runner.pyw' -Force
foreach ($m in @('license_crypto.py','activation_crypto.py','device_identity.py','pro_licensing.py')) { Copy-Item (Join-Path 'autoledger-r8' $m) (Join-Path 'autoledger-r10-3\work\pro' $m) -Force }

foreach ($edition in @('free','pro')) {
  $common = "autoledger-r10-3\work\$edition\autoledger_common.py"
  python 'autoledger-r10-1\r10_1_common_transform.py' $common
  python 'autoledger-r10-2\r10_2_common_transform.py' $common
  python 'autoledger-r10-3\r10_3_common_transform.py' $common
}

Copy-Item 'autoledger-r8\EULA.txt' 'autoledger-r10-3\EULA.txt' -Force
New-Item -ItemType Directory -Force 'autoledger-r10-3\assets' | Out-Null
Copy-Item 'autoledger-r8\assets\*' 'autoledger-r10-3\assets' -Force

foreach ($edition in @('free','pro')) {
  Get-ChildItem "autoledger-r10-3\work\$edition" -File | Where-Object { $_.Extension -in @('.py','.pyw') } | ForEach-Object {
    python -m py_compile $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Compile failed: $($_.FullName)" }
  }
}
