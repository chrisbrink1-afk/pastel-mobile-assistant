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

    s = replace_once(s, 'APP_VERSION = "1.11.11"', 'APP_VERSION = "1.11.12"', 'version')

    # When a correction updates the SAVED rule, the row should be treated exactly
    # like any other saved-rule allocation. Previously reapply_rules() correctly
    # made it automatic, but execution then fell through and immediately changed
    # it back to manual_override=True / auto_allocated=False.
    old = '''            self.store.save_rule(rule)\n            t.manual_override = False\n            self.reapply_rules(silent=True)\n        t.account = account\n        t.description = description\n        t.vat = vat\n        t.tax_type = tax_type\n        t.pastel_ref = pastel_ref\n        t.rule_id = rule.id if rule else t.rule_id\n        t.rule_name = f"Corrected • {rule.name}" if rule else "Corrected"\n        t.status = "Corrected allocation • saved rule updated" if (update_rule and rule) else "Corrected allocation • this statement only"\n        t.manual_override = True\n        t.auto_allocated = False\n        t.ambiguous = False\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        self.status_var.set("Correction saved. This row is marked Corrected and is excluded by Select Auto-Allocated until you reset it to the saved rule.")\n'''

    new = '''            self.store.save_rule(rule)\n            t.manual_override = False\n            self.reapply_rules(silent=True)\n            self.refresh_transaction_tree(direction)\n            self.refresh_recurring_tree(direction)\n            self.status_var.set("Saved rule updated and reapplied. Matching transactions are automatic allocations and will be included by Select Auto-Allocated.")\n            return\n\n        # A correction that is explicitly for this statement only remains a\n        # manual/corrected row and must not be selected by Select Auto-Allocated.\n        t.account = account\n        t.description = description\n        t.vat = vat\n        t.tax_type = tax_type\n        t.pastel_ref = pastel_ref\n        t.rule_id = rule.id if rule else t.rule_id\n        t.rule_name = f"Corrected • {rule.name}" if rule else "Corrected"\n        t.status = "Corrected allocation • this statement only"\n        t.manual_override = True\n        t.auto_allocated = False\n        t.ambiguous = False\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        self.status_var.set("Correction saved for this statement only. It remains excluded by Select Auto-Allocated.")\n'''

    s = replace_once(s, old, new, 'saved rule correction remains automatic')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.12: saved-rule edits remain automatic allocations")


if __name__ == "__main__":
    main(sys.argv[1])
