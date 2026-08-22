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
    s = replace_once(s, 'APP_VERSION = "1.11.7"', 'APP_VERSION = "1.11.8"', 'version')

    # v1.11.8 corrects the v1.11.7 placement: the allocation selector belongs
    # inside the amount-rule dialog, not as an extra column on the main table.
    s = replace_once(
        s,
        '''        ttk.Button(actions, text="Assign once", command=lambda d=direction: self.manual_assign_selected(d)).pack(side="left", padx=3)\n        ttk.Button(actions, text="Assign selected review items", command=lambda d=direction: self.assign_selected_review_items(d)).pack(side="left", padx=(10,3))\n''',
        '''        ttk.Button(actions, text="Assign once", command=lambda d=direction: self.manual_assign_selected(d)).pack(side="left", padx=3)\n''',
        'remove misplaced main review button',
    )

    s = replace_once(
        s,
        '''        ttk.Label(summary, text="Export ☑ controls Pastel export • Allocate ☑ selects one or many Amount Review rows", foreground="#555555").pack(side="right")\n\n        cols = ("inc", "review", "date", "details", "description", "amount", "key", "repeat", "account", "vat", "rule", "status")\n''',
        '''        ttk.Label(summary, text="☐ / ☑ controls export", foreground="#555555").pack(side="right")\n\n        cols = ("inc", "date", "details", "description", "amount", "key", "repeat", "account", "vat", "rule", "status")\n''',
        'restore main table columns',
    )

    s = replace_once(
        s,
        '''            "inc": "Export", "review": "Allocate", "date": "Date", "details": "Bank description / reference", "description": "Pastel description", "amount": "Current CSV amount",\n            "key": "Matched name + number", "repeat": "Recurring", "account": "GL account", "vat": "VAT", "rule": "Rule", "status": "Status"\n        }\n        widths = {"inc": 58, "review": 64, "date": 88, "details": 280, "description": 170, "amount": 105, "key": 155, "repeat": 70, "account": 100, "vat": 55, "rule": 145, "status": 185}\n''',
        '''            "inc": "Export", "date": "Date", "details": "Bank description / reference", "description": "Pastel description", "amount": "Current CSV amount",\n            "key": "Matched name + number", "repeat": "Recurring", "account": "GL account", "vat": "VAT", "rule": "Rule", "status": "Status"\n        }\n        widths = {"inc": 58, "date": 88, "details": 280, "description": 170, "amount": 105, "key": 155, "repeat": 70, "account": 100, "vat": 55, "rule": 145, "status": 185}\n''',
        'restore main table labels',
    )

    s = replace_once(
        s,
        '''            tree.column(c, width=widths[c], anchor="center" if c in {"inc", "review"} else ("e" if c == "amount" else "w"), stretch=(c in {"details", "description", "rule"}))\n''',
        '''            tree.column(c, width=widths[c], anchor="center" if c == "inc" else ("e" if c == "amount" else "w"), stretch=(c in {"details", "description", "rule"}))\n''',
        'restore main table alignment',
    )

    s = replace_once(
        s,
        '''        txns = self._list(direction)\n        reviewable = {i for i, t in enumerate(txns) if (t.status or "").startswith("Amount review required")}\n        self.review_selection[direction].intersection_update(reviewable)\n        q = normalize_text(self.search_vars[direction].get())\n''',
        '''        txns = self._list(direction)\n        q = normalize_text(self.search_vars[direction].get())\n''',
        'remove main review selection cleanup',
    )

    s = replace_once(
        s,
        '''            review_tick = "☑" if idx in self.review_selection[direction] else ("☐" if (t.status or "").startswith("Amount review required") else "")\n            vals = ("☑" if t.include else "☐", review_tick, t.txn_date.strftime("%d/%m/%Y"), t.details, t.description, f"R {money(t.payment_amount)}", t.match_key, repeat, t.account, "VAT" if t.vat else "No", t.rule_name, t.status)\n''',
        '''            vals = ("☑" if t.include else "☐", t.txn_date.strftime("%d/%m/%Y"), t.details, t.description, f"R {money(t.payment_amount)}", t.match_key, repeat, t.account, "VAT" if t.vat else "No", t.rule_name, t.status)\n''',
        'restore main table row values',
    )

    old_click = '''    def _tree_click(self, event, direction: str):\n        tree = self.trees[direction]\n        if tree.identify_region(event.x, event.y) != "cell":\n            return\n        col = tree.identify_column(event.x)\n        iid = tree.identify_row(event.y)\n        if not iid:\n            return\n        txns = self._list(direction)\n        try:\n            idx = int(iid)\n        except Exception:\n            return\n        if col == "#1":\n            txns[idx].include = not txns[idx].include\n            self.refresh_transaction_tree(direction)\n            tree.selection_set(iid)\n            return "break"\n        if col == "#2":\n            t = txns[idx]\n            if not (t.status or "").startswith("Amount review required"):\n                return "break"\n            if idx in self.review_selection[direction]:\n                self.review_selection[direction].remove(idx)\n            else:\n                self.review_selection[direction].add(idx)\n            self.refresh_transaction_tree(direction)\n            tree.selection_set(iid)\n            return "break"\n\n    def _tree_double_click(self, event, direction: str):\n        if self.trees[direction].identify_column(event.x) not in {"#1", "#2"}:\n            self.assign_rule_selected(direction)\n'''
    new_click = '''    def _tree_click(self, event, direction: str):\n        tree = self.trees[direction]\n        if tree.identify_region(event.x, event.y) == "cell" and tree.identify_column(event.x) == "#1":\n            iid = tree.identify_row(event.y)\n            if iid:\n                txns = self._list(direction)\n                try:\n                    idx = int(iid); txns[idx].include = not txns[idx].include\n                except Exception:\n                    return\n                self.refresh_transaction_tree(direction)\n                tree.selection_set(iid)\n                return "break"\n\n    def _tree_double_click(self, event, direction: str):\n        if self.trees[direction].identify_column(event.x) != "#1":\n            self.assign_rule_selected(direction)\n'''
    s = replace_once(s, old_click, new_click, 'restore main table click handling')

    helper_marker = '\n\ndef apply_review_assignment(txns: List["Transaction"], account: str, description: str = "", vat: bool = False, tax_type: int = 0) -> int:\n'
    helper = '''\n\ndef rule_window_amount_candidates(txns: List["Transaction"], direction: str, mode: str, pattern: str, operator: str, threshold: str) -> List[Tuple[int, "Transaction"]]:\n    """Rows from the current statement caught by this rule's amount condition.\n\n    These are the exceptions the user needs to see inside the Rule window when\n    Review each qualifying transaction is selected.\n    """\n    out: List[Tuple[int, "Transaction"]] = []\n    direction = (direction or "PAYMENT").upper()\n    if not (pattern or "").strip() or not (operator or "").strip() or not (threshold or "").strip():\n        return out\n    for idx, t in enumerate(txns):\n        if (t.direction or "PAYMENT").upper() != direction:\n            continue\n        if not rule_matches(mode, pattern, t.details, t.txn_type):\n            continue\n        if amount_condition_matches(t.payment_amount, operator, threshold):\n            out.append((idx, t))\n    return out\n\n\ndef apply_rule_window_manual_assignment(txns: List["Transaction"], account: str, description: str = "", vat: bool = False, tax_type: int = 0) -> int:\n    """Apply an allocation staged inside the Rule window to exactly these rows."""\n    account = (account or "").strip()\n    description = (description or "").strip()\n    if not account:\n        return 0\n    count = 0\n    for t in txns:\n        t.account = account\n        if description:\n            t.description = description\n        t.vat = bool(vat)\n        t.tax_type = int(tax_type or 0) if t.vat else 0\n        t.rule_id = None\n        t.rule_name = "Manual amount review"\n        t.status = "Amount review assigned manually"\n        t.manual_override = True\n        t.ambiguous = False\n        t.auto_allocated = False\n        t.amount_condition_applied = True\n        count += 1\n    return count\n'''
    s = replace_once(s, helper_marker, helper + helper_marker, 'rule window helpers')

    s = replace_once(
        s,
        '''        self.store = store\n        self.txn = txn\n        self.rule = rule\n        self.locked_identity = normalize_text(locked_identity)\n        self.result = None\n''',
        '''        self.store = store\n        self.txn = txn\n        self.rule = rule\n        self.app = parent\n        self.locked_identity = normalize_text(locked_identity)\n        self.result = None\n        self.amount_review_selected: set = set()\n        self.pending_amount_review_assignments: Dict[int, Tuple[str, str, bool, int]] = {}\n        self.applied_review_transaction_ids: set = set()\n''',
        'rule dialog review state',
    )

    amount_hint = '''        ttk.Label(amount_box, text="Automatically allocate uses the Alternative GL/description. Review each qualifying transaction leaves every matching amount unallocated so you can select it and use Assign once.", foreground="#555555", wraplength=560).grid(row=4, column=0, columnspan=6, sticky="w", pady=(6,0))\n        ttk.Label(amount_box, text="If the amount condition is not met, the normal GL account and normal description above are used automatically.", foreground="#555555", wraplength=560).grid(row=5, column=0, columnspan=6, sticky="w", pady=(3,0))\n        self._amount_state()\n'''
    amount_table = '''        ttk.Label(amount_box, text="Automatically allocate uses the Alternative GL/description. Review each qualifying transaction shows the matching exception payments/receipts in the table below so you can allocate one or many of them separately.", foreground="#555555", wraplength=650).grid(row=4, column=0, columnspan=6, sticky="w", pady=(6,0))\n        ttk.Label(amount_box, text="If the amount condition is not met, the normal GL account and normal description above are used automatically.", foreground="#555555", wraplength=650).grid(row=5, column=0, columnspan=6, sticky="w", pady=(3,0))\n\n        self.amount_review_box = ttk.LabelFrame(amount_box, text="Transactions caught by this amount condition — select and allocate individually", padding=7)\n        self.amount_review_box.grid(row=6, column=0, columnspan=6, sticky="nsew", pady=(8,0))\n        review_cols = ("pick", "date", "amount", "details", "account", "description")\n        self.amount_review_tree = ttk.Treeview(self.amount_review_box, columns=review_cols, show="headings", selectmode="none", height=7)\n        review_labels = {"pick":"Select", "date":"Date", "amount":"Amount", "details":"Bank description / reference", "account":"Assigned GL", "description":"Pastel description"}\n        review_widths = {"pick":58, "date":82, "amount":92, "details":245, "account":95, "description":150}\n        for c in review_cols:\n            self.amount_review_tree.heading(c, text=review_labels[c])\n            self.amount_review_tree.column(c, width=review_widths[c], anchor="center" if c in {"pick", "date"} else ("e" if c == "amount" else "w"), stretch=c in {"details", "description"})\n        ry = ttk.Scrollbar(self.amount_review_box, orient="vertical", command=self.amount_review_tree.yview)\n        self.amount_review_tree.configure(yscrollcommand=ry.set)\n        self.amount_review_tree.grid(row=0, column=0, columnspan=5, sticky="nsew")\n        ry.grid(row=0, column=5, sticky="ns")\n        self.amount_review_box.columnconfigure(0, weight=1)\n        self.amount_review_box.rowconfigure(0, weight=1)\n        self.amount_review_tree.bind("<Button-1>", self._amount_review_tree_click, add="+")\n        ttk.Button(self.amount_review_box, text="Select all shown", command=self._amount_review_select_all).grid(row=1, column=0, sticky="w", pady=(6,0))\n        ttk.Button(self.amount_review_box, text="Clear selection", command=self._amount_review_clear_selection).grid(row=1, column=1, sticky="w", padx=(6,0), pady=(6,0))\n        ttk.Button(self.amount_review_box, text="Assign selected…", command=self._amount_review_assign_selected).grid(row=1, column=2, sticky="w", padx=(12,0), pady=(6,0))\n        self.amount_review_summary = ttk.Label(self.amount_review_box, text="", foreground="#555555")\n        self.amount_review_summary.grid(row=1, column=3, columnspan=2, sticky="e", padx=(12,0), pady=(6,0))\n\n        self.vars["amount_threshold"].trace_add("write", lambda *_: self._refresh_amount_review_table())\n        self.vars["amount_operator"].trace_add("write", lambda *_: self._refresh_amount_review_table())\n        self.vars["pattern"].trace_add("write", lambda *_: self._refresh_amount_review_table())\n        self.vars["mode_label"].trace_add("write", lambda *_: self._refresh_amount_review_table())\n        self._amount_state()\n'''
    s = replace_once(s, amount_hint, amount_table, 'embedded amount review table')

    old_state = '''    def _amount_state(self):\n        enabled = bool(self.vars["amount_enabled"].get())\n        review_each = self.vars["amount_action_label"].get() == "Review each qualifying transaction"\n        self.amount_op.configure(state="readonly" if enabled else "disabled")\n        self.amount_threshold.configure(state="normal" if enabled else "disabled")\n        self.amount_action.configure(state="readonly" if enabled else "disabled")\n        auto_state = "normal" if (enabled and not review_each) else "disabled"\n        self.amount_account.configure(state=auto_state)\n        self.amount_description.configure(state=auto_state)\n\n    def save(self):\n'''
    new_state = '''    def _amount_state(self):\n        enabled = bool(self.vars["amount_enabled"].get())\n        review_each = self.vars["amount_action_label"].get() == "Review each qualifying transaction"\n        self.amount_op.configure(state="readonly" if enabled else "disabled")\n        self.amount_threshold.configure(state="normal" if enabled else "disabled")\n        self.amount_action.configure(state="readonly" if enabled else "disabled")\n        auto_state = "normal" if (enabled and not review_each) else "disabled"\n        self.amount_account.configure(state=auto_state)\n        self.amount_description.configure(state=auto_state)\n        if hasattr(self, "amount_review_box"):\n            if enabled and review_each:\n                self.amount_review_box.grid()\n                self._refresh_amount_review_table()\n            else:\n                self.amount_review_box.grid_remove()\n\n    def _amount_review_candidates(self) -> List[Tuple[int, Transaction]]:\n        if not hasattr(self.app, "_list"):\n            return []\n        pattern = self.locked_identity or self.vars["pattern"].get().strip()\n        mode = "SMART" if self.locked_identity else next((b for a,b in self.MODES if a == self.vars["mode_label"].get()), "SMART")\n        return rule_window_amount_candidates(\n            self.app._list(self.direction), self.direction, mode, pattern,\n            self.vars["amount_operator"].get().strip(), self.vars["amount_threshold"].get().strip()\n        )\n\n    def _refresh_amount_review_table(self):\n        if not hasattr(self, "amount_review_tree"):\n            return\n        tree = self.amount_review_tree\n        tree.delete(*tree.get_children())\n        candidates = self._amount_review_candidates()\n        valid = {idx for idx, _t in candidates}\n        self.amount_review_selected.intersection_update(valid)\n        for idx, t in candidates:\n            pending = self.pending_amount_review_assignments.get(idx)\n            account = pending[0] if pending else t.account\n            description = pending[1] if (pending and pending[1]) else (t.description or "")\n            tree.insert(\n                "", "end", iid=str(idx),\n                values=("☑" if idx in self.amount_review_selected else "☐", t.txn_date.strftime("%d/%m/%Y"), f"R {money(t.payment_amount)}", t.details, account, description)\n            )\n        selected_count = len(self.amount_review_selected)\n        self.amount_review_summary.configure(text=f"{len(candidates)} qualifying • {selected_count} selected")\n\n    def _amount_review_tree_click(self, event):\n        tree = self.amount_review_tree\n        if tree.identify_region(event.x, event.y) != "cell" or tree.identify_column(event.x) != "#1":\n            return\n        iid = tree.identify_row(event.y)\n        if not iid:\n            return\n        try:\n            idx = int(iid)\n        except ValueError:\n            return\n        if idx in self.amount_review_selected:\n            self.amount_review_selected.remove(idx)\n        else:\n            self.amount_review_selected.add(idx)\n        self._refresh_amount_review_table()\n        return "break"\n\n    def _amount_review_select_all(self):\n        self.amount_review_selected = {idx for idx, _t in self._amount_review_candidates()}\n        self._refresh_amount_review_table()\n\n    def _amount_review_clear_selection(self):\n        self.amount_review_selected.clear()\n        self._refresh_amount_review_table()\n\n    def _amount_review_assign_selected(self):\n        candidates = dict(self._amount_review_candidates())\n        selected_pairs = [(idx, candidates[idx]) for idx in sorted(self.amount_review_selected) if idx in candidates]\n        if not selected_pairs:\n            messagebox.showinfo(APP_NAME, "Tick one or more transactions in the table first.", parent=self)\n            return\n        txns = [t for _idx, t in selected_pairs]\n        dlg = MultiReviewAssignDialog(self, txns, self.store.get_setting("vat_tax_type", ""), self.store.known_accounts())\n        self.wait_window(dlg)\n        if not dlg.result:\n            return\n        account, description, vat, tax_type = dlg.result\n        for idx, _t in selected_pairs:\n            self.pending_amount_review_assignments[idx] = (account, description, vat, tax_type)\n        self.amount_review_selected.clear()\n        self._refresh_amount_review_table()\n\n    def save(self):\n'''
    s = replace_once(s, old_state, new_state, 'rule dialog review methods')

    s = replace_once(
        s,
        '''        rid = self.store.save_rule(r)\n        self.result = rid\n        self.destroy()\n''',
        '''        rid = self.store.save_rule(r)\n        self.applied_review_transaction_ids = set()\n        if amount_action == "REVIEW" and self.pending_amount_review_assignments and hasattr(self.app, "_list"):\n            current_candidates = dict(self._amount_review_candidates())\n            live = self.app._list(self.direction)\n            for idx, assignment in list(self.pending_amount_review_assignments.items()):\n                if idx not in current_candidates or not (0 <= idx < len(live)):\n                    continue\n                account_i, description_i, vat_i, tax_type_i = assignment\n                t = live[idx]\n                apply_rule_window_manual_assignment([t], account_i, description_i, vat_i, tax_type_i)\n                self.applied_review_transaction_ids.add(id(t))\n        self.result = rid\n        self.destroy()\n''',
        'apply staged review allocations on save',
    )

    # Preserve rows allocated inside the rule dialog when callers reapply rules.
    s = replace_once(
        s,
        '''        if dlg.result:\n            t.manual_override = False\n            self.reapply_rules(silent=True)\n\n    def manual_assign_selected(self, direction: str):\n''',
        '''        if dlg.result:\n            if id(t) not in getattr(dlg, "applied_review_transaction_ids", set()):\n                t.manual_override = False\n            self.reapply_rules(silent=True)\n\n    def manual_assign_selected(self, direction: str):\n''',
        'preserve rule-dialog assignment from main rule action',
    )

    s = replace_once(
        s,
        '''        if dlg.result:\n            for i in idxs:\n                txns[i].manual_override = False\n            self.reapply_rules(silent=True)\n            self.status_var.set(f"Saved identity rule for {key}. It applies to that identity in future CSV files; each CSV amount remains automatic.")\n''',
        '''        if dlg.result:\n            protected = getattr(dlg, "applied_review_transaction_ids", set())\n            for i in idxs:\n                if id(txns[i]) not in protected:\n                    txns[i].manual_override = False\n            self.reapply_rules(silent=True)\n            self.status_var.set(f"Saved identity rule for {key}. Qualifying amount exceptions can be allocated individually inside the rule window.")\n''',
        'preserve rule-dialog assignments from recurring rule action',
    )

    s = replace_once(
        s,
        '''        ttk.Label(f,text="Only the checked Allocate rows will be changed. Other Amount Review transactions remain untouched for separate allocation.",foreground="#555555",wraplength=600).grid(row=6,column=0,columnspan=2,sticky="w",pady=(4,10))\n''',
        '''        ttk.Label(f,text="Only the transactions selected in the rule window will receive this allocation. All other qualifying transactions stay unchanged so you can assign them separately.",foreground="#555555",wraplength=600).grid(row=6,column=0,columnspan=2,sticky="w",pady=(4,10))\n''',
        'group assignment dialog wording',
    )

    test_marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.8: the Rule window lists only matching transactions caught by the amount condition.\n    rw_a = Transaction(180, date(2026, 6, 1), Decimal("-1610.00"), "DEBIT", "C VAN HEERDEN", direction="PAYMENT")\n    rw_b = Transaction(181, date(2026, 6, 1), Decimal("-1778.65"), "DEBIT", "C VAN HEERDEN", direction="PAYMENT")\n    rw_c = Transaction(182, date(2026, 6, 2), Decimal("-48452.10"), "DEBIT", "C VAN HEERDEN", direction="PAYMENT")\n    rw_other = Transaction(183, date(2026, 6, 1), Decimal("-1200.00"), "DEBIT", "OTHER SUPPLIER", direction="PAYMENT")\n    rw_candidates = rule_window_amount_candidates([rw_a, rw_b, rw_c, rw_other], "PAYMENT", "SMART", "C VAN HEERDEN", "<", "45000.00")\n    assert [idx for idx, _t in rw_candidates] == [0, 1]\n    assert apply_rule_window_manual_assignment([rw_a, rw_b], "3270000", "PETROL", False, 0) == 2\n    assert rw_a.account == "3270000" and rw_b.account == "3270000" and rw_a.description == "PETROL"\n    assert rw_c.account == "" and rw_other.account == ""\n    assert apply_rule_window_manual_assignment([rw_c], "4400010", "SURVEY", False, 0) == 1\n    assert rw_c.account == "4400010" and rw_c.description == "SURVEY"\n\n'''
    s = replace_once(s, test_marker, tests + test_marker, 'rule window table self tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.8 with embedded Rule-window amount review table")


if __name__ == "__main__":
    main(sys.argv[1])
