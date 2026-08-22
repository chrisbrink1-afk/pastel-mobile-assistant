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

    s = replace_once(s, 'APP_VERSION = "1.11.15"', 'APP_VERSION = "1.11.16"', 'version')

    # A rule saved from the Recurring screen is already locked to one exact
    # recurring identity. Apply it directly to those child rows instead of
    # sending them back through the broader global rule matcher. This prevents
    # the identity heading from showing a saved GL while its child rows remain
    # orange/unassigned.
    marker = '\n\ndef repeat_description_choices(txns: List["Transaction"]) -> List[str]:\n'
    helper = '''\n\ndef apply_saved_recurring_identity_rule(\n    txns: List["Transaction"], indices: List[int], identity_key: str, rule: "Rule", default_tax_type: int = 0\n) -> Tuple[int, int]:\n    \"\"\"Apply one saved identity rule to the exact recurring rows selected in the UI.\n\n    The rows are still identity-checked with smart_key before allocation. This is\n    intentionally narrower than global matching: the user explicitly saved the\n    rule from this recurring identity, so matching child rows should immediately\n    inherit its GL/VAT/description and become automatic allocations.\n    Returns (allocated_count, review_count).\n    \"\"\"\n    nk = normalize_text(identity_key)\n    allocated = 0\n    review = 0\n    for idx in indices:\n        if idx < 0 or idx >= len(txns):\n            continue\n        t = txns[idx]\n        if normalize_text(smart_key(t.details, t.txn_type)) != nk:\n            continue\n\n        t.manual_override = False\n        t.ambiguous = False\n        t.rule_id = rule.id\n        t.rule_name = rule.name\n        t.match_key = rule.pattern\n        t.description = (rule.description or \"\").strip()\n        t.vat = bool(rule.vat)\n        t.tax_type = int(rule.tax_type or default_tax_type or 0) if t.vat else 0\n        t.pastel_ref = (rule.pastel_ref or derive_pastel_reference(t.details, rule.pattern, t.row_no))[:8]\n\n        amount_branch = amount_rule_condition_active(rule, t.payment_amount)\n        if amount_branch and amount_rule_action(rule) == \"REVIEW\":\n            t.account = \"\"\n            t.auto_allocated = False\n            t.amount_condition_applied = True\n            t.status = f\"Amount review required • amount {rule.amount_operator} R {money(D(rule.amount_threshold))}\"\n            review += 1\n            continue\n\n        account, amount_branch = effective_rule_account(rule, t.payment_amount)\n        t.account = account\n        t.auto_allocated = bool(account)\n        t.amount_condition_applied = amount_branch\n        if account:\n            amount_note = \"\"\n            if amount_branch:\n                amount_note = f\" • amount {rule.amount_operator} R {money(D(rule.amount_threshold))}\"\n            t.status = f\"Auto-assigned{amount_note} • saved recurring identity rule\"\n            allocated += 1\n        else:\n            t.status = \"Unassigned • saved recurring identity rule has no GL account\"\n    return allocated, review\n'''
    s = replace_once(s, marker, helper + marker, 'saved recurring identity direct-apply helper')

    old = '''        self.wait_window(dlg)\n        if dlg.result:\n            protected = getattr(dlg, "applied_review_transaction_ids", set())\n            for i in idxs:\n                if id(txns[i]) not in protected:\n                    txns[i].manual_override = False\n            self.reapply_rules(silent=True)\n            self.status_var.set(f"Saved identity rule for {key}. Qualifying amount exceptions can be allocated individually inside the rule window.")\n'''
    new = '''        self.wait_window(dlg)\n        if dlg.result:\n            protected = getattr(dlg, "applied_review_transaction_ids", set())\n            saved_rule = self._specific_rule_for_key(key, direction)\n            if not saved_rule:\n                # Defensive fallback: the dialog reported success but no exact\n                # identity rule can be read back. Reapply normally and surface a\n                # clear status instead of silently leaving orange child rows.\n                for i in idxs:\n                    if id(txns[i]) not in protected:\n                        txns[i].manual_override = False\n                self.reapply_rules(silent=True)\n                self.status_var.set(f"Saved identity rule for {key}; rule was reapplied through normal matching.")\n                return\n            default_tax = int(self.store.get_setting("vat_tax_type", "0") or 0)\n            direct_idxs = [i for i in idxs if id(txns[i]) not in protected]\n            allocated, review = apply_saved_recurring_identity_rule(txns, direct_idxs, key, saved_rule, default_tax)\n            self.refresh_transaction_tree(direction)\n            self.refresh_recurring_tree(direction)\n            self.refresh_rules()\n            if review:\n                self.status_var.set(f"Saved identity rule for {key}. {allocated} transaction(s) allocated automatically and {review} sent to amount review. Any allocations made inside the rule window were preserved.")\n            else:\n                self.status_var.set(f"Saved identity rule for {key}. {allocated} matching transaction(s) are now automatic allocations and no longer unassigned.")\n'''
    s = replace_once(s, old, new, 'recurring identity save applies child rows directly')

    # Regression test for the exact bug shown by STOP ORDER HANDLING FEE: the
    # identity rule exists, but child rows must not remain orange/unassigned.
    test_marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.16: saving a recurring identity rule immediately allocates its child rows.\n    identity_rows = [\n        Transaction(916, date(2026, 6, 1), Decimal("-50.00"), "DEBIT", "STOP ORDER HANDLING FEE", direction="PAYMENT"),\n        Transaction(917, date(2026, 6, 25), Decimal("-50.00"), "DEBIT", "STOP ORDER HANDLING FEE", direction="PAYMENT"),\n    ]\n    identity_key = smart_key(identity_rows[0].details, identity_rows[0].txn_type)\n    identity_rule = Rule(916, "STOP ORDER FEE", "SMART", identity_key, "3200000", True, 15, direction="PAYMENT", description="FEE")\n    got_allocated, got_review = apply_saved_recurring_identity_rule(identity_rows, [0, 1], identity_key, identity_rule, 15)\n    assert got_allocated == 2 and got_review == 0\n    assert all(t.account == "3200000" and t.auto_allocated and not t.manual_override and not t.ambiguous for t in identity_rows)\n    assert all(t.vat and t.tax_type == 15 and t.description == "FEE" for t in identity_rows)\n\n'''
    s = replace_once(s, test_marker, tests + test_marker, 'recurring identity direct-apply self-test')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.16 with immediate saved recurring identity allocation")


if __name__ == "__main__":
    main(sys.argv[1])
