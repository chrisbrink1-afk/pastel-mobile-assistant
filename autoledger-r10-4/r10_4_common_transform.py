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
    s = replace_once(s, 'UPDATE_REVISION = "R10.3"', 'UPDATE_REVISION = "R10.4"', 'R10.4 revision')
    s = replace_once(
        s,
        'from inline_walkthrough_r103 import register_r103_curriculum, install_r103_inline_walkthrough\n',
        'from inline_walkthrough_r103 import register_r103_curriculum, install_r103_inline_walkthrough\nfrom inline_walkthrough_r104 import register_r104_curriculum, install_r104_walkthrough\n',
        'R10.4 imports',
    )
    s = replace_once(
        s,
        '    register_r103_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        '    register_r103_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    register_r104_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        'R10.4 curriculum registration',
    )
    s = replace_once(
        s,
        '    install_r103_inline_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        '    install_r103_inline_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n    # R10.4 supersedes only tutorial rendering/target selection; accounting logic and gates stay unchanged.\n    install_r104_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        'R10.4 walkthrough installation',
    )
    s = s.replace('R10.3 BUILD TEST', 'R10.4 BUILD TEST')
    s = s.replace('R10.3 inline guided walkthrough', 'R10.4 non-obscuring arrow guided walkthrough')
    s = s.replace('R10.3 update walkthrough', 'R10.4 update walkthrough')
    p.write_text(s, encoding="utf-8")
    print(f"Updated {p} for R10.4 non-obscuring arrow walkthrough")


if __name__ == '__main__':
    main(sys.argv[1])
