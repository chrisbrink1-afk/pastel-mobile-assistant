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
    s = replace_once(s, 'APP_VERSION = "1.11.1"', 'APP_VERSION = "1.11.2"', 'version')

    start = s.index('def rule_matches(mode: str, pattern: str, details: str, txn_type: str) -> bool:')
    end = s.index('\n\ndef mode_rank', start)
    safe_rule_matches = '''def rule_matches(mode: str, pattern: str, details: str, txn_type: str) -> bool:\n    \"\"\"Match a saved rule only after the strict identity safety check passes.\n\n    This guard applies to every automatic allocation mode and to both payments\n    and receipts. A loose CONTAINS/STARTS rule can therefore never bypass the\n    name/reference identity check. Transaction-type text is never used to make\n    an identity match.\n    \"\"\"\n    p = normalize_text(pattern)\n    d = normalize_text(details)\n    if not p or not d:\n        return False\n\n    # GLOBAL SAFETY GATE: all automatic allocations must first satisfy the\n    # conservative whole-token/reference matcher.\n    if not smart_match(pattern, details, txn_type):\n        return False\n\n    mode = (mode or \"SMART\").upper()\n    if mode == \"EXACT\":\n        return p == d\n    if mode == \"STARTS\":\n        return d.startswith(p)\n    if mode == \"CONTAINS\":\n        return p in d\n    # SMART already passed the strict safety gate above.\n    return True\n'''
    s = s[:start] + safe_rule_matches + s[end:]

    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.2: strict identity protection applies to ALL rule modes and directions.\n    for test_mode in ("SMART", "CONTAINS", "STARTS", "EXACT"):\n        bad_payment = Transaction(101, date(2026, 8, 5), Decimal("-100.00"), "EFT PAYMENT", "CHRIS BRINK", direction="PAYMENT")\n        ce_payment_rule = Rule(101, "C E BRINK", test_mode, "C E BRINK", "7100099", False, 0, direction="PAYMENT")\n        apply_rules([bad_payment], [ce_payment_rule], 0)\n        assert bad_payment.account == "" and not bad_payment.auto_allocated, test_mode\n\n        bad_receipt = Transaction(102, date(2026, 8, 5), Decimal("100.00"), "EFT RECEIPT", "CHRIS BRINK", direction="RECEIPT")\n        ce_receipt_rule = Rule(102, "C E BRINK", test_mode, "C E BRINK", "4100099", False, 0, direction="RECEIPT")\n        apply_rules([bad_receipt], [ce_receipt_rule], 0)\n        assert bad_receipt.account == "" and not bad_receipt.auto_allocated, test_mode\n\n    # Reference mismatches are blocked globally too, even for loose modes.\n    for test_mode in ("SMART", "CONTAINS", "STARTS"):\n        wrong_ref = Transaction(103, date(2026, 8, 5), Decimal("-200.00"), "EFT PAYMENT", "C E BRINK REF5678", direction="PAYMENT")\n        ref_rule = Rule(103, "C E BRINK 1234", test_mode, "C E BRINK 1234", "7100088", False, 0, direction="PAYMENT")\n        apply_rules([wrong_ref], [ref_rule], 0)\n        assert wrong_ref.account == "" and not wrong_ref.auto_allocated, test_mode\n\n'''
    s = replace_once(s, marker, tests + marker, 'global strict-match tests')
    p.write_text(s, encoding='utf-8')
    print(f'Transformed {p} to global-safe v1.11.2')


if __name__ == '__main__':
    main(sys.argv[1])
