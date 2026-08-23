from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
RESULT = DESKTOP / "TUTORIAL_SCRIPT_DIAGNOSTIC_RESULT.txt"

TRANSFORMS = [
    "v1.11.1_strict_match_transform.py",
    "v1.11.2_global_match_transform.py",
    "v1.11.3_amount_description_transform.py",
    "v1.11.4_amount_review_transform.py",
    "v1.11.5_sequential_reference_transform.py",
    "v1.11.6_profiles_transform.py",
    "v1.11.7_multi_review_assignment_transform.py",
    "v1.11.8_pre_remove_main_review_method.py",
    "v1.11.8_rule_dialog_review_table_transform.py",
    "v1.11.9_visible_rule_assignment_transform.py",
    "v1.11.10_resizable_rule_dialog_transform.py",
    "v1.11.11_scrollable_rule_dialog_transform.py",
    "v1.11.12_rule_edits_stay_auto_transform.py",
    "v1.11.13_select_manual_allocations_transform.py",
    "v1.11.14_additive_allocation_selection_transform.py",
    "v1.11.15_user_friendly_help_transform.py",
    "v1.11.16_recurring_identity_apply_transform.py",
    "v1.11.17_blank_details_identity_transform.py",
    "v1.11.18_receipt_bank_sign_transform.py",
    "v1.11.19_autosave_session_transform.py",
    "v1.11.20_recurring_payee_identity_transform.py",
    "v1.11.21_modern_classic_ui_transform.py",
    "v1.11.22_adaptive_tutorial_transform.py",
    "v1.11.22_tutorial_classic_restore_transform.py",
]


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    print("RUN:", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=False)


def recreate_sources() -> tuple[Path, Path]:
    personal = DESKTOP / "diag_v11122_personal.pyw"
    clean = DESKTOP / "diag_v22_clean.pyw"

    run(["git", "fetch", "origin", "feature/v1.11-allocation-controls"])
    source = subprocess.check_output(
        ["git", "show", "origin/feature/v1.11-allocation-controls:desktop/v1.11_final.pyw"],
        cwd=ROOT,
    )
    personal.write_bytes(source)

    for transform in TRANSFORMS:
        run([sys.executable, str(DESKTOP / transform), str(personal)])

    py_compile.compile(str(personal), doraise=True)
    run([sys.executable, str(personal), "--self-test"])

    shutil.copy2(personal, clean)
    run([sys.executable, str(DESKTOP / "v2.2_clean_feedback_transform.py"), str(clean)])
    py_compile.compile(str(clean), doraise=True)
    run([sys.executable, str(clean), "--self-test"])
    return personal, clean


def load_module(path: Path, name: str, appdata: Path):
    os.environ["APPDATA"] = str(appdata)
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"Could not create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def exercise_ui(path: Path, name: str, expect_clean: bool) -> None:
    with tempfile.TemporaryDirectory() as td:
        appdata = Path(td)
        mod = load_module(path, name, appdata)
        app = mod.App()
        try:
            app.withdraw()
            app.update_idletasks()

            assert app.ui_mode == "modern", app.ui_mode
            assert mod.should_auto_start_tutorial(app.store) is True

            snap = mod.tutorial_workspace_snapshot(app.store, app.txns, app.receipts)
            assert snap["loaded"] is False
            assert "load" in mod.adaptive_tutorial_topic_ids(snap)
            assert mod.search_tutorial_topics("orange transaction")[0]["id"] == "orange"
            assert mod.search_tutorial_topics("receipt negative")[0]["id"] == "receipt_sign"
            assert mod.search_tutorial_topics("wrong gl")[0]["id"] == "wrong_gl"

            app.start_tutorial(auto=False)
            app.update_idletasks()
            assert app.tutorial_window.winfo_exists()
            assert app.tutorial_list.size() > 5

            app.tutorial_search_var.set("wrong gl")
            app._tutorial_search()
            app.update_idletasks()
            assert app.tutorial_title_var.get() == "An automatic allocation used the wrong GL"

            app._tutorial_clear_search()
            app.update_idletasks()
            app._tutorial_rescan()
            app.update_idletasks()
            app._tutorial_close()
            app.update_idletasks()

            app._apply_ui_mode("classic")
            app.update_idletasks()
            assert app.ui_mode == "classic"
            app.start_tutorial(auto=False)
            app.update_idletasks()
            assert app.ui_mode == "modern"
            app._tutorial_close()
            app.update_idletasks()
            assert app.ui_mode == "classic"

            app._tutorial_record_state("skipped")
            assert mod.should_auto_start_tutorial(app.store) is False

            app._apply_ui_mode("modern")
            app._navigate_modern("dashboard")
            app._navigate_modern("payments")
            app._navigate_modern("receipts")
            app._navigate_modern("rules")
            app._navigate_modern("settings")
            app.update_idletasks()
            assert app._save_session() is True

            if expect_clean:
                assert mod.APP_DATA_NAMESPACE == "PastelPaymentAssistantV2Feedback"
                assert mod.ALLOW_BUNDLED_RULE_BOOTSTRAP is False
            else:
                assert mod.APP_DATA_NAMESPACE == "PastelPaymentAssistant"
                assert mod.ALLOW_BUNDLED_RULE_BOOTSTRAP is True
        finally:
            try:
                win = getattr(app, "tutorial_window", None)
                if win is not None and win.winfo_exists():
                    win.destroy()
            except Exception:
                pass
            app.destroy()


def main() -> int:
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    lines = [
        "Pastel Payment Assistant tutorial script diagnostic",
        f"Run ID: {run_id}",
        f"Attempt: {attempt}",
    ]
    try:
        personal, clean = recreate_sources()
        lines.append("Personal transform/compile/self-test: success")
        lines.append("Clean transform/compile/self-test: success")

        exercise_ui(personal, "diag_personal_ui", False)
        lines.append("Personal tutorial UI smoke: success")
        exercise_ui(clean, "diag_clean_ui", True)
        lines.append("Clean tutorial UI smoke: success")
        lines.append("RESULT: SUCCESS")
        RESULT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines), flush=True)
        return 0
    except Exception:
        lines.append("RESULT: FAILURE")
        lines.append("")
        lines.append(traceback.format_exc())
        RESULT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
