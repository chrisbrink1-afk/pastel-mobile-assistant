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
    s = replace_once(s, 'UPDATE_REVISION = "R8"', 'UPDATE_REVISION = "R10"', 'revision')
    s = replace_once(
        s,
        'import autoledger_core as core\n',
        'import autoledger_core as core\nfrom help_topics import install_complete_help\nfrom guided_tutorial import install_guided_tutorial\n',
        'R10 imports',
    )
    old = '''def configure(edition: str, licence_info: dict | None = None) -> None:\n    configure_common(edition)\n    if edition.upper() == "FREE":\n        install_free_controls()\n    install_edition_ui(edition, licence_info)\n'''
    new = '''def configure(edition: str, licence_info: dict | None = None) -> None:\n    configure_common(edition)\n    install_complete_help(core, edition, licence_info)\n    install_guided_tutorial(core, edition, licence_info, revision=UPDATE_REVISION)\n    if edition.upper() == "FREE":\n        install_free_controls()\n    install_edition_ui(edition, licence_info)\n'''
    s = replace_once(s, old, new, 'install R10 help and guided tutorial')
    s = s.replace('"R8" not in app.title()', '"R10" not in app.title()')
    s = s.replace('R8 BUILD TEST', 'R10 BUILD TEST')
    p.write_text(s, encoding="utf-8")
    print(f"Updated {p} for R10 guided tutorial")


if __name__ == '__main__':
    main(sys.argv[1])
