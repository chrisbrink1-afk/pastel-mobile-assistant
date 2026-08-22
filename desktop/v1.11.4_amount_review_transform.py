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
    s = replace_once(s, 'APP_VERSION = "1.11.3"', 'APP_VERSION = "1.11.4"', 'version')

    old_helpers = '''def effective_rule_account(rule: "Rule", amount: Decimal) -> Tuple[str, bool]:
    if rule.amount_account.strip() and amount_condition_matches(amount, rule.amount_operator, rule.amount_threshold):
        return rule.amount_account.strip(), True
    return rule.account.strip(), False


def effective_rule_description(rule: "Rule", amount: Decimal) -> str:
    """Return the branch-specific Pastel description for an allocation rule.

    If the amount-based branch is triggered and an alternative description has
    been supplied, use it. Otherwise keep the rule's normal description.
    """
    _account, amount_branch = effective_rule_account(rule, amount)
    if amount_branch and rule.amount_description.strip():
        return rule.amount_description.strip()
    return (rule.description or "").strip()
'''
    new_helpers = '''def amount_rule_action(rule: "Rule") -> str:
    action = (getattr(rule, "amount_action", "AUTO") or "AUTO").strip().upper()
    return "REVIEW" if action == "REVIEW" else "AUTO"


def amount_rule_condition_active(rule: "Rule", amount: Decimal) -> bool:
    return bool(
        (rule.amount_operator or "").strip()
        and (rule.amount_threshold or "").strip()
        and amount_condition_matches(amount, rule.amount_operator, rule.amount_threshold)
    )


def effective_rule_account(rule: "Rule", amount: Decimal) -> Tuple[str, bool]:
    amount_branch = amount_rule_condition_active(rule, amount)
    if amount_branch:
        if amount_rule_action(rule) == "REVIEW":
            # The normal account is returned only as a rule signature/default;
            # apply_rules deliberately leaves the transaction unallocated.
            return rule.account.strip(), True
        if rule.amount_account.strip():
            return rule.amount_account.strip(), True
    return rule.account.strip(), False


def effective_rule_description(rule: "Rule", amount: Decimal) -> str:
    """Return the branch-specific Pastel description for an allocation rule."""
    _account, amount_branch = effective_rule_account(rule, amount)
    if amount_branch and amount_rule_action(rule) == "AUTO" and rule.amount_description.strip():
        return rule.amount_description.strip()
    return (rule.description or "").strip()
'''
    s = replace_once(s, old_helpers, new_helpers, 'amount review helpers')

    s = replace_once(
        s,
        '''    amount_account: str = ""
    amount_description: str = ""
''',
        '''    amount_account: str = ""
    amount_description: str = ""
    amount_action: str = "AUTO"
''',
        'rule dataclass amount action',
    )

    s = replace_once(
        s,
        '''            amount_account TEXT NOT NULL DEFAULT '',
            amount_description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
''',
        '''            amount_account TEXT NOT NULL DEFAULT '',
            amount_description TEXT NOT NULL DEFAULT '',
            amount_action TEXT NOT NULL DEFAULT 'AUTO',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
''',
        'rules schema amount action',
    )

    s = replace_once(
        s,
        '''            "amount_account": "TEXT NOT NULL DEFAULT ''",
            "amount_description": "TEXT NOT NULL DEFAULT ''",
        }.items():
''',
        '''            "amount_account": "TEXT NOT NULL DEFAULT ''",
            "amount_description": "TEXT NOT NULL DEFAULT ''",
            "amount_action": "TEXT NOT NULL DEFAULT 'AUTO'",
        }.items():
''',
        'rules migration amount action',
    )

    s = replace_once(
        s,
        '''            (r["amount_account"] if "amount_account" in keys else "") or "",
            (r["amount_description"] if "amount_description" in keys else "") or "",
        )
''',
        '''            (r["amount_account"] if "amount_account" in keys else "") or "",
            (r["amount_description"] if "amount_description" in keys else "") or "",
            ((r["amount_action"] if "amount_action" in keys else "AUTO") or "AUTO").upper(),
        )
''',
        'row to rule amount action',
    )

    s = replace_once(
        s,
        '''            rule.amount_threshold or "", rule.amount_account or "", rule.amount_description or "",
        )
''',
        '''            rule.amount_threshold or "", rule.amount_account or "", rule.amount_description or "", amount_rule_action(rule),
        )
''',
        'save rule values amount action',
    )

    s = replace_once(
        s,
        '''"""UPDATE rules SET name=?,mode=?,pattern=?,account=?,vat=?,tax_type=?,pastel_ref=?,priority=?,enabled=?,direction=?,description=?,amount_operator=?,amount_threshold=?,amount_account=?,amount_description=?,updated_at=CURRENT_TIMESTAMP WHERE id=?"""''',
        '''"""UPDATE rules SET name=?,mode=?,pattern=?,account=?,vat=?,tax_type=?,pastel_ref=?,priority=?,enabled=?,direction=?,description=?,amount_operator=?,amount_threshold=?,amount_account=?,amount_description=?,amount_action=?,updated_at=CURRENT_TIMESTAMP WHERE id=?"""''',
        'update rule SQL amount action',
    )

    s = replace_once(
        s,
        '''"""INSERT INTO rules(name,mode,pattern,account,vat,tax_type,pastel_ref,priority,enabled,direction,description,amount_operator,amount_threshold,amount_account,amount_description) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""''',
        '''"""INSERT INTO rules(name,mode,pattern,account,vat,tax_type,pastel_ref,priority,enabled,direction,description,amount_operator,amount_threshold,amount_account,amount_description,amount_action) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""''',
        'insert rule SQL amount action',
    )

    s = replace_once(
        s,
        '''        distinct = {
            (effective_rule_account(r, t.payment_amount)[0], bool(r.vat), int(r.tax_type), effective_rule_description(r, t.payment_amount))
            for r in top
        }
''',
        '''        distinct = {
            (amount_rule_action(r), effective_rule_account(r, t.payment_amount)[0], bool(r.vat), int(r.tax_type), effective_rule_description(r, t.payment_amount))
            for r in top
        }
''',
        'ambiguity amount action',
    )

    s = replace_once(
        s,
        '''        r = top[0]
        account, amount_branch = effective_rule_account(r, t.payment_amount)
        t.rule_id = r.id
''',
        '''        r = top[0]
        account, amount_branch = effective_rule_account(r, t.payment_amount)
        if amount_branch and amount_rule_action(r) == "REVIEW":
            # Qualifying amount is deliberately NOT auto-allocated. Keep enough
            # rule context to make one-at-a-time review quick and auditable.
            t.rule_id = r.id
            t.rule_name = f"Review • {r.name}"
            t.account = ""
            t.description = (r.description or "").strip()
            t.vat = bool(r.vat)
            t.tax_type = int(r.tax_type or default_tax_type or 0) if t.vat else 0
            t.match_key = r.pattern
            t.pastel_ref = (r.pastel_ref or derive_pastel_reference(t.details, r.pattern, t.row_no))[:8]
            t.auto_allocated = False
            t.amount_condition_applied = True
            t.status = f"Amount review required • amount {r.amount_operator} R {money(D(r.amount_threshold))}"
            continue
        t.rule_id = r.id
''',
        'apply amount review branch',
    )

    s = replace_once(
        s,
        '''        initial_amount_enabled = bool(rule and rule.amount_operator and rule.amount_account)
        initial_amount_operator = rule.amount_operator if rule and rule.amount_operator else "<"
        initial_amount_threshold = rule.amount_threshold if rule else ""
        initial_amount_account = rule.amount_account if rule else ""
        initial_amount_description = rule.amount_description if rule else ""
''',
        '''        initial_amount_action = amount_rule_action(rule) if rule else "AUTO"
        initial_amount_enabled = bool(rule and rule.amount_operator and (rule.amount_account or initial_amount_action == "REVIEW"))
        initial_amount_operator = rule.amount_operator if rule and rule.amount_operator else "<"
        initial_amount_threshold = rule.amount_threshold if rule else ""
        initial_amount_account = rule.amount_account if rule else ""
        initial_amount_description = rule.amount_description if rule else ""
        initial_amount_action_label = "Review each qualifying transaction" if initial_amount_action == "REVIEW" else "Automatically allocate"
''',
        'dialog initial amount action',
    )

    s = replace_once(
        s,
        '''            "amount_account": tk.StringVar(value=initial_amount_account),
            "amount_description": tk.StringVar(value=initial_amount_description),
        }
''',
        '''            "amount_account": tk.StringVar(value=initial_amount_account),
            "amount_description": tk.StringVar(value=initial_amount_description),
            "amount_action_label": tk.StringVar(value=initial_amount_action_label),
        }
''',
        'dialog amount action variable',
    )

    old_ui = '''        ttk.Checkbutton(amount_box, text="Use amount-based allocation rule", variable=self.vars["amount_enabled"], command=self._amount_state).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,6))
        ttk.Label(amount_box, text="If amount").grid(row=1, column=0, sticky="w")
        self.amount_op = ttk.Combobox(amount_box, textvariable=self.vars["amount_operator"], values=["<", "<=", ">", ">=", "="], state="readonly", width=5)
        self.amount_op.grid(row=1, column=1, padx=(5,8))
        self.amount_threshold = ttk.Entry(amount_box, textvariable=self.vars["amount_threshold"], width=12)
        self.amount_threshold.grid(row=1, column=2, padx=(0,10))
        ttk.Label(amount_box, text="allocate to GL").grid(row=1, column=3, sticky="w")
        self.amount_account = ttk.Combobox(amount_box, textvariable=self.vars["amount_account"], values=self.store.known_accounts(), width=20)
        self.amount_account.grid(row=1, column=4, padx=(6,0), sticky="ew")
        ttk.Label(amount_box, text="Alternative description").grid(row=2, column=0, columnspan=2, sticky="w", pady=(7,0))
        self.amount_description = ttk.Entry(amount_box, textvariable=self.vars["amount_description"], width=36)
        self.amount_description.grid(row=2, column=2, columnspan=3, sticky="ew", padx=(0,0), pady=(7,0))
        ttk.Label(amount_box, text="Optional. When the amount condition is met, this Pastel description is used. Leave blank to keep the normal description.", foreground="#555555", wraplength=520).grid(row=3, column=0, columnspan=6, sticky="w", pady=(6,0))
        ttk.Label(amount_box, text="If the condition is not met, the normal General ledger account and normal description above are used.", foreground="#555555", wraplength=520).grid(row=4, column=0, columnspan=6, sticky="w", pady=(3,0))
        self._amount_state()
'''
    new_ui = '''        ttk.Checkbutton(amount_box, text="Use amount-based allocation rule", variable=self.vars["amount_enabled"], command=self._amount_state).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,6))
        ttk.Label(amount_box, text="If amount").grid(row=1, column=0, sticky="w")
        self.amount_op = ttk.Combobox(amount_box, textvariable=self.vars["amount_operator"], values=["<", "<=", ">", ">=", "="], state="readonly", width=5)
        self.amount_op.grid(row=1, column=1, padx=(5,8))
        self.amount_threshold = ttk.Entry(amount_box, textvariable=self.vars["amount_threshold"], width=12)
        self.amount_threshold.grid(row=1, column=2, padx=(0,10))
        ttk.Label(amount_box, text="then").grid(row=1, column=3, sticky="w")
        self.amount_action = ttk.Combobox(amount_box, textvariable=self.vars["amount_action_label"], values=["Automatically allocate", "Review each qualifying transaction"], state="readonly", width=31)
        self.amount_action.grid(row=1, column=4, padx=(6,0), sticky="ew")
        self.amount_action.bind("<<ComboboxSelected>>", lambda e: self._amount_state())
        ttk.Label(amount_box, text="Alternative GL").grid(row=2, column=0, columnspan=2, sticky="w", pady=(7,0))
        self.amount_account = ttk.Combobox(amount_box, textvariable=self.vars["amount_account"], values=self.store.known_accounts(), width=20)
        self.amount_account.grid(row=2, column=2, columnspan=3, sticky="ew", pady=(7,0))
        ttk.Label(amount_box, text="Alternative description").grid(row=3, column=0, columnspan=2, sticky="w", pady=(7,0))
        self.amount_description = ttk.Entry(amount_box, textvariable=self.vars["amount_description"], width=36)
        self.amount_description.grid(row=3, column=2, columnspan=3, sticky="ew", pady=(7,0))
        ttk.Label(amount_box, text="Automatically allocate uses the Alternative GL/description. Review each qualifying transaction leaves every matching amount unallocated so you can select it and use Assign once.", foreground="#555555", wraplength=560).grid(row=4, column=0, columnspan=6, sticky="w", pady=(6,0))
        ttk.Label(amount_box, text="If the amount condition is not met, the normal GL account and normal description above are used automatically.", foreground="#555555", wraplength=560).grid(row=5, column=0, columnspan=6, sticky="w", pady=(3,0))
        self._amount_state()
'''
    s = replace_once(s, old_ui, new_ui, 'amount action UI')

    s = replace_once(
        s,
        '''        enabled = bool(self.vars["amount_enabled"].get())
        self.amount_op.configure(state="readonly" if enabled else "disabled")
        self.amount_threshold.configure(state="normal" if enabled else "disabled")
        self.amount_account.configure(state="normal" if enabled else "disabled")
        self.amount_description.configure(state="normal" if enabled else "disabled")
''',
        '''        enabled = bool(self.vars["amount_enabled"].get())
        review_each = self.vars["amount_action_label"].get() == "Review each qualifying transaction"
        self.amount_op.configure(state="readonly" if enabled else "disabled")
        self.amount_threshold.configure(state="normal" if enabled else "disabled")
        self.amount_action.configure(state="readonly" if enabled else "disabled")
        auto_state = "normal" if (enabled and not review_each) else "disabled"
        self.amount_account.configure(state=auto_state)
        self.amount_description.configure(state=auto_state)
''',
        'amount action state',
    )

    old_save = '''        amount_operator = ""
        amount_threshold = ""
        amount_account = ""
        amount_description = ""
        if self.vars["amount_enabled"].get():
            amount_operator = self.vars["amount_operator"].get().strip()
            amount_account = self.vars["amount_account"].get().strip()
            amount_description = self.vars["amount_description"].get().strip()
            raw_threshold = self.vars["amount_threshold"].get().strip()
            if amount_operator not in {"<", "<=", ">", ">=", "="} or not raw_threshold or not amount_account:
                messagebox.showerror(APP_NAME, "For an amount-based rule, choose an operator, enter an amount and enter the alternate GL account.", parent=self); return
            try:
                threshold_value = Decimal(raw_threshold.replace(",", ""))
            except (InvalidOperation, ValueError):
                messagebox.showerror(APP_NAME, "The amount-rule threshold must be a valid number.", parent=self); return
            amount_threshold = money(threshold_value)
'''
    new_save = '''        amount_operator = ""
        amount_threshold = ""
        amount_account = ""
        amount_description = ""
        amount_action = "AUTO"
        if self.vars["amount_enabled"].get():
            amount_operator = self.vars["amount_operator"].get().strip()
            amount_action = "REVIEW" if self.vars["amount_action_label"].get() == "Review each qualifying transaction" else "AUTO"
            raw_threshold = self.vars["amount_threshold"].get().strip()
            if amount_operator not in {"<", "<=", ">", ">=", "="} or not raw_threshold:
                messagebox.showerror(APP_NAME, "For an amount-based rule, choose an operator and enter the amount threshold.", parent=self); return
            if amount_action == "AUTO":
                amount_account = self.vars["amount_account"].get().strip()
                amount_description = self.vars["amount_description"].get().strip()
                if not amount_account:
                    messagebox.showerror(APP_NAME, "Automatic amount allocation requires an Alternative GL account. Choose Review each qualifying transaction if you want to allocate those rows one at a time.", parent=self); return
            try:
                threshold_value = Decimal(raw_threshold.replace(",", ""))
            except (InvalidOperation, ValueError):
                messagebox.showerror(APP_NAME, "The amount-rule threshold must be a valid number.", parent=self); return
            amount_threshold = money(threshold_value)
'''
    s = replace_once(s, old_save, new_save, 'save amount action')

    s = replace_once(
        s,
        '''            description, amount_operator, amount_threshold, amount_account, amount_description,
        )
''',
        '''            description, amount_operator, amount_threshold, amount_account, amount_description, amount_action,
        )
''',
        'Rule constructor amount action',
    )

    s = replace_once(
        s,
        '''            amount_rule = f"{r.amount_operator} R {r.amount_threshold} → {r.amount_account}" if (r.amount_operator and r.amount_account) else ""
            if amount_rule and r.amount_description:
                amount_rule += f" • desc: {r.amount_description}"
''',
        '''            amount_rule = ""
            if r.amount_operator and r.amount_threshold:
                if amount_rule_action(r) == "REVIEW":
                    amount_rule = f"{r.amount_operator} R {r.amount_threshold} → REVIEW EACH"
                elif r.amount_account:
                    amount_rule = f"{r.amount_operator} R {r.amount_threshold} → {r.amount_account}"
                    if r.amount_description:
                        amount_rule += f" • desc: {r.amount_description}"
''',
        'rules table amount action',
    )

    s = replace_once(
        s,
        '''            w = csv.writer(f); w.writerow(["direction", "name", "mode", "pattern", "account", "description", "amount_operator", "amount_threshold", "amount_account", "amount_description", "vat", "tax_type", "pastel_ref", "priority", "enabled"])
            for r in self.store.all_rules():
                w.writerow([r.direction, r.name, r.mode, r.pattern, r.account, r.description, r.amount_operator, r.amount_threshold, r.amount_account, r.amount_description, int(r.vat), r.tax_type, r.pastel_ref, r.priority, int(r.enabled)])
''',
        '''            w = csv.writer(f); w.writerow(["direction", "name", "mode", "pattern", "account", "description", "amount_operator", "amount_threshold", "amount_account", "amount_description", "amount_action", "vat", "tax_type", "pastel_ref", "priority", "enabled"])
            for r in self.store.all_rules():
                w.writerow([r.direction, r.name, r.mode, r.pattern, r.account, r.description, r.amount_operator, r.amount_threshold, r.amount_account, r.amount_description, amount_rule_action(r), int(r.vat), r.tax_type, r.pastel_ref, r.priority, int(r.enabled)])
''',
        'rule backup export amount action',
    )

    s = replace_once(
        s,
        '''                    r = Rule(None, row.get("name", "").strip(), row.get("mode", "SMART").strip(), row.get("pattern", "").strip(), row.get("account", "").strip(), row.get("vat", "0").strip() in {"1", "true", "True", "yes", "Yes"}, int(row.get("tax_type", "0") or 0), row.get("pastel_ref", "").strip(), int(row.get("priority", "100") or 100), row.get("enabled", "1").strip() not in {"0", "false", "False"}, direction, row.get("description", "").strip(), row.get("amount_operator", "").strip(), row.get("amount_threshold", "").strip(), row.get("amount_account", "").strip(), row.get("amount_description", "").strip())
''',
        '''                    r = Rule(None, row.get("name", "").strip(), row.get("mode", "SMART").strip(), row.get("pattern", "").strip(), row.get("account", "").strip(), row.get("vat", "0").strip() in {"1", "true", "True", "yes", "Yes"}, int(row.get("tax_type", "0") or 0), row.get("pastel_ref", "").strip(), int(row.get("priority", "100") or 100), row.get("enabled", "1").strip() not in {"0", "false", "False"}, direction, row.get("description", "").strip(), row.get("amount_operator", "").strip(), row.get("amount_threshold", "").strip(), row.get("amount_account", "").strip(), row.get("amount_description", "").strip(), (row.get("amount_action", "AUTO") or "AUTO").strip().upper())
''',
        'rule backup import amount action',
    )

    s = replace_once(
        s,
        '''            values=["All", "Recurring", "Unassigned", "Ambiguous", "Assigned", "Auto-allocated", "Corrected", "VAT", "No VAT", "Selected for export", "Not selected"],
            state="readonly", width=17
''',
        '''            values=["All", "Recurring", "Unassigned", "Amount review", "Ambiguous", "Assigned", "Auto-allocated", "Corrected", "VAT", "No VAT", "Selected for export", "Not selected"],
            state="readonly", width=20
''',
        'amount review filter option',
    )

    s = replace_once(
        s,
        '''            if flt == "Auto-allocated" and (not t.auto_allocated or not t.include or t.ambiguous):
                continue
            if flt == "Corrected" and (not t.status.startswith("Corrected") or not t.include):
''',
        '''            if flt == "Auto-allocated" and (not t.auto_allocated or not t.include or t.ambiguous):
                continue
            if flt == "Amount review" and (not t.status.startswith("Amount review required") or not t.include):
                continue
            if flt == "Corrected" and (not t.status.startswith("Corrected") or not t.include):
''',
        'amount review filter behavior',
    )

    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.4: qualifying amount rules can require one-at-a-time review instead of blanket allocation.\n    review_small = Transaction(140, date(2026, 8, 7), Decimal("-250.00"), "DEBIT", "FUEL CARD 7788", direction="PAYMENT")\n    review_large = Transaction(141, date(2026, 8, 7), Decimal("-850.00"), "DEBIT", "FUEL CARD 7788", direction="PAYMENT")\n    review_rule = Rule(140, "FUEL CARD 7788", "SMART", "FUEL CARD 7788", "7100001", False, 0, direction="PAYMENT", description="Normal card spend", amount_operator="<", amount_threshold="500.00", amount_action="REVIEW")\n    apply_rules([review_small, review_large], [review_rule], 0)\n    assert review_small.account == "" and not review_small.auto_allocated and review_small.amount_condition_applied\n    assert review_small.status.startswith("Amount review required") and review_small.rule_id == 140\n    assert review_large.account == "7100001" and review_large.auto_allocated and not review_large.amount_condition_applied\n\n    review_receipt = Transaction(142, date(2026, 8, 7), Decimal("200.00"), "CREDIT", "MISC RECEIPT 8899", direction="RECEIPT")\n    review_receipt_rule = Rule(142, "MISC RECEIPT 8899", "SMART", "MISC RECEIPT 8899", "4100001", False, 0, direction="RECEIPT", amount_operator="<", amount_threshold="500.00", amount_action="REVIEW")\n    apply_rules([review_receipt], [review_receipt_rule], 0)\n    assert review_receipt.account == "" and not review_receipt.auto_allocated and review_receipt.status.startswith("Amount review required")\n\n'''
    s = replace_once(s, marker, tests + marker, 'amount review self tests')

    p.write_text(s, encoding='utf-8')
    print(f'Transformed {p} to v1.11.4 with individual amount-review mode')


if __name__ == '__main__':
    main(sys.argv[1])
