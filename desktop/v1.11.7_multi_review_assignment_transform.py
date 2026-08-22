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
    s = replace_once(s, 'APP_VERSION = "1.11.6"', 'APP_VERSION = "1.11.7"', 'version')

    helper = '''\n\ndef apply_review_assignment(txns: List["Transaction"], account: str, description: str = "", vat: bool = False, tax_type: int = 0) -> int:\n    \"\"\"Apply one manual allocation to only the supplied amount-review rows.\n\n    The caller chooses the exact rows (one or many). Other qualifying amount\n    review transactions are deliberately untouched. A blank description keeps\n    each selected transaction's existing description.\n    \"\"\"\n    account = (account or "").strip()\n    description = (description or "").strip()\n    if not account:\n        return 0\n    count = 0\n    for t in txns:\n        if not (t.status or "").startswith("Amount review required"):\n            continue\n        t.account = account\n        if description:\n            t.description = description\n        t.vat = bool(vat)\n        t.tax_type = int(tax_type or 0) if t.vat else 0\n        t.rule_id = None\n        t.rule_name = "Manual amount review"\n        t.status = "Amount review assigned manually"\n        t.manual_override = True\n        t.ambiguous = False\n        t.auto_allocated = False\n        t.amount_condition_applied = True\n        count += 1\n    return count\n'''
    s = replace_once(s, '\n\nclass Store:\n', helper + '\n\nclass Store:\n', 'review assignment helper')

    s = replace_once(
        s,
        '''        self.txns: List[Transaction] = []\n        self.receipts: List[Transaction] = []\n        self.current_file = ""\n''',
        '''        self.txns: List[Transaction] = []\n        self.receipts: List[Transaction] = []\n        self.review_selection: Dict[str, set] = {d: set() for d in self.DIRECTIONS}\n        self.current_file = ""\n''',
        'review selection state',
    )

    s = replace_once(
        s,
        '''        ttk.Button(actions, text="Assign once", command=lambda d=direction: self.manual_assign_selected(d)).pack(side="left", padx=3)\n''',
        '''        ttk.Button(actions, text="Assign once", command=lambda d=direction: self.manual_assign_selected(d)).pack(side="left", padx=3)\n        ttk.Button(actions, text="Assign selected review items", command=lambda d=direction: self.assign_selected_review_items(d)).pack(side="left", padx=(10,3))\n''',
        'review assign button',
    )

    s = replace_once(
        s,
        '''        ttk.Label(summary, text="☐ / ☑ controls export", foreground="#555555").pack(side="right")\n\n        cols = ("inc", "date", "details", "description", "amount", "key", "repeat", "account", "vat", "rule", "status")\n''',
        '''        ttk.Label(summary, text="Export ☑ controls Pastel export • Allocate ☑ selects one or many Amount Review rows", foreground="#555555").pack(side="right")\n\n        cols = ("inc", "review", "date", "details", "description", "amount", "key", "repeat", "account", "vat", "rule", "status")\n''',
        'review checkbox column tuple',
    )

    s = replace_once(
        s,
        '''            "inc": "Export", "date": "Date", "details": "Bank description / reference", "description": "Pastel description", "amount": "Current CSV amount",\n            "key": "Matched name + number", "repeat": "Recurring", "account": "GL account", "vat": "VAT", "rule": "Rule", "status": "Status"\n        }\n        widths = {"inc": 58, "date": 88, "details": 280, "description": 170, "amount": 105, "key": 155, "repeat": 70, "account": 100, "vat": 55, "rule": 145, "status": 185}\n''',
        '''            "inc": "Export", "review": "Allocate", "date": "Date", "details": "Bank description / reference", "description": "Pastel description", "amount": "Current CSV amount",\n            "key": "Matched name + number", "repeat": "Recurring", "account": "GL account", "vat": "VAT", "rule": "Rule", "status": "Status"\n        }\n        widths = {"inc": 58, "review": 64, "date": 88, "details": 280, "description": 170, "amount": 105, "key": 155, "repeat": 70, "account": 100, "vat": 55, "rule": 145, "status": 185}\n''',
        'review checkbox labels widths',
    )

    s = replace_once(
        s,
        '''            tree.column(c, width=widths[c], anchor="center" if c == "inc" else ("e" if c == "amount" else "w"), stretch=(c in {"details", "description", "rule"}))\n''',
        '''            tree.column(c, width=widths[c], anchor="center" if c in {"inc", "review"} else ("e" if c == "amount" else "w"), stretch=(c in {"details", "description", "rule"}))\n''',
        'review checkbox column alignment',
    )

    s = replace_once(
        s,
        '''    def refresh_transaction_tree(self, direction: str):\n        tree = self.trees.get(direction)\n        if not tree:\n            return\n        txns = self._list(direction)\n        q = normalize_text(self.search_vars[direction].get())\n''',
        '''    def refresh_transaction_tree(self, direction: str):\n        tree = self.trees.get(direction)\n        if not tree:\n            return\n        txns = self._list(direction)\n        reviewable = {i for i, t in enumerate(txns) if (t.status or "").startswith("Amount review required")}\n        self.review_selection[direction].intersection_update(reviewable)\n        q = normalize_text(self.search_vars[direction].get())\n''',
        'review selection cleanup',
    )

    s = replace_once(
        s,
        '''            vals = ("☑" if t.include else "☐", t.txn_date.strftime("%d/%m/%Y"), t.details, t.description, f"R {money(t.payment_amount)}", t.match_key, repeat, t.account, "VAT" if t.vat else "No", t.rule_name, t.status)\n''',
        '''            review_tick = "☑" if idx in self.review_selection[direction] else ("☐" if (t.status or "").startswith("Amount review required") else "")\n            vals = ("☑" if t.include else "☐", review_tick, t.txn_date.strftime("%d/%m/%Y"), t.details, t.description, f"R {money(t.payment_amount)}", t.match_key, repeat, t.account, "VAT" if t.vat else "No", t.rule_name, t.status)\n''',
        'review checkbox values',
    )

    old_click = '''    def _tree_click(self, event, direction: str):\n        tree = self.trees[direction]\n        if tree.identify_region(event.x, event.y) == "cell" and tree.identify_column(event.x) == "#1":\n            iid = tree.identify_row(event.y)\n            if iid:\n                txns = self._list(direction)\n                try:\n                    idx = int(iid); txns[idx].include = not txns[idx].include\n                except Exception:\n                    return\n                self.refresh_transaction_tree(direction)\n                tree.selection_set(iid)\n                return "break"\n\n    def _tree_double_click(self, event, direction: str):\n        if self.trees[direction].identify_column(event.x) != "#1":\n            self.assign_rule_selected(direction)\n'''
    new_click = '''    def _tree_click(self, event, direction: str):\n        tree = self.trees[direction]\n        if tree.identify_region(event.x, event.y) != "cell":\n            return\n        col = tree.identify_column(event.x)\n        iid = tree.identify_row(event.y)\n        if not iid:\n            return\n        txns = self._list(direction)\n        try:\n            idx = int(iid)\n        except Exception:\n            return\n        if col == "#1":\n            txns[idx].include = not txns[idx].include\n            self.refresh_transaction_tree(direction)\n            tree.selection_set(iid)\n            return "break"\n        if col == "#2":\n            t = txns[idx]\n            if not (t.status or "").startswith("Amount review required"):\n                return "break"\n            if idx in self.review_selection[direction]:\n                self.review_selection[direction].remove(idx)\n            else:\n                self.review_selection[direction].add(idx)\n            self.refresh_transaction_tree(direction)\n            tree.selection_set(iid)\n            return "break"\n\n    def _tree_double_click(self, event, direction: str):\n        if self.trees[direction].identify_column(event.x) not in {"#1", "#2"}:\n            self.assign_rule_selected(direction)\n'''
    s = replace_once(s, old_click, new_click, 'review checkbox click handling')

    dialog = '''\n\nclass MultiReviewAssignDialog(tk.Toplevel):\n    def __init__(self, parent, txns: List[Transaction], default_tax_type: str, known_accounts: Optional[List[str]] = None):\n        super().__init__(parent)\n        self.result = None\n        self.txns = txns\n        count = len(txns)\n        noun = "receipt" if txns and (txns[0].direction or "PAYMENT").upper() == "RECEIPT" else "payment"\n        self.title(f"Assign {count} selected {noun}{'' if count == 1 else 's'}")\n        self.transient(parent); self.grab_set(); self.resizable(False, False)\n        account = tk.StringVar(value="")\n        descriptions = {(t.description or "").strip() for t in txns}\n        description = tk.StringVar(value=next(iter(descriptions)) if len(descriptions) == 1 else "")\n        vat_values = {bool(t.vat) for t in txns}\n        vat = tk.BooleanVar(value=next(iter(vat_values)) if len(vat_values) == 1 else False)\n        tax_values = {int(t.tax_type or 0) for t in txns if t.vat}\n        initial_tax = str(next(iter(tax_values))) if len(tax_values) == 1 else str(default_tax_type or "")\n        tax = tk.StringVar(value=initial_tax)\n        total = sum((t.payment_amount for t in txns), Decimal("0.00"))\n        f = ttk.Frame(self, padding=14); f.grid(sticky="nsew")\n        ttk.Label(f, text=f"{count} Amount Review {noun}{'' if count == 1 else 's'} selected • Total R {money(total)}", font=("Segoe UI",10,"bold")).grid(row=0,column=0,columnspan=2,sticky="w")\n        preview = "\\n".join(f"{t.txn_date:%d/%m/%Y}  R {money(t.payment_amount)}  {t.details[:55]}" for t in txns[:6])\n        if count > 6:\n            preview += f"\\n… plus {count - 6} more selected rows"\n        ttk.Label(f, text=preview, wraplength=620).grid(row=1,column=0,columnspan=2,sticky="w",pady=(4,10))\n        ttk.Label(f,text="GL account for selected rows").grid(row=2,column=0,sticky="w",pady=4)\n        ttk.Combobox(f,textvariable=account,values=known_accounts or [],width=40).grid(row=2,column=1,pady=4)\n        ttk.Label(f,text="Pastel description (optional)").grid(row=3,column=0,sticky="w",pady=4)\n        ttk.Entry(f,textvariable=description,width=43).grid(row=3,column=1,pady=4)\n        ttk.Label(f,text="Leave description blank to keep each selected row's existing description.",foreground="#555555",wraplength=560).grid(row=4,column=0,columnspan=2,sticky="w")\n        vatframe=ttk.Frame(f); vatframe.grid(row=5,column=0,columnspan=2,sticky="w",pady=8)\n        ttk.Checkbutton(vatframe,text="VAT",variable=vat).pack(side="left")\n        ttk.Label(vatframe,text="Tax type").pack(side="left",padx=(18,5)); ttk.Entry(vatframe,textvariable=tax,width=6).pack(side="left")\n        ttk.Label(f,text="Only the checked Allocate rows will be changed. Other Amount Review transactions remain untouched for separate allocation.",foreground="#555555",wraplength=600).grid(row=6,column=0,columnspan=2,sticky="w",pady=(4,10))\n        b=ttk.Frame(f); b.grid(row=7,column=0,columnspan=2,sticky="e")\n        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=(8,0))\n        ttk.Button(b,text="Assign selected",command=lambda:self._save(account,description,vat,tax)).pack(side="right")\n        self.wait_visibility(); self.focus_force()\n\n    def _save(self, account, description, vat, tax):\n        acc = account.get().strip()\n        if not acc:\n            messagebox.showerror(APP_NAME,"GL account is required.",parent=self); return\n        if len(acc) > 7:\n            if not messagebox.askyesno(APP_NAME,"This GL account is longer than Sage's published 7-character layout. Use it anyway? Export validation will still block invalid accounts.",parent=self):\n                return\n        try:\n            tt = int(tax.get() or 0) if vat.get() else 0\n        except ValueError:\n            messagebox.showerror(APP_NAME,"Tax type must be a whole number.",parent=self); return\n        self.result = (acc, description.get().strip(), bool(vat.get()), tt)\n        self.destroy()\n'''
    s = replace_once(s, '\n\nclass CorrectionDialog(tk.Toplevel):\n', dialog + '\n\nclass CorrectionDialog(tk.Toplevel):\n', 'multi review dialog')

    method_marker = '''    def manual_assign_selected(self, direction: str):\n'''
    method = '''    def assign_selected_review_items(self, direction: str):\n        txns = self._list(direction)\n        idxs = sorted(self.review_selection[direction])\n        selected = [txns[i] for i in idxs if 0 <= i < len(txns) and (txns[i].status or "").startswith("Amount review required")]\n        if not selected:\n            messagebox.showinfo(APP_NAME, f"Tick one or more Allocate boxes on Amount Review {self._noun(direction, True)} first.")\n            return\n        dlg = MultiReviewAssignDialog(self, selected, self.store.get_setting("vat_tax_type", ""), self.store.known_accounts())\n        self.wait_window(dlg)\n        if not dlg.result:\n            return\n        account, description, vat, tax_type = dlg.result\n        count = apply_review_assignment(selected, account, description, vat, tax_type)\n        for i in idxs:\n            self.review_selection[direction].discard(i)\n        assign_monthly_sequential_references(self.txns + self.receipts)\n        self.refresh_transaction_tree(direction)\n        self.refresh_recurring_tree(direction)\n        self.status_var.set(f"Assigned {count} selected Amount Review {self._noun(direction, True)} to GL {account}. Other review rows were left unchanged.")\n\n'''
    s = replace_once(s, method_marker, method + method_marker, 'multi review assignment method')

    s = replace_once(
        s,
        '''        self.current_file = p; self.parser_name = parser; self.txns = payments; self.receipts = receipts\n        self.store.set_setting("last_folder", str(Path(p).parent))\n''',
        '''        self.current_file = p; self.parser_name = parser; self.txns = payments; self.receipts = receipts\n        for d in self.DIRECTIONS:\n            self.review_selection[d].clear()\n        self.store.set_setting("last_folder", str(Path(p).parent))\n''',
        'clear review selections on load',
    )

    test_marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.7: one or many amount-review rows can be assigned together, without changing unselected review rows.\n    petrol_a = Transaction(170, date(2026, 6, 1), Decimal("-100.00"), "DEBIT", "CARD SPEND A", direction="PAYMENT", status="Amount review required • amount < R 500.00")\n    petrol_b = Transaction(171, date(2026, 6, 1), Decimal("-120.00"), "DEBIT", "CARD SPEND B", direction="PAYMENT", status="Amount review required • amount < R 500.00")\n    petrol_c = Transaction(172, date(2026, 6, 1), Decimal("-140.00"), "DEBIT", "CARD SPEND C", direction="PAYMENT", status="Amount review required • amount < R 500.00")\n    survey = Transaction(173, date(2026, 6, 1), Decimal("-160.00"), "DEBIT", "CARD SPEND D", direction="PAYMENT", status="Amount review required • amount < R 500.00")\n    assert apply_review_assignment([petrol_a, petrol_b, petrol_c], "PETROL", "Petrol", False, 0) == 3\n    assert [petrol_a.account, petrol_b.account, petrol_c.account] == ["PETROL", "PETROL", "PETROL"]\n    assert survey.account == "" and survey.status.startswith("Amount review required")\n    assert apply_review_assignment([survey], "SURVEY", "Survey", False, 0) == 1\n    assert survey.account == "SURVEY" and survey.description == "Survey"\n\n'''
    s = replace_once(s, test_marker, tests + test_marker, 'multi review assignment tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.7 with checkbox multi-select Amount Review assignment")


if __name__ == "__main__":
    main(sys.argv[1])
