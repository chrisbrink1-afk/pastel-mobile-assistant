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
    old = '''    def assign_selected_review_items(self, direction: str):\n        txns = self._list(direction)\n        idxs = sorted(self.review_selection[direction])\n        selected = [txns[i] for i in idxs if 0 <= i < len(txns) and (txns[i].status or "").startswith("Amount review required")]\n        if not selected:\n            messagebox.showinfo(APP_NAME, f"Tick one or more Allocate boxes on Amount Review {self._noun(direction, True)} first.")\n            return\n        dlg = MultiReviewAssignDialog(self, selected, self.store.get_setting("vat_tax_type", ""), self.store.known_accounts())\n        self.wait_window(dlg)\n        if not dlg.result:\n            return\n        account, description, vat, tax_type = dlg.result\n        count = apply_review_assignment(selected, account, description, vat, tax_type)\n        for i in idxs:\n            self.review_selection[direction].discard(i)\n        assign_monthly_sequential_references(self.txns + self.receipts)\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        self.status_var.set(f"Assigned {count} selected Amount Review {self._noun(direction, True)} to GL {account}. Other review rows were left unchanged.")\n\n'''
    s = replace_once(s, old, '', 'remove obsolete main review assignment method')
    p.write_text(s, encoding='utf-8')
    print(f'Removed obsolete v1.11.7 main-screen review method from {p}')


if __name__ == '__main__':
    main(sys.argv[1])
