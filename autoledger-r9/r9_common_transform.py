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
    s = replace_once(s, 'UPDATE_REVISION = "R8"', 'UPDATE_REVISION = "R9"', 'revision')
    s = replace_once(
        s,
        'import autoledger_core as core\n',
        'import autoledger_core as core\nfrom help_topics import install_complete_help\n',
        'complete-help import',
    )
    old = '''def configure(edition: str, licence_info: dict | None = None) -> None:\n    configure_common(edition)\n    if edition.upper() == "FREE":\n        install_free_controls()\n    install_edition_ui(edition, licence_info)\n'''
    new = '''def configure(edition: str, licence_info: dict | None = None) -> None:\n    configure_common(edition)\n    install_complete_help(core, edition, licence_info)\n    if edition.upper() == "FREE":\n        install_free_controls()\n    install_edition_ui(edition, licence_info)\n'''
    s = replace_once(s, old, new, 'install complete help')
    s = s.replace('"R8" not in app.title()', '"R9" not in app.title()')
    s = s.replace('R8 BUILD TEST', 'R9 BUILD TEST')
    p.write_text(s, encoding="utf-8")
    print(f"Updated {p} for R9 complete help")


if __name__ == '__main__':
    main(sys.argv[1])
