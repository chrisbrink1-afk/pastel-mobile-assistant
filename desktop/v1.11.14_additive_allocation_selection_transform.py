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

    s = replace_once(s, 'APP_VERSION = "1.11.13"', 'APP_VERSION = "1.11.14"', 'version')

    old_auto = '''    def select_auto_allocated_export(self, direction: str, recurring_only: bool = False):\n        count = 0\n        for t in self._list(direction):\n            if recurring_only and t.recurring_count < 2:\n                continue\n            selected = bool(t.auto_allocated and t.account and not t.ambiguous)\n            t.include = selected\n            if selected:\n                count += 1\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        scope = "recurring " if recurring_only else ""\n        self.status_var.set(f"Selected {count} automatically allocated {scope}{self._noun(direction, True)} for export; manual/corrected/unassigned rows were left unticked.")\n'''

    new_auto = '''    def select_auto_allocated_export(self, direction: str, recurring_only: bool = False):\n        # Add matching automatic allocations to the current export selection.\n        # Do not clear manual allocations (or any other rows) that are already ticked.\n        matched = 0\n        added = 0\n        for t in self._list(direction):\n            if recurring_only and t.recurring_count < 2:\n                continue\n            selected = bool(t.auto_allocated and t.account and not t.ambiguous)\n            if selected:\n                matched += 1\n                if not t.include:\n                    added += 1\n                t.include = True\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        scope = "recurring " if recurring_only else ""\n        self.status_var.set(f"Added {added} automatically allocated {scope}{self._noun(direction, True)} to the export selection ({matched} matching). Existing manual selections were preserved.")\n'''
    s = replace_once(s, old_auto, new_auto, 'make auto allocation selection additive')

    old_manual = '''    def select_manual_allocated_export(self, direction: str, recurring_only: bool = False):\n        """Select allocated manual/corrected rows for export without mixing them with auto-allocation."""\n        count = 0\n        for t in self._list(direction):\n            if recurring_only and t.recurring_count < 2:\n                continue\n            selected = bool(t.manual_override and t.account and not t.ambiguous)\n            t.include = selected\n            if selected:\n                count += 1\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        scope = "recurring " if recurring_only else ""\n        self.status_var.set(f"Selected {count} manually allocated {scope}{self._noun(direction, True)} for export; automatic/unassigned/ambiguous rows were left unticked.")\n'''

    new_manual = '''    def select_manual_allocated_export(self, direction: str, recurring_only: bool = False):\n        """Add allocated manual/corrected rows to the existing export selection."""\n        matched = 0\n        added = 0\n        for t in self._list(direction):\n            if recurring_only and t.recurring_count < 2:\n                continue\n            selected = bool(t.manual_override and t.account and not t.ambiguous)\n            if selected:\n                matched += 1\n                if not t.include:\n                    added += 1\n                t.include = True\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        scope = "recurring " if recurring_only else ""\n        self.status_var.set(f"Added {added} manually allocated {scope}{self._noun(direction, True)} to the export selection ({matched} matching). Existing automatic selections were preserved.")\n'''
    s = replace_once(s, old_manual, new_manual, 'make manual allocation selection additive')

    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.14: auto and manual selection are additive rather than exclusive.\n    additive_auto = Transaction(814, date(2026, 8, 22), Decimal("-100.00"), "DEBIT", "ADDITIVE AUTO 814", direction="PAYMENT")\n    additive_auto.account = "7000014"\n    additive_auto.auto_allocated = True\n    additive_auto.include = True\n    additive_manual = Transaction(815, date(2026, 8, 22), Decimal("-100.00"), "DEBIT", "ADDITIVE MANUAL 815", direction="PAYMENT")\n    additive_manual.account = "7000015"\n    additive_manual.manual_override = True\n    additive_manual.include = False\n    # Selecting manual after auto must preserve the already-selected auto row.\n    if additive_manual.manual_override and additive_manual.account and not additive_manual.ambiguous:\n        additive_manual.include = True\n    assert additive_auto.include and additive_manual.include\n    # Selecting auto after manual must likewise preserve the manual row.\n    additive_auto.include = False\n    additive_manual.include = True\n    if additive_auto.auto_allocated and additive_auto.account and not additive_auto.ambiguous:\n        additive_auto.include = True\n    assert additive_auto.include and additive_manual.include\n\n'''
    s = replace_once(s, marker, tests + marker, 'additive allocation selection self-tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.14 with additive auto/manual allocation selection")


if __name__ == "__main__":
    main(sys.argv[1])
