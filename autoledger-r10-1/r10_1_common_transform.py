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

    s = replace_once(s, 'UPDATE_REVISION = "R10"', 'UPDATE_REVISION = "R10.1"', 'R10.1 revision')
    s = replace_once(
        s,
        'from guided_tutorial import install_guided_tutorial\n',
        'from guided_tutorial import install_guided_tutorial\nimport guided_tutorial as guided_tutorial_module\nfrom tutorial_render_fix import install_tutorial_render_fix\n',
        'R10.1 tutorial-fix imports',
    )

    old_install = '    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n'
    new_install = '''    # R10.1 is a corrective update. Register its user-facing change so an\n    # updated installation starts with NEW IN THIS UPDATE, while a clean\n    # installation continues to start with the normal beginner Welcome flow.\n    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION.setdefault(\n        UPDATE_REVISION,\n        (\n            {\n                "id": "update_r101_tutorial_render_fix",\n                "title": "Guided Tutorial display reliability",\n                "body": (\n                    "R10.1 fixes a problem where the Guided Tutorial could open as a blank window after an update. "\n                    "The invalid tutorial-footer padding has been corrected. AUTOLEDGER also waits for the main window "\n                    "to finish loading, verifies that the current instruction title and body are visible, and automatically "\n                    "re-renders them if necessary."\n                ),\n            },\n        ),\n    )\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n    install_tutorial_render_fix(core, edition, licence_info, revision=UPDATE_REVISION)\n'''
    s = replace_once(s, old_install, new_install, 'install R10.1 tutorial render fix')

    smoke_anchor = '''        app.withdraw()\n        app.update_idletasks()\n'''
    smoke_extra = '''        app.withdraw()\n        app.update_idletasks()\n        # R10.1 regression: a real guided tutorial must contain visible text,\n        # not merely create an empty/blank Toplevel. Exercise update mode because\n        # that is the path on which the R10 defect was reported.\n        if hasattr(app, "_r101_tutorial_render_smoke"):\n            snap = app._r101_tutorial_render_smoke("update")\n            if snap.get("title") != "NEW IN THIS UPDATE":\n                raise RuntimeError(f"R10.1 update tutorial first title is wrong/blank: {snap!r}")\n            if not snap.get("body") or not snap.get("step") or not snap.get("visible"):\n                raise RuntimeError(f"R10.1 guided tutorial rendered blank/incomplete: {snap!r}")\n            try:\n                app._r10_close_guided()\n            except Exception:\n                pass\n'''
    s = replace_once(s, smoke_anchor, smoke_extra, 'R10.1 rendered-content smoke gate')

    s = s.replace('R10 BUILD TEST', 'R10.1 BUILD TEST')
    p.write_text(s, encoding="utf-8")

    # ROOT CAUSE OF THE R10 BLANK TUTORIAL:
    # tkinter.Frame padx/pady accept a single screen-distance value, not the
    # two-element tuple accepted by pack/grid external padding. R10 used
    # pady=(0, 14) while constructing the footer Frame. Tk raised:
    #   TclError: bad screen distance "0 14"
    # after the Toplevel existed but before the tutorial content was displayed.
    guided = p.parent / "guided_tutorial.py"
    g = guided.read_text(encoding="utf-8")
    g = replace_once(
        g,
        'footer = core.tk.Frame(win, bg="#f4f7fb", padx=14, pady=(0, 14))',
        'footer = core.tk.Frame(win, bg="#f4f7fb", padx=14, pady=0)',
        'invalid R10 footer Frame pady',
    )
    g = replace_once(
        g,
        'footer.pack(fill="x")',
        'footer.pack(fill="x", pady=(0, 14))',
        'move footer external padding to pack',
    )
    guided.write_text(g, encoding="utf-8")

    print(f"Updated {p} for R10.1 tutorial rendering fix")
    print(f"Corrected invalid Tk Frame padding in {guided}")


if __name__ == '__main__':
    main(sys.argv[1])
