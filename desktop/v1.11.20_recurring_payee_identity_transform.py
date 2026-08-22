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

    s = replace_once(s, 'APP_VERSION = "1.11.19"', 'APP_VERSION = "1.11.20"', 'version')

    # Recurrence grouping is deliberately separate from rule matching.  Bank-
    # generated references and petty-cash wording can vary while the payee is
    # still the same recurring person.  Only verified aliases belong here so a
    # recurrence improvement can never loosen automatic GL allocation safety.
    marker = '\n\ndef smart_match(pattern: str, details: str, txn_type: str = "") -> bool:\n'
    helper = '''\n\ndef recurring_identity_key(details: str, txn_type: str = "") -> str:\n    \"\"\"Return the stable identity used only for recurrence grouping/history.\n\n    This is intentionally separate from smart_key/rule_matches.  It may collapse\n    verified bank-description variants for the same payee without making any\n    automatic-allocation rule broader.\n    \"\"\"\n    combined = normalize_text(f\"{details} {txn_type}\")\n\n    # Verified from the supplied Standard Bank statement: Mary Hartslief appears\n    # as plain name, PCASH/PETTY CASH variants and Immediate Payment rows with a\n    # changing bank-generated leading reference.  All are the same recurring\n    # payee for display/history purposes.\n    if re.search(r\"\\bMARY\\s+HARTSLIEF\\b\", combined):\n        return \"MARY HARTSLIEF\"\n\n    return smart_key(details, txn_type)\n'''
    s = replace_once(s, marker, helper + marker, 'recurring identity helper')

    s = replace_once(
        s,
        '    keys = {smart_key(t.details, t.txn_type) for t in txns if t.include and t.recurring_count >= 2}\n',
        '    keys = {recurring_identity_key(t.details, t.txn_type) for t in txns if t.include and t.recurring_count >= 2}\n',
        'repeat choices use recurrence identity',
    )

    s = replace_once(
        s,
        '''        for t in txns:\n            key = smart_key(t.details, t.txn_type)\n            direction = (t.direction or "PAYMENT").upper()\n            key_pairs.append((direction, key))\n            sig = self._txn_signature(t)\n            self.conn.execute(\n                "INSERT OR IGNORE INTO transaction_history(signature,txn_date,match_key,details,amount,source_name,direction) VALUES(?,?,?,?,?,?,?)",\n                (sig, t.txn_date.isoformat(), key, t.details, money(t.payment_amount), Path(t.source).name if t.source else "", direction)\n            )\n''',
        '''        for t in txns:\n            key = recurring_identity_key(t.details, t.txn_type)\n            direction = (t.direction or "PAYMENT").upper()\n            key_pairs.append((direction, key))\n            sig = self._txn_signature(t)\n            self.conn.execute(\n                \"\"\"INSERT INTO transaction_history(signature,txn_date,match_key,details,amount,source_name,direction) VALUES(?,?,?,?,?,?,?)\n                ON CONFLICT(signature) DO UPDATE SET\n                    txn_date=excluded.txn_date, match_key=excluded.match_key, details=excluded.details,\n                    amount=excluded.amount, source_name=excluded.source_name, direction=excluded.direction\"\"\",\n                (sig, t.txn_date.isoformat(), key, t.details, money(t.payment_amount), Path(t.source).name if t.source else "", direction)\n            )\n''',
        'history stores updated recurrence identity',
    )

    s = replace_once(
        s,
        '''        for t in txns:\n            direction = (t.direction or "PAYMENT").upper()\n            key = smart_key(t.details, t.txn_type)\n            pair = (direction, key)\n''',
        '''        for t in txns:\n            direction = (t.direction or "PAYMENT").upper()\n            key = recurring_identity_key(t.details, t.txn_type)\n            pair = (direction, key)\n''',
        'recurring counts use recurrence identity',
    )

    s = replace_once(
        s,
        '            count = max((t.recurring_count for t in txns if smart_key(t.details, t.txn_type) == key), default=2)\n',
        '            count = max((t.recurring_count for t in txns if recurring_identity_key(t.details, t.txn_type) == key), default=2)\n',
        'repeat dropdown count uses recurrence identity',
    )

    s = replace_once(
        s,
        '            current_repeat_key = smart_key(t.details, t.txn_type)\n',
        '            current_repeat_key = recurring_identity_key(t.details, t.txn_type)\n',
        'transaction repeat filter uses recurrence identity',
    )

    s = replace_once(
        s,
        '        recurring_groups = len({smart_key(t.details, t.txn_type) for t in txns if t.recurring_count >= 2})\n',
        '        recurring_groups = len({recurring_identity_key(t.details, t.txn_type) for t in txns if t.recurring_count >= 2})\n',
        'summary recurring groups use recurrence identity',
    )

    s = replace_once(
        s,
        '''        for idx, t in enumerate(txns):\n            if t.recurring_count < 2:\n                continue\n            key = smart_key(t.details, t.txn_type)\n            if not key:\n''',
        '''        for idx, t in enumerate(txns):\n            if t.recurring_count < 2:\n                continue\n            key = recurring_identity_key(t.details, t.txn_type)\n            if not key:\n''',
        'recurring tree grouping uses recurrence identity',
    )

    s = replace_once(
        s,
        '''            t = self._list(direction)[idx]\n            return smart_key(t.details, t.txn_type)\n''',
        '''            t = self._list(direction)[idx]\n            return recurring_identity_key(t.details, t.txn_type)\n''',
        'selected recurring transaction returns recurrence identity',
    )

    s = replace_once(
        s,
        '        if normalize_text(smart_key(t.details, t.txn_type)) != nk:\n',
        '        if normalize_text(recurring_identity_key(t.details, t.txn_type)) != nk:\n',
        'saved recurring identity direct apply uses recurrence identity',
    )

    # Autosaved v1.11.19 sessions may carry old recurring_count values.  Re-run
    # recurrence/history bookkeeping immediately after deserializing so an
    # upgrade takes effect without forcing the user to reload the statement.
    s = replace_once(
        s,
        '''            self.current_file = str(data.get("current_file") or "")\n            self.parser_name = str(data.get("parser_name") or "")\n\n            saved_search = data.get("search") if isinstance(data.get("search"), dict) else {}\n''',
        '''            self.current_file = str(data.get("current_file") or "")\n            self.parser_name = str(data.get("parser_name") or "")\n            self.store.remember_transactions(self.txns)\n            self.store.remember_transactions(self.receipts)\n\n            saved_search = data.get("search") if isinstance(data.get("search"), dict) else {}\n''',
        'recalculate recurrence after session restore',
    )

    test_marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.20: verified Mary Hartslief bank variants are one recurring payee.\n    mary_rows = [\n        Transaction(58, date(2026, 6, 12), Decimal("-4000.00"), "IB PAYMENT TO", "MARY HARTSLIEF PCASH", direction="PAYMENT"),\n        Transaction(114, date(2026, 6, 25), Decimal("-21515.63"), "IB PAYMENT TO", "MARY HARTSLIEF", direction="PAYMENT"),\n        Transaction(133, date(2026, 6, 26), Decimal("-2000.00"), "IMMEDIATE PAYMENT", "299478576 MARY HARTSLIEF", direction="PAYMENT"),\n        Transaction(200, date(2026, 7, 6), Decimal("-2000.00"), "IMMEDIATE PAYMENT", "300309850 MARY HARTSLIEF", direction="PAYMENT"),\n        Transaction(225, date(2026, 7, 13), Decimal("-4000.00"), "IB PAYMENT TO", "MARY HARTSLIEF PETTY CASH", direction="PAYMENT"),\n        Transaction(280, date(2026, 7, 24), Decimal("-20515.63"), "IMMEDIATE PAYMENT", "301673371 MARY HARTSLIEF", direction="PAYMENT"),\n    ]\n    # The stricter rule/matching key remains untouched and still sees variants;\n    # only recurrence grouping collapses the verified payee aliases.\n    assert len({smart_key(t.details, t.txn_type) for t in mary_rows}) >= 4\n    assert {recurring_identity_key(t.details, t.txn_type) for t in mary_rows} == {"MARY HARTSLIEF"}\n    with tempfile.TemporaryDirectory() as td:\n        mary_store = Store(Path(td) / "mary.db")\n        mary_store.remember_transactions(mary_rows)\n        assert all(t.recurring_count == 6 for t in mary_rows)\n        assert len(mary_store.recurring_summary("PAYMENT")) == 1\n        mary_store.conn.close()\n\n    # Grouping must not alter individual allocations: different Mary rows can\n    # still carry different manual GLs while appearing under one recurring payee.\n    mary_rows[0].account = "7100001"\n    mary_rows[0].manual_override = True\n    mary_rows[1].account = "7200002"\n    mary_rows[1].manual_override = True\n    assert mary_rows[0].account != mary_rows[1].account\n\n'''
    # tempfile is already imported in self_test before this marker in the release chain.
    s = replace_once(s, test_marker, tests + test_marker, 'Mary recurring identity self-tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.20 with safe recurring payee identity grouping")


if __name__ == "__main__":
    main(sys.argv[1])
