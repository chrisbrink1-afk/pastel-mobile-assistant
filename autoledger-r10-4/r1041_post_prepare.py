from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
FIX = ROOT / "r1041_rule_gate_fix.py"


def patch_common(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    old_revision = 'UPDATE_REVISION = "R10.4"'
    new_revision = 'UPDATE_REVISION = "R10.4.1"'
    if old_revision not in text:
        raise RuntimeError(f"{path}: R10.4 revision marker not found")
    text = text.replace(old_revision, new_revision, 1)

    import_anchor = "from inline_walkthrough_r104 import register_r104_curriculum, install_r104_walkthrough\n"
    import_line = "from r1041_rule_gate_fix import install_r1041_rule_gate_fix\n"
    if import_anchor not in text:
        raise RuntimeError(f"{path}: R10.4 import anchor not found")
    if import_line not in text:
        text = text.replace(import_anchor, import_anchor + import_line, 1)

    install_anchor = "    install_r104_walkthrough(core, edition, licence_info, revision=UPDATE_REVISION)\n"
    install_line = "    install_r1041_rule_gate_fix(core, edition, licence_info, revision=UPDATE_REVISION)\n"
    if install_anchor not in text:
        raise RuntimeError(f"{path}: R10.4 install anchor not found")
    if install_line not in text:
        text = text.replace(install_anchor, install_anchor + install_line, 1)

    text = text.replace("R10.4 BUILD TEST", "R10.4.1 BUILD TEST")
    text = text.replace("R10.4 non-obscuring arrow guided walkthrough", "R10.4.1 corrected Saved Rule guided walkthrough")
    text = text.replace("R10.4 update walkthrough", "R10.4.1 update walkthrough")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    for edition in ("free", "pro"):
        dest = ROOT / "work" / edition
        if not dest.exists():
            raise RuntimeError(f"Prepared source directory missing: {dest}")
        shutil.copy2(FIX, dest / FIX.name)
        patch_common(dest / "autoledger_common.py")

    print("R10.4.1 post-prepare patch applied to Free and Pro source")


if __name__ == "__main__":
    main()
