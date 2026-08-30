$ErrorActionPreference='Stop'
$env:APPDATA = Join-Path $env:RUNNER_TEMP 'r103-inline-walkthrough-appdata'
Remove-Item $env:APPDATA -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $env:APPDATA | Out-Null
Push-Location 'autoledger-r10-3\work\free'
@'
import time
import autoledger_common as common
common.configure('FREE')
import autoledger_core as core

app = core.App()
try:
    app.geometry('1100x760+20+20'); app.deiconify(); app.update_idletasks(); app.update()
    assert common.UPDATE_REVISION == 'R10.3'
    update = app._r103_walkthrough_smoke('update')
    print('R10.3 update inline snapshot:', update)
    assert update['title'] == 'NEW IN THIS UPDATE' and update['step_id'] == 'update_intro', update
    assert update['separate_window'] is False and update['tutorial_toplevel'] is False, update
    assert getattr(app, '_r10_guided_window', None) is None
    assert getattr(app, '_r102_pointer_window', None) is None
    assert app._r103_overlay.bubble.winfo_toplevel() is app
    assert all(update[k]['mapped'] and update[k]['onscreen'] for k in ('back','next','skip')), update
    app._r10_close_guided()

    clean = app._r103_walkthrough_smoke('clean')
    assert clean['step_id'] == 'welcome' and clean['title'] != 'NEW IN THIS UPDATE', clean
    app._r10_guided_next.invoke(); app.update()
    profile = app._r103_walkthrough_snapshot()
    assert profile['step_id'] == 'profile' and profile['next']['state'] == 'disabled', profile
    app.profile_manager.rename_profile(app.active_profile_id, 'Tutorial Test Company')
    app._refresh_profile_ui(); app.update()
    deadline=time.time()+1.5
    while time.time()<deadline and app._r103_walkthrough_snapshot()['next']['state']=='disabled': app.update(); time.sleep(.03)
    assert app._r103_walkthrough_snapshot()['next']['state']!='disabled'
    app._r10_guided_next.invoke(); app.update(); time.sleep(.15); app.update()
    setting=app._r103_walkthrough_snapshot(); print('R10.3 exact field snapshot:',setting)
    assert setting['step_id']=='cashbook_gl',setting
    assert setting['target_class'] in ('entry','tentry','combobox','tcombobox','spinbox','tspinbox'),setting
    assert setting['highlight_parts']==4,setting
    assert app._r103_overlay.bubble.winfo_toplevel() is app

    priority=app._r103_definition('rule_priority'); pbody=priority['body'].casefold()
    assert 'leave priority at 100' in pbody and '200' in pbody and 'higher' in pbody and 'overlap' in pbody,priority
    app._r103_overlay.skip.invoke(); app.update()
    assert not getattr(app,'_r103_walkthrough_active',False) and getattr(app,'_r10_guided_window',None) is None and app.winfo_exists()
finally:
    try: app._r10_close_guided()
    except Exception: pass
    app.destroy()
'@ | Set-Content -Encoding UTF8 r103_inline_acceptance_test.py
python r103_inline_acceptance_test.py
if ($LASTEXITCODE -ne 0) { throw 'R10.3 inline walkthrough acceptance test failed' }
Pop-Location

Remove-Item 'autoledger-r10-3\audit-output' -Recurse -Force -ErrorAction SilentlyContinue
python 'autoledger-r9\help_inventory.py' 'autoledger-r10-3\work\free\autoledger_core.py' 'autoledger-r10-3\audit-output'
Push-Location 'autoledger-r9'
python help_coverage_test.py '..\autoledger-r10-3\audit-output\ui_feature_inventory.json'
if ($LASTEXITCODE -ne 0) { throw 'Complete-help coverage test failed' }
Pop-Location
