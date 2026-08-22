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
    s = replace_once(s, 'APP_VERSION = "1.11.4"', 'APP_VERSION = "1.11.5"', 'version')

    marker = '''def period_for_date(d: date, fiscal_start_month: int) -> int:\n'''
    helper = '''def assign_monthly_sequential_references(txns: List["Transaction"]) -> None:\n    \"\"\"Assign a unique Pastel reference to every transaction in calendar-month order.\n\n    Payments use P<month>-0001 and receipts use R<month>-0001. Multiple\n    transactions on the same date are sequenced by their original bank-statement\n    row number, so no two rows in the same direction/month receive the same\n    reference in a loaded statement. Saved/manual rule references are deliberately\n    overwritten by this transaction-level sequence.\n    \"\"\"\n    counters: Dict[Tuple[str, int], int] = {}\n    ordered = sorted(\n        txns,\n        key=lambda t: (\n            (t.direction or \"PAYMENT\").upper(),\n            t.txn_date.year,\n            t.txn_date.month,\n            t.txn_date,\n            t.row_no,\n        ),\n    )\n    for t in ordered:\n        direction = (t.direction or \"PAYMENT\").upper()\n        prefix = \"R\" if direction == \"RECEIPT\" else \"P\"\n        key = (direction, t.txn_date.month)\n        seq = counters.get(key, 0) + 1\n        counters[key] = seq\n        t.pastel_ref = f\"{prefix}{t.txn_date.month}-{seq:04d}\"\n\n\n'''
    s = replace_once(s, marker, helper + marker, 'monthly sequential reference helper')

    s = replace_once(
        s,
        '''def validate_export(txns: List[Transaction], settings: Dict[str, str], label: str = "transactions") -> Tuple[List[str], List[str]]:\n    errors, warnings = [], []\n''',
        '''def validate_export(txns: List[Transaction], settings: Dict[str, str], label: str = "transactions") -> Tuple[List[str], List[str]]:\n    assign_monthly_sequential_references(txns)\n    errors, warnings = [], []\n''',
        'reference assignment before validation',
    )

    s = replace_once(
        s,
        '''    vat_count = 0\n    trunc_count = 0\n    for t in exportable:\n''',
        '''    vat_count = 0\n    trunc_count = 0\n    seen_refs = set()\n    for t in exportable:\n''',
        'duplicate reference validation set',
    )

    s = replace_once(
        s,
        '''        ref = (t.pastel_ref or "").strip()\n        if len(ref) > 8:\n            errors.append(f"Row {t.row_no}: Pastel reference '{ref}' exceeds 8 characters.")\n''',
        '''        ref = (t.pastel_ref or "").strip()\n        if len(ref) > 8:\n            errors.append(f"Row {t.row_no}: Pastel reference '{ref}' exceeds 8 characters.")\n        if ref in seen_refs:\n            errors.append(f"Row {t.row_no}: duplicate Pastel reference '{ref}' was generated. Export is blocked to prevent duplicate references entering Pastel.")\n        elif ref:\n            seen_refs.add(ref)\n''',
        'duplicate reference validation',
    )

    s = replace_once(
        s,
        '''def pastel_rows(txns: List[Transaction], settings: Dict[str, str]):\n    project = settings.get("project_code", "").strip()\n''',
        '''def pastel_rows(txns: List[Transaction], settings: Dict[str, str]):\n    # Re-assert unique sequential references at the final export boundary so\n    # saved-rule or manual-reference text can never create duplicate CSV refs.\n    assign_monthly_sequential_references(txns)\n    project = settings.get("project_code", "").strip()\n''',
        'reference assignment at export boundary',
    )

    s = replace_once(
        s,
        '''        apply_rules(self.txns, self.store.rules("PAYMENT"), default_tax)\n        apply_rules(self.receipts, self.store.rules("RECEIPT"), default_tax)\n        for d in self.DIRECTIONS:\n''',
        '''        apply_rules(self.txns, self.store.rules("PAYMENT"), default_tax)\n        apply_rules(self.receipts, self.store.rules("RECEIPT"), default_tax)\n        assign_monthly_sequential_references(self.txns + self.receipts)\n        for d in self.DIRECTIONS:\n''',
        'reference assignment after applying rules',
    )

    s = replace_once(
        s,
        '''            ("Pastel reference (max 8)", "ref"),\n''',
        '''            ("Pastel reference (auto-generated on each transaction)", "ref"),\n''',
        'rule dialog reference label',
    )

    test_marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.5: calendar-month sequential Pastel references are unique per transaction.\n    june_refs = [\n        Transaction(30, date(2026, 6, 1), Decimal("-100.00"), "PAYMENT", "JUNE ONE A", direction="PAYMENT"),\n        Transaction(31, date(2026, 6, 1), Decimal("-200.00"), "PAYMENT", "JUNE ONE B", direction="PAYMENT"),\n        Transaction(32, date(2026, 6, 2), Decimal("-300.00"), "PAYMENT", "JUNE TWO", direction="PAYMENT"),\n        Transaction(33, date(2026, 7, 1), Decimal("-400.00"), "PAYMENT", "JULY ONE", direction="PAYMENT"),\n    ]\n    june_receipts = [\n        Transaction(34, date(2026, 6, 1), Decimal("500.00"), "RECEIPT", "JUNE RECEIPT A", direction="RECEIPT"),\n        Transaction(35, date(2026, 6, 1), Decimal("600.00"), "RECEIPT", "JUNE RECEIPT B", direction="RECEIPT"),\n    ]\n    assign_monthly_sequential_references(june_refs + june_receipts)\n    assert [t.pastel_ref for t in june_refs] == ["P6-0001", "P6-0002", "P6-0003", "P7-0001"]\n    assert [t.pastel_ref for t in june_receipts] == ["R6-0001", "R6-0002"]\n    assert len({t.pastel_ref for t in june_refs}) == len(june_refs)\n    assert len({t.pastel_ref for t in june_receipts}) == len(june_receipts)\n\n    # A saved rule reference must never override the unique transaction sequence.\n    ref_override_a = Transaction(36, date(2026, 6, 3), Decimal("-10.00"), "PAYMENT", "REF OVERRIDE 7777", direction="PAYMENT")\n    ref_override_b = Transaction(37, date(2026, 6, 3), Decimal("-20.00"), "PAYMENT", "REF OVERRIDE 7777", direction="PAYMENT")\n    duplicate_ref_rule = Rule(36, "REF OVERRIDE", "SMART", "REF OVERRIDE 7777", "7100001", False, 0, pastel_ref="SAME", direction="PAYMENT")\n    apply_rules([ref_override_a, ref_override_b], [duplicate_ref_rule], 0)\n    assign_monthly_sequential_references([ref_override_a, ref_override_b])\n    assert [ref_override_a.pastel_ref, ref_override_b.pastel_ref] == ["P6-0001", "P6-0002"]\n\n'''
    s = replace_once(s, test_marker, tests + test_marker, 'monthly sequential reference tests')

    p.write_text(s, encoding='utf-8')
    print(f'Transformed {p} to v1.11.5 with monthly sequential Pastel references')


if __name__ == '__main__':
    main(sys.argv[1])
