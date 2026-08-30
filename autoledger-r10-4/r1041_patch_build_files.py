from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent


def add_old_r104_support(text: str, edition: str) -> str:
    # After the R10.4 -> R10.4.1 target-name replacement, re-add R10.4 as a
    # supported predecessor and ensure its executable is retired on upgrade.
    old_delete = f'Type: files; Name: "{{app}}\\AUTOLEDGER {edition} v2.2.5 R10.3 TEST.exe"'
    r104_delete = f'Type: files; Name: "{{app}}\\AUTOLEDGER {edition} v2.2.5 R10.4 TEST.exe"'
    if old_delete in text and r104_delete not in text:
        text = text.replace(old_delete, old_delete + "\n" + r104_delete, 1)

    current_probe = (
        f"    FileExists(ExpandConstant('{{localappdata}}\\Programs\\AUTOLEDGER {edition}\\"
        f"AUTOLEDGER {edition} v2.2.5 R10.4.1 TEST.exe'))"
    )
    old_probe = (
        f"    FileExists(ExpandConstant('{{localappdata}}\\Programs\\AUTOLEDGER {edition}\\"
        f"AUTOLEDGER {edition} v2.2.5 R10.4 TEST.exe'))"
    )
    if current_probe in text and old_probe not in text:
        text = text.replace(current_probe, old_probe + " or\n" + current_probe, 1)
    return text


def patch_iss(path: Path, edition: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("R10.4", "R10.4.1")
    text = text.replace("R10_4", "R10_4_1")
    text = add_old_r104_support(text, edition)
    path.write_text(text, encoding="utf-8")


def patch_build_script() -> None:
    src = ROOT / "ci" / "03_build_unsigned.ps1"
    dst = ROOT / "ci" / "03_build_unsigned_r1041.generated.ps1"
    text = src.read_text(encoding="utf-8")
    text = text.replace("R10.4", "R10.4.1")
    text = text.replace("R10_4", "R10_4_1")
    dst.write_text(text, encoding="utf-8")


def main() -> None:
    source_readme = ROOT / "README_R10_4.txt"
    target_readme = ROOT / "README_R10_4_1.txt"
    readme = source_readme.read_text(encoding="utf-8")
    readme = readme.replace("R10.4", "R10.4.1")
    readme += (
        "\n\nR10.4.1 CORRECTION\n"
        "------------------\n"
        "The Guided Walkthrough now confirms a Saved Rule from the persisted Saved Rules store. "
        "If the rule is successfully created, Next unlocks even when the legacy RuleDialog result flag is false.\n"
        "This correction does not change accounting logic, Saved Rule contents, profiles, usage storage or Pro licensing.\n"
    )
    target_readme.write_text(readme, encoding="utf-8")

    patch_iss(ROOT / "free_update.iss", "Free")
    patch_iss(ROOT / "free_full.iss", "Free")
    patch_iss(ROOT / "pro_update.iss", "Pro")
    patch_iss(ROOT / "pro_full.iss", "Pro")
    patch_build_script()
    print("R10.4.1 build/install files prepared; R10.4 remains a supported update predecessor")


if __name__ == "__main__":
    main()
