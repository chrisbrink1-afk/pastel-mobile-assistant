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

    s = replace_once(s, 'APP_VERSION = "1.11.19"', 'APP_VERSION = "2.0"', 'version')
    s = replace_once(
        s,
        'APP_DATA_NAMESPACE = "PastelPaymentAssistant"\nAPP_DATA_FALLBACK = ".pastel_payment_assistant"\n',
        'APP_DATA_NAMESPACE = "PastelPaymentAssistantV2Feedback"\nAPP_DATA_FALLBACK = ".pastel_payment_assistant_v2_feedback"\nCLEAN_FEEDBACK_BUILD = True\n',
        'isolated v2 app-data namespace',
    )
    s = replace_once(
        s,
        'ALLOW_BUNDLED_RULE_BOOTSTRAP = True\n',
        'ALLOW_BUNDLED_RULE_BOOTSTRAP = False\n',
        'disable private bootstrap in clean build',
    )

    s = replace_once(
        s,
        '''    def _startup_restore(self):\n        imported = self._bootstrap_rules_if_present()\n        restored = self._restore_session()\n        if imported and not restored:\n            self.status_var.set(f"Imported {imported} bundled saved rule(s) into this empty profile. Load a bank CSV to continue.")\n''',
        '''    def _startup_restore(self):\n        imported = self._bootstrap_rules_if_present()\n        restored = self._restore_session()\n        if imported and not restored:\n            self.status_var.set(f"Imported {imported} bundled saved rule(s) into this empty profile. Load a bank CSV to continue.")\n        elif not restored:\n            self.status_var.set("v2.0 Clean feedback build — no personal rules, settings, history, profiles or saved session were bundled. Load a bank CSV to begin.")\n''',
        'clean feedback startup message',
    )

    test_marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v2.0 Clean: use a separate app-data namespace and never bootstrap private rules.\n    assert APP_DATA_NAMESPACE == "PastelPaymentAssistantV2Feedback"\n    assert APP_DATA_FALLBACK == ".pastel_payment_assistant_v2_feedback"\n    assert CLEAN_FEEDBACK_BUILD is True and ALLOW_BUNDLED_RULE_BOOTSTRAP is False\n\n'''
    s = replace_once(s, test_marker, tests + test_marker, 'clean feedback isolation self-test')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to clean isolated v2.0 feedback build")


if __name__ == "__main__":
    main(sys.argv[1])
