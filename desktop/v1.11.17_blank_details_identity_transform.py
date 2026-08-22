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

    s = replace_once(s, 'APP_VERSION = "1.11.16"', 'APP_VERSION = "1.11.17"', 'version')

    old = '''def rule_matches(mode: str, pattern: str, details: str, txn_type: str) -> bool:\n    \"\"\"Match a saved rule only after the strict identity safety check passes.\n\n    This guard applies to every automatic allocation mode and to both payments\n    and receipts. A loose CONTAINS/STARTS rule can therefore never bypass the\n    name/reference identity check. Transaction-type text is never used to make\n    an identity match.\n    \"\"\"\n    p = normalize_text(pattern)\n    d = normalize_text(details)\n    if not p or not d:\n        return False\n\n    # GLOBAL SAFETY GATE: all automatic allocations must first satisfy the\n    # conservative whole-token/reference matcher.\n    if not smart_match(pattern, details, txn_type):\n        return False\n\n    mode = (mode or \"SMART\").upper()\n    if mode == \"EXACT\":\n        return p == d\n    if mode == \"STARTS\":\n        return d.startswith(p)\n    if mode == \"CONTAINS\":\n        return p in d\n    # SMART already passed the strict safety gate above.\n    return True\n'''

    new = '''def rule_matches(mode: str, pattern: str, details: str, txn_type: str) -> bool:\n    \"\"\"Match saved rules conservatively, including bank charges with blank details.\n\n    Normal transactions still use the strict whole-token/reference safety gate.\n    Some Standard Bank charge rows (for example STOP ORDER HANDLING FEE) have a\n    blank description/reference field and carry their only stable identity in the\n    transaction-type field. For those blank-detail rows we allow exactly one safe\n    fallback: the saved rule pattern must equal the canonical smart_key identity.\n    Loose Contains/Starts behavior is never used for this fallback.\n    \"\"\"\n    p = normalize_text(pattern)\n    d = normalize_text(details)\n    if not p:\n        return False\n\n    # blank bank-description/reference fallback. smart_key('', txn_type) returns\n    # the normalized transaction type, so only an exact canonical identity can\n    # match. This fixes bank-charge rows without weakening normal matching.\n    if not d:\n        canonical = normalize_text(smart_key(details, txn_type))\n        return bool(canonical and p == canonical)\n\n    # GLOBAL SAFETY GATE: all normal automatic allocations must first satisfy\n    # the conservative whole-token/reference matcher.\n    if not smart_match(pattern, details, txn_type):\n        return False\n\n    mode = (mode or \"SMART\").upper()\n    if mode == \"EXACT\":\n        return p == d\n    if mode == \"STARTS\":\n        return d.startswith(p)\n    if mode == \"CONTAINS\":\n        return p in d\n    return True\n'''
    s = replace_once(s, old, new, 'blank-detail canonical identity matcher')

    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.17: Standard Bank bank-charge rows may have blank details.\n    # Only an exact canonical transaction-type identity is allowed in that case.\n    stop_fee = Transaction(1017, date(2026, 6, 1), Decimal("-50.00"), "STOP ORDER HANDLING FEE", "", direction="PAYMENT")\n    stop_rule = Rule(1017, "STOP ORDER FEE", "SMART", "STOP ORDER HANDLING FEE", "3200000", True, 15, direction="PAYMENT", description="FEE")\n    assert rule_matches(stop_rule.mode, stop_rule.pattern, stop_fee.details, stop_fee.txn_type)\n    apply_rules([stop_fee], [stop_rule], 15)\n    assert stop_fee.account == "3200000" and stop_fee.auto_allocated and stop_fee.vat and stop_fee.tax_type == 15\n    assert stop_fee.description == "FEE"\n\n    # The blank-detail fallback is exact-canonical only; similar/generic patterns\n    # must not match merely because they appear in the transaction type.\n    assert not rule_matches("SMART", "STOP ORDER", "", "STOP ORDER HANDLING FEE")\n    assert not rule_matches("CONTAINS", "HANDLING", "", "STOP ORDER HANDLING FEE")\n    assert not rule_matches("STARTS", "STOP", "", "STOP ORDER HANDLING FEE")\n    assert not rule_matches("EXACT", "STOP ORDER FEE", "", "STOP ORDER HANDLING FEE")\n\n'''
    s = replace_once(s, marker, tests + marker, 'blank-detail identity self-tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.17 with safe blank-detail recurring identity matching")


if __name__ == "__main__":
    main(sys.argv[1])
