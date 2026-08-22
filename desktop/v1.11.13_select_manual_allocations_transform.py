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

    s = replace_once(s, 'APP_VERSION = "1.11.12"', 'APP_VERSION = "1.11.13"', 'version')

    # Keep automatic and manual export selection as two separate explicit actions.
    s = replace_once(
        s,
        '        ttk.Button(actions2, text="Select Auto-Allocated", command=lambda d=direction: self.select_auto_allocated_export(d)).pack(side="left", padx=(12,3))\n',
        '        ttk.Button(actions2, text="Select Auto-Allocated", command=lambda d=direction: self.select_auto_allocated_export(d)).pack(side="left", padx=(12,3))\n        ttk.Button(actions2, text="Select Manual Allocations", command=lambda d=direction: self.select_manual_allocated_export(d)).pack(side="left", padx=3)\n',
        'main Select Manual Allocations button',
    )

    s = replace_once(
        s,
        '        ttk.Button(actions2, text="Select auto-allocated recurring", command=lambda d=direction: self.select_auto_allocated_export(d, True)).pack(side="left", padx=3)\n',
        '        ttk.Button(actions2, text="Select auto-allocated recurring", command=lambda d=direction: self.select_auto_allocated_export(d, True)).pack(side="left", padx=3)\n        ttk.Button(actions2, text="Select manual allocations", command=lambda d=direction: self.select_manual_allocated_export(d, True)).pack(side="left", padx=3)\n',
        'recurring Select manual allocations button',
    )

    old_tail = '''        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        scope = "recurring " if recurring_only else ""\n        self.status_var.set(f"Selected {count} automatically allocated {scope}{self._noun(direction, True)} for export; manual/corrected/unassigned rows were left unticked.")\n\n    def correct_auto_allocation_selected(self, direction: str, txn: Optional[Transaction] = None):\n'''

    new_tail = '''        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        scope = "recurring " if recurring_only else ""\n        self.status_var.set(f"Selected {count} automatically allocated {scope}{self._noun(direction, True)} for export; manual/corrected/unassigned rows were left unticked.")\n\n    def select_manual_allocated_export(self, direction: str, recurring_only: bool = False):\n        """Select allocated manual/corrected rows for export without mixing them with auto-allocation."""\n        count = 0\n        for t in self._list(direction):\n            if recurring_only and t.recurring_count < 2:\n                continue\n            selected = bool(t.manual_override and t.account and not t.ambiguous)\n            t.include = selected\n            if selected:\n                count += 1\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        scope = "recurring " if recurring_only else ""\n        self.status_var.set(f"Selected {count} manually allocated {scope}{self._noun(direction, True)} for export; automatic/unassigned/ambiguous rows were left unticked.")\n\n    def correct_auto_allocation_selected(self, direction: str, txn: Optional[Transaction] = None):\n'''
    s = replace_once(s, old_tail, new_tail, 'manual allocation selection method')

    # Add a focused regression test: manual allocated rows are selectable; automatic,
    # unassigned, and ambiguous rows are not part of the manual selection class.
    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.13: manual allocation selection classification.\n    manual_pick = Transaction(713, date(2026, 8, 22), Decimal("-100.00"), "DEBIT", "MANUAL PICK 713", direction="PAYMENT")\n    manual_pick.account = "7000001"\n    manual_pick.manual_override = True\n    assert manual_pick.manual_override and manual_pick.account and not manual_pick.ambiguous\n    auto_not_manual = Transaction(714, date(2026, 8, 22), Decimal("-100.00"), "DEBIT", "AUTO PICK 714", direction="PAYMENT")\n    auto_not_manual.account = "7000002"\n    auto_not_manual.auto_allocated = True\n    assert not auto_not_manual.manual_override\n    ambiguous_manual = Transaction(715, date(2026, 8, 22), Decimal("-100.00"), "DEBIT", "AMBIG PICK 715", direction="PAYMENT")\n    ambiguous_manual.account = "7000003"\n    ambiguous_manual.manual_override = True\n    ambiguous_manual.ambiguous = True\n    assert not (ambiguous_manual.manual_override and ambiguous_manual.account and not ambiguous_manual.ambiguous)\n\n'''
    s = replace_once(s, marker, tests + marker, 'manual allocation selection self-tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.13 with separate manual allocation selection")


if __name__ == "__main__":
    main(sys.argv[1])
