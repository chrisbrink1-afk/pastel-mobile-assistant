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
        'from guided_walkthrough_r102 import register_r102_curriculum, install_r102_walkthrough\nfrom guided_walkthrough_r103 import register_r103_curriculum, install_r103_walkthrough\n',
        'R10.3 walkthrough imports',
    )
    s = replace_once(
        s,
        '    register_r102_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        '    register_r102_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    register_r103_curriculum(guided_tutorial_module, UPDATE_REVISION)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        'R10.3 curriculum registration',
    )
    s = replace_once(
        s,
        '    install_r102_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        '    install_r102_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n    # R10.3 keeps the action gates/curriculum but renders the walkthrough inline.\n    install_r103_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n',
        'R10.3 inline walkthrough installation',
    )
    s = s.replace('R10.2 BUILD TEST', 'R10.3 BUILD TEST')
    s = s.replace('R10.2 guided walkthrough rendered blank/incomplete', 'R10.3 inline guided walkthrough rendered blank/incomplete')
    s = s.replace('R10.2 update walkthrough first title is wrong/blank', 'R10.3 update walkthrough first title is wrong/blank')
    p.write_text(s, encoding="utf-8")
    print(f"Updated {p} for R10.3 inline highlighted walkthrough")


if __name__ == '__main__':
    main(sys.argv[1])
