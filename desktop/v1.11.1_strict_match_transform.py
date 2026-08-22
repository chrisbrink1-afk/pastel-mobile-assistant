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
    s = replace_once(s, 'APP_VERSION = "1.11.0"', 'APP_VERSION = "1.11.1"', 'version')

    start = s.index('def smart_match(pattern: str, details: str, txn_type: str = "") -> bool:')
    end = s.index('\n\ndef repeat_description_choices', start)
    strict = '''def _contains_token_sequence(container: List[str], sequence: List[str]) -> bool:\n    if not sequence:\n        return True\n    n = len(sequence)\n    return any(container[i:i+n] == sequence for i in range(0, len(container) - n + 1))\n\n\ndef smart_match(pattern: str, details: str, txn_type: str = "") -> bool:\n    \"\"\"Conservative SMART matching based only on the bank description identity.\n\n    Names must match as whole tokens in the same order. If the saved rule contains\n    a reference number, the transaction must contain that same numeric suffix.\n    Transaction-type text is deliberately excluded so generic words cannot cause\n    false matches (for example C E BRINK must never match CHRIS BRINK).\n    \"\"\"\n    p = normalize_text(pattern)\n    d = normalize_text(details)\n    if not p or not d:\n        return False\n\n    # Exact canonical identities remain the strongest and safest match.\n    if p == normalize_text(smart_key(details, txn_type)):\n        return True\n\n    ptoks = p.split()\n    dtoks = d.split()\n    name_tokens: List[str] = []\n    reference_suffixes: List[str] = []\n\n    for tok in ptoks:\n        digits = \"\".join(re.findall(r\"\\d\", tok))\n        letters = re.sub(r\"[^A-Z]\", \"\", tok)\n        if tok.isdigit():\n            reference_suffixes.append(tok)\n        elif letters and digits and len(digits) >= 4:\n            # Treat long alphanumeric tokens as references (e.g. B0003783).\n            reference_suffixes.append(digits)\n        else:\n            name_tokens.append(tok)\n\n    # The saved name must occur as an exact whole-token sequence.\n    if name_tokens and not _contains_token_sequence(dtoks, name_tokens):\n        return False\n\n    # Every saved numeric reference must be present as a non-date suffix.\n    for suffix in reference_suffixes:\n        matched = False\n        for tok in dtoks:\n            digits = \"\".join(re.findall(r\"\\d\", tok))\n            if not digits or looks_like_date_code(digits):\n                continue\n            if digits.endswith(suffix):\n                matched = True\n                break\n        if not matched:\n            return False\n\n    return bool(name_tokens or reference_suffixes)\n'''
    s = s[:start] + strict + s[end:]

    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.1: strict identity matching prevents similar-name false allocations.\n    assert smart_match("C E BRINK", "PAYMENT TO C E BRINK", "EFT PAYMENT")\n    assert not smart_match("C E BRINK", "CHRIS BRINK", "EFT PAYMENT")\n    assert not smart_match("CHRIS BRINK", "C E BRINK", "EFT PAYMENT")\n    assert smart_match("C E BRINK 1234", "PAYMENT C E BRINK REF1234", "EFT PAYMENT")\n    assert not smart_match("C E BRINK 1234", "PAYMENT C E BRINK REF5678", "EFT PAYMENT")\n    false_name = Transaction(90, date(2026, 8, 4), Decimal("-100.00"), "EFT PAYMENT", "CHRIS BRINK", direction="PAYMENT")\n    ce_rule = Rule(90, "C E BRINK", "SMART", "C E BRINK", "7100099", False, 0, direction="PAYMENT")\n    apply_rules([false_name], [ce_rule], 0)\n    assert false_name.account == "" and not false_name.auto_allocated\n\n'''
    s = replace_once(s, marker, tests + marker, 'strict-match tests')
    p.write_text(s, encoding='utf-8')
    print(f'Transformed {p} to strict-match v1.11.1')


if __name__ == '__main__':
    main(sys.argv[1])
