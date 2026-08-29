from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def main(path: str) -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8")

    s = replace_once(s, 'UPDATE_REVISION = "R10.2"', 'UPDATE_REVISION = "R10.3"', 'R10.3 revision')
    s = replace_once(
        s,
        'from guided_walkthrough_r102 import register_r102_curriculum, install_r102_walkthrough\n',
        'from guided_walkthrough_r102 import register_r102_curriculum, install_r102_walkthrough\n'
        'from inline_walkthrough_r103 import register_r103_curriculum, install_r103_inline_walkthrough\n',
        'R10.3 inline walkthrough import',
    )

    old_install = '''    # Permanent version-aware tutorial policy: every update revision registers\n    # its own NEW IN THIS UPDATE curriculum before the guided system is installed.\n    register_r102_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n    # Retain R10.1's render hardening, then replace the slide-like presentation\n    # with the R10.2 action-gated guided walkthrough.\n    install_tutorial_render_fix(core, edition, licence_info, revision=UPDATE_REVISION)\n    install_r102_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n'''
    new_install = '''    # Permanent version-aware tutorial policy: every update revision registers\n    # its own NEW IN THIS UPDATE curriculum before the guided system is installed.\n    register_r103_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n    # Keep R10.1 rendering hardening and R10.2's action/rule-field tracking,\n    # then replace the popup presentation entirely with R10.3's inline\n    # highlight + hint-bubble walkthrough.\n    install_tutorial_render_fix(core, edition, licence_info, revision=UPDATE_REVISION)\n    install_r102_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n    install_r103_inline_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n'''
    s = replace_once(s, old_install, new_install, 'R10.3 inline walkthrough installation')

    old_smoke = '''        app.withdraw()\n        app.update_idletasks()\n        # R10.2 acceptance gate: this must be a usable walkthrough, not a static\n        # instruction page. All navigation controls must be visible on-screen.\n        if hasattr(app, "_r102_walkthrough_smoke"):\n            walk = app._r102_walkthrough_smoke("update")\n            if walk.get("title") != "NEW IN THIS UPDATE":\n                raise RuntimeError(f"R10.2 update walkthrough did not start with NEW IN THIS UPDATE: {walk!r}")\n            for button_name in ("back", "next", "skip"):\n                info = walk.get(button_name, {})\n                if not info.get("mapped") or not info.get("onscreen"):\n                    raise RuntimeError(f"R10.2 {button_name} button is not visibly usable: {walk!r}")\n            if walk.get("next", {}).get("state") == "disabled":\n                raise RuntimeError(f"R10.2 introductory Next button should be enabled: {walk!r}")\n            try:\n                app._r10_close_guided()\n            except Exception:\n                pass\n'''
    new_smoke = '''        app.geometry("1100x760+20+20")\n        app.deiconify()\n        app.update_idletasks()\n        # R10.3 acceptance gate: tutorial guidance must be embedded in the\n        # normal AUTOLEDGER window. No separate tutorial window may exist.\n        if hasattr(app, "_r103_inline_smoke"):\n            walk = app._r103_inline_smoke("update")\n            if not walk.get("no_tutorial_window"):\n                raise RuntimeError(f"R10.3 created a separate tutorial window: {walk!r}")\n            if walk.get("title") != "NEW IN THIS UPDATE":\n                raise RuntimeError(f"R10.3 update walkthrough did not start with NEW IN THIS UPDATE: {walk!r}")\n            if not walk.get("bubble_mapped"):\n                raise RuntimeError(f"R10.3 hint bubble is not visible: {walk!r}")\n            for button_name in ("back", "next", "skip"):\n                info = walk.get(button_name, {})\n                if not info.get("exists") or not info.get("mapped"):\n                    raise RuntimeError(f"R10.3 {button_name} control is not available: {walk!r}")\n            try:\n                app._r10_close_guided()\n            except Exception:\n                pass\n'''
    s = replace_once(s, old_smoke, new_smoke, 'R10.3 inline smoke gate')

    # R10.1's old bundled smoke check specifically expected a separate popup
    # tutorial window and therefore conflicts with R10.3's deliberate no-popup
    # design. R10.3 has its own stronger inline smoke gate above, so remove only
    # that obsolete inherited check before building the standalone EXEs.
    legacy_popup_smoke = '''        # R10.1 regression: a real guided tutorial must contain visible text,\n        # not merely create an empty/blank Toplevel. Exercise update mode because\n        # that is the path on which the R10 defect was reported.\n        if hasattr(app, "_r101_tutorial_render_smoke"):\n            snap = app._r101_tutorial_render_smoke("update")\n            if snap.get("title") != "NEW IN THIS UPDATE":\n                raise RuntimeError(f"R10.2 update walkthrough first title is wrong/blank: {snap!r}")\n            if not snap.get("body") or not snap.get("step") or not snap.get("visible"):\n                raise RuntimeError(f"R10.2 guided walkthrough rendered blank/incomplete: {snap!r}")\n            try:\n                app._r10_close_guided()\n            except Exception:\n                pass\n'''
    s = replace_once(s, legacy_popup_smoke, '', 'remove obsolete R10.1 popup smoke gate')

    s = s.replace('R10.2 BUILD TEST', 'R10.3 BUILD TEST')
    s = s.replace('R10.2 guided walkthrough rendered blank/incomplete', 'R10.3 inline guided walkthrough rendered blank/incomplete')
    s = s.replace('R10.2 update walkthrough first title is wrong/blank', 'R10.3 update walkthrough first title is wrong/blank')
    p.write_text(s, encoding="utf-8")

    # Smooth R10.3 navigation: keep the current hint visible until the next
    # hint has been rendered. This avoids a brief blank/flicker between steps
    # and keeps navigation controls available while Tk settles the next page.
    inline = p.with_name('inline_walkthrough_r103.py')
    if inline.exists():
        walk = inline.read_text(encoding='utf-8')
        old_move = '''        if 0 <= new_index < len(self._r10_guided_steps):\n            self._r10_guided_index = new_index\n            _clear_visuals(self)\n            _show_step(self)\n'''
        new_move = '''        if 0 <= new_index < len(self._r10_guided_steps):\n            self._r10_guided_index = new_index\n            # Keep the existing bubble/highlight visible until the replacement\n            # for the new step is ready. _show_step invalidates the visual\n            # signature and schedules the correct replacement.\n            _show_step(self)\n'''
        walk = replace_once(walk, old_move, new_move, 'R10.3 continuous hint navigation')
        inline.write_text(walk, encoding='utf-8')
        print(f"Updated {inline} for continuous R10.3 hint navigation")

    print(f"Updated {p} for R10.3 inline highlight walkthrough")


if __name__ == '__main__':
    main(sys.argv[1])
