from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def main(path: str) -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8-sig")

    s = replace_once(s, 'APP_VERSION = "1.11.22"', 'APP_VERSION = "2.2"', 'version')
    s = replace_once(
        s,
        'APP_DATA_NAMESPACE = "PastelPaymentAssistant"\nAPP_DATA_FALLBACK = ".pastel_payment_assistant"\n',
        'APP_DATA_NAMESPACE = "PastelPaymentAssistantV2Feedback"\nAPP_DATA_FALLBACK = ".pastel_payment_assistant_v2_feedback"\nCLEAN_FEEDBACK_BUILD = True\n',
        'isolated clean app-data namespace',
    )
    s = replace_once(
        s,
        'ALLOW_BUNDLED_RULE_BOOTSTRAP = True\n',
        'ALLOW_BUNDLED_RULE_BOOTSTRAP = False\n',
        'disable private bundled rule bootstrap',
    )
    s = replace_once(
        s,
        'ttk.Label(title_box, text=f"v{APP_VERSION} Personal workspace", style="ModernSubtitle.TLabel").pack(anchor="w")\n',
        'ttk.Label(title_box, text=f"v{APP_VERSION} Clean feedback workspace", style="ModernSubtitle.TLabel").pack(anchor="w")\n',
        'clean modern workspace header',
    )
    s = replace_once(
        s,
        '''    def _startup_restore(self):\n        imported = self._bootstrap_rules_if_present()\n        restored = self._restore_session()\n        if imported and not restored:\n            self.status_var.set(f"Imported {imported} bundled saved rule(s) into this empty profile. Load a bank CSV to continue.")\n''',
        '''    def _startup_restore(self):\n        imported = self._bootstrap_rules_if_present()\n        restored = self._restore_session()\n        if imported and not restored:\n            self.status_var.set(f"Imported {imported} bundled saved rule(s) into this empty profile. Load a bank CSV to continue.")\n        elif not restored:\n            self.status_var.set("v2.2 Clean feedback build — no personal data was bundled. The adaptive Tutorial & Help will open automatically for a genuinely new workspace and can be run again at any time.")\n''',
        'clean startup message',
    )

    test_marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v2.2 Clean: isolated data plus adaptive searchable tutorial.\n    assert APP_DATA_NAMESPACE == "PastelPaymentAssistantV2Feedback"\n    assert APP_DATA_FALLBACK == ".pastel_payment_assistant_v2_feedback"\n    assert CLEAN_FEEDBACK_BUILD is True and ALLOW_BUNDLED_RULE_BOOTSTRAP is False\n    assert DEFAULT_UI_MODE == "modern" and "classic" in UI_MODES\n    assert TUTORIAL_SETTING_KEY == "__tutorial_v2_state"\n    assert search_tutorial_topics("orange transaction")[0]["id"] == "orange"\n\n'''
    s = replace_once(s, test_marker, tests + test_marker, 'clean tutorial/isolation tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to clean isolated v2.2 with adaptive searchable tutorial")


if __name__ == "__main__":
    main(sys.argv[1])
