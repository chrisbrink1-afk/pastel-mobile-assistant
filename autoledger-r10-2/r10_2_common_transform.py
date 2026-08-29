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

    s = replace_once(s, 'UPDATE_REVISION = "R10.1"', 'UPDATE_REVISION = "R10.2"', 'R10.2 revision')
    s = replace_once(
        s,
        'from tutorial_render_fix import install_tutorial_render_fix\n',
        'from tutorial_render_fix import install_tutorial_render_fix\nfrom guided_walkthrough_r102 import register_r102_curriculum, install_r102_walkthrough\n',
        'R10.2 walkthrough imports',
    )

    old = '''    # R10.1 is a corrective update. Register its user-facing change so an\n    # updated installation starts with NEW IN THIS UPDATE, while a clean\n    # installation continues to start with the normal beginner Welcome flow.\n    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION.setdefault(\n        UPDATE_REVISION,\n        (\n            {\n                "id": "update_r101_tutorial_render_fix",\n                "title": "Guided Tutorial display reliability",\n                "body": (\n                    "R10.1 fixes a problem where the Guided Tutorial could open as a blank window after an update. "\n                    "The invalid tutorial-footer padding has been corrected. AUTOLEDGER also waits for the main window "\n                    "to finish loading, verifies that the current instruction title and body are visible, and automatically "\n                    "re-renders them if necessary."\n                ),\n            },\n        ),\n    )\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n    install_tutorial_render_fix(core, edition, licence_info, revision=UPDATE_REVISION)\n'''
    new = '''    # Permanent version-aware tutorial policy: every update revision registers\n    # its own NEW IN THIS UPDATE curriculum before the guided system is installed.\n    register_r102_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n    # Retain R10.1's render hardening, then replace the slide-like presentation\n    # with the R10.2 action-gated guided walkthrough.\n    install_tutorial_render_fix(core, edition, licence_info, revision=UPDATE_REVISION)\n    install_r102_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n'''
    s = replace_once(s, old, new, 'R10.2 guided walkthrough installation')

    s = s.replace('R10.1 BUILD TEST', 'R10.2 BUILD TEST')

    smoke_anchor = '''        app.withdraw()\n        app.update_idletasks()\n'''
    smoke_extra = '''        app.withdraw()\n        app.update_idletasks()\n        # R10.2 acceptance gate: this must be a usable walkthrough, not a static\n        # instruction page. All navigation controls must be visible on-screen.\n        if hasattr(app, "_r102_walkthrough_smoke"):\n            walk = app._r102_walkthrough_smoke("update")\n            if walk.get("title") != "NEW IN THIS UPDATE":\n                raise RuntimeError(f"R10.2 update walkthrough did not start with NEW IN THIS UPDATE: {walk!r}")\n            for button_name in ("back", "next", "skip"):\n                info = walk.get(button_name, {})\n                if not info.get("mapped") or not info.get("onscreen"):\n                    raise RuntimeError(f"R10.2 {button_name} button is not visibly usable: {walk!r}")\n            if walk.get("next", {}).get("state") == "disabled":\n                raise RuntimeError(f"R10.2 introductory Next button should be enabled: {walk!r}")\n            try:\n                app._r10_close_guided()\n            except Exception:\n                pass\n'''
    s = replace_once(s, smoke_anchor, smoke_extra, 'R10.2 walkthrough smoke gate')

    s = s.replace('R10.1 guided tutorial rendered blank/incomplete', 'R10.2 guided walkthrough rendered blank/incomplete')
    s = s.replace('R10.1 update tutorial first title is wrong/blank', 'R10.2 update walkthrough first title is wrong/blank')
    s = s.replace('R10.1 BUILD TEST', 'R10.2 BUILD TEST')
    p.write_text(s, encoding="utf-8")
    print(f"Updated {p} for R10.2 true guided walkthrough")


if __name__ == '__main__':
    main(sys.argv[1])
