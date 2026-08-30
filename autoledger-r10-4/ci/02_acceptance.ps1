$ErrorActionPreference='Stop'
$env:APPDATA = Join-Path $env:RUNNER_TEMP 'r104-walkthrough-appdata'
Remove-Item $env:APPDATA -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $env:APPDATA | Out-Null

Push-Location 'autoledger-r10-4\work\free'
@'
import time
import autoledger_common as common
common.configure('FREE')
import autoledger_core as core

app = core.App()
try:
    app.geometry('1100x760+20+20')
    app.deiconify(); app.update_idletasks(); app.update()
    assert common.UPDATE_REVISION == 'R10.4', common.UPDATE_REVISION

    update = app._r104_walkthrough_smoke('update')
    print('R10.4 update snapshot:', update)
    assert update['title'] == 'NEW IN THIS UPDATE' and update['step_id'] == 'update_intro', update
    assert update['separate_window'] is False and update['tutorial_toplevel'] is False, update
    assert getattr(app, '_r10_guided_window', None) is None
    assert getattr(app, '_r102_pointer_window', None) is None
    assert app._r104_overlay.bubble.winfo_toplevel() is app
    assert all(update[k]['mapped'] and update[k]['onscreen'] for k in ('back','next','skip')), update
    app._r10_close_guided(); app.update()

    clean = app._r104_walkthrough_smoke('clean')
    assert clean['step_id'] == 'welcome' and clean['title'] != 'NEW IN THIS UPDATE', clean
    app._r10_guided_next.invoke(); app.update(); time.sleep(.1); app.update()
    profile = app._r104_walkthrough_snapshot()
    print('R10.4 profile snapshot:', profile)
    assert profile['step_id'] == 'profile', profile
    assert profile['target_class'] in ('button','tbutton'), profile
    assert profile['highlight_parts'] == 4 and profile['arrow_mapped'], profile
    assert not profile['bubble_overlaps_target'], profile
    assert profile['next']['state'] == 'disabled', profile

    app.profile_manager.rename_profile(app.active_profile_id, 'Tutorial Test Company')
    app._refresh_profile_ui(); app.update()
    deadline = time.time() + 1.5
    while time.time() < deadline and app._r104_walkthrough_snapshot()['next']['state'] == 'disabled':
        app.update(); time.sleep(.03)
    assert app._r104_walkthrough_snapshot()['next']['state'] != 'disabled'
    app._r10_guided_next.invoke(); app.update(); time.sleep(.15); app.update()

    setting = app._r104_walkthrough_snapshot()
    print('R10.4 settings field snapshot:', setting)
    assert setting['step_id'] == 'cashbook_gl', setting
    assert setting['target_class'] in ('entry','tentry','combobox','tcombobox','spinbox','tspinbox','text'), setting
    assert setting['highlight_parts'] == 4 and setting['arrow_mapped'], setting
    assert not setting['bubble_overlaps_target'], setting
    assert app._r104_overlay.bubble.winfo_toplevel() is app

    # Repositioning must remain non-obscuring after the application is resized.
    app.geometry('900x650+30+30'); app.update_idletasks(); app.update(); time.sleep(.3); app.update()
    resized = app._r104_walkthrough_snapshot()
    print('R10.4 resized snapshot:', resized)
    assert resized['highlight_parts'] == 4 and resized['arrow_mapped'], resized
    assert not resized['bubble_overlaps_target'], resized

    app._navigate_modern('settings'); app.update_idletasks(); app.update()
    save_target = app._r104_resolve_target(('Save settings',), 'save_settings')
    assert save_target is not None and str(save_target.winfo_class()).casefold() in ('button','tbutton'), str(save_target)
    gl_target = app._r104_resolve_target(('Cash Book bank GL account',), 'cashbook_gl')
    assert gl_target is not None and str(gl_target.winfo_class()).casefold() in ('entry','tentry','combobox','tcombobox','spinbox','tspinbox','text'), str(gl_target)

    priority = app._r104_definition('rule_priority')
    pbody = priority['body'].casefold()
    assert 'leave priority at 100' in pbody and '200' in pbody and 'higher' in pbody and 'overlap' in pbody, priority

    update_steps = list(app._r102_step_ids('update'))
    assert update_steps[0] == 'update_intro'
    assert any('r104' in x for x in update_steps[1:6]), update_steps[:8]

    app._r104_overlay.skip.invoke(); app.update()
    assert not getattr(app, '_r104_walkthrough_active', False)
    assert getattr(app, '_r10_guided_window', None) is None
    assert getattr(app, '_r102_pointer_window', None) is None
    assert app.winfo_exists()
finally:
    try: app._r10_close_guided()
    except Exception: pass
    app.destroy()
'@ | Set-Content -Encoding UTF8 r104_acceptance_test.py
python r104_acceptance_test.py
if ($LASTEXITCODE -ne 0) { throw 'R10.4 non-obscuring arrow walkthrough acceptance test failed' }
Pop-Location

Remove-Item 'autoledger-r10-4\audit-output' -Recurse -Force -ErrorAction SilentlyContinue
python 'autoledger-r9\help_inventory.py' 'autoledger-r10-4\work\free\autoledger_core.py' 'autoledger-r10-4\audit-output'
Push-Location 'autoledger-r9'
python help_coverage_test.py '..\autoledger-r10-4\audit-output\ui_feature_inventory.json'
if ($LASTEXITCODE -ne 0) { throw 'Complete-help coverage test failed' }
Pop-Location
