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
    s = replace_once(s, 'APP_VERSION = "1.11.2"', 'APP_VERSION = "1.11.3"', 'version')

    s = replace_once(
        s,
        '''def effective_rule_account(rule: "Rule", amount: Decimal) -> Tuple[str, bool]:\n    if rule.amount_account.strip() and amount_condition_matches(amount, rule.amount_operator, rule.amount_threshold):\n        return rule.amount_account.strip(), True\n    return rule.account.strip(), False\n''',
        '''def effective_rule_account(rule: "Rule", amount: Decimal) -> Tuple[str, bool]:\n    if rule.amount_account.strip() and amount_condition_matches(amount, rule.amount_operator, rule.amount_threshold):\n        return rule.amount_account.strip(), True\n    return rule.account.strip(), False\n\n\ndef effective_rule_description(rule: "Rule", amount: Decimal) -> str:\n    \"\"\"Return the branch-specific Pastel description for an allocation rule.\n\n    If the amount-based branch is triggered and an alternative description has\n    been supplied, use it. Otherwise keep the rule's normal description.\n    \"\"\"\n    _account, amount_branch = effective_rule_account(rule, amount)\n    if amount_branch and rule.amount_description.strip():\n        return rule.amount_description.strip()\n    return (rule.description or \"\").strip()\n''',
        'effective description helper',
    )

    s = replace_once(
        s,
        '''    amount_threshold: str = ""\n    amount_account: str = ""\n''',
        '''    amount_threshold: str = ""\n    amount_account: str = ""\n    amount_description: str = ""\n''',
        'rule dataclass amount description',
    )

    s = replace_once(
        s,
        '''            amount_threshold TEXT NOT NULL DEFAULT '',\n            amount_account TEXT NOT NULL DEFAULT '',\n            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,\n''',
        '''            amount_threshold TEXT NOT NULL DEFAULT '',\n            amount_account TEXT NOT NULL DEFAULT '',\n            amount_description TEXT NOT NULL DEFAULT '',\n            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,\n''',
        'rules schema amount description',
    )

    s = replace_once(
        s,
        '''            "amount_threshold": "TEXT NOT NULL DEFAULT ''",\n            "amount_account": "TEXT NOT NULL DEFAULT ''",\n        }.items():\n''',
        '''            "amount_threshold": "TEXT NOT NULL DEFAULT ''",\n            "amount_account": "TEXT NOT NULL DEFAULT ''",\n            "amount_description": "TEXT NOT NULL DEFAULT ''",\n        }.items():\n''',
        'rules migration amount description',
    )

    s = replace_once(
        s,
        '''            (r["amount_threshold"] if "amount_threshold" in keys else "") or "",\n            (r["amount_account"] if "amount_account" in keys else "") or "",\n        )\n''',
        '''            (r["amount_threshold"] if "amount_threshold" in keys else "") or "",\n            (r["amount_account"] if "amount_account" in keys else "") or "",\n            (r["amount_description"] if "amount_description" in keys else "") or "",\n        )\n''',
        'row to rule amount description',
    )

    s = replace_once(
        s,
        '''            int(rule.priority), int(rule.enabled), direction, rule.description or "", rule.amount_operator or "",\n            rule.amount_threshold or "", rule.amount_account or "",\n        )\n''',
        '''            int(rule.priority), int(rule.enabled), direction, rule.description or "", rule.amount_operator or "",\n            rule.amount_threshold or "", rule.amount_account or "", rule.amount_description or "",\n        )\n''',
        'save rule values amount description',
    )

    s = replace_once(
        s,
        '''"""UPDATE rules SET name=?,mode=?,pattern=?,account=?,vat=?,tax_type=?,pastel_ref=?,priority=?,enabled=?,direction=?,description=?,amount_operator=?,amount_threshold=?,amount_account=?,updated_at=CURRENT_TIMESTAMP WHERE id=?"""''',
        '''"""UPDATE rules SET name=?,mode=?,pattern=?,account=?,vat=?,tax_type=?,pastel_ref=?,priority=?,enabled=?,direction=?,description=?,amount_operator=?,amount_threshold=?,amount_account=?,amount_description=?,updated_at=CURRENT_TIMESTAMP WHERE id=?"""''',
        'update rule SQL amount description',
    )

    s = replace_once(
        s,
        '''"""INSERT INTO rules(name,mode,pattern,account,vat,tax_type,pastel_ref,priority,enabled,direction,description,amount_operator,amount_threshold,amount_account) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""''',
        '''"""INSERT INTO rules(name,mode,pattern,account,vat,tax_type,pastel_ref,priority,enabled,direction,description,amount_operator,amount_threshold,amount_account,amount_description) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""''',
        'insert rule SQL amount description',
    )

    s = replace_once(
        s,
        '''            (effective_rule_account(r, t.payment_amount)[0], bool(r.vat), int(r.tax_type), (r.description or "").strip())\n''',
        '''            (effective_rule_account(r, t.payment_amount)[0], bool(r.vat), int(r.tax_type), effective_rule_description(r, t.payment_amount))\n''',
        'ambiguity description branch',
    )

    s = replace_once(
        s,
        '''        t.description = (r.description or "").strip()\n''',
        '''        t.description = effective_rule_description(r, t.payment_amount)\n''',
        'apply alternative description',
    )

    s = replace_once(
        s,
        '''        initial_amount_threshold = rule.amount_threshold if rule else ""\n        initial_amount_account = rule.amount_account if rule else ""\n\n        self.vars = {\n''',
        '''        initial_amount_threshold = rule.amount_threshold if rule else ""\n        initial_amount_account = rule.amount_account if rule else ""\n        initial_amount_description = rule.amount_description if rule else ""\n\n        self.vars = {\n''',
        'dialog initial amount description',
    )

    s = replace_once(
        s,
        '''            "amount_threshold": tk.StringVar(value=initial_amount_threshold),\n            "amount_account": tk.StringVar(value=initial_amount_account),\n        }\n''',
        '''            "amount_threshold": tk.StringVar(value=initial_amount_threshold),\n            "amount_account": tk.StringVar(value=initial_amount_account),\n            "amount_description": tk.StringVar(value=initial_amount_description),\n        }\n''',
        'dialog variable amount description',
    )

    s = replace_once(
        s,
        '''        self.amount_account = ttk.Combobox(amount_box, textvariable=self.vars["amount_account"], values=self.store.known_accounts(), width=20)\n        self.amount_account.grid(row=1, column=4, padx=(6,0), sticky="ew")\n        ttk.Label(amount_box, text="If the condition is not met, the normal General ledger account above is used.", foreground="#555555", wraplength=520).grid(row=2, column=0, columnspan=6, sticky="w", pady=(6,0))\n        self._amount_state()\n''',
        '''        self.amount_account = ttk.Combobox(amount_box, textvariable=self.vars["amount_account"], values=self.store.known_accounts(), width=20)\n        self.amount_account.grid(row=1, column=4, padx=(6,0), sticky="ew")\n        ttk.Label(amount_box, text="Alternative description").grid(row=2, column=0, columnspan=2, sticky="w", pady=(7,0))\n        self.amount_description = ttk.Entry(amount_box, textvariable=self.vars["amount_description"], width=36)\n        self.amount_description.grid(row=2, column=2, columnspan=3, sticky="ew", padx=(0,0), pady=(7,0))\n        ttk.Label(amount_box, text="Optional. When the amount condition is met, this Pastel description is used. Leave blank to keep the normal description.", foreground="#555555", wraplength=520).grid(row=3, column=0, columnspan=6, sticky="w", pady=(6,0))\n        ttk.Label(amount_box, text="If the condition is not met, the normal General ledger account and normal description above are used.", foreground="#555555", wraplength=520).grid(row=4, column=0, columnspan=6, sticky="w", pady=(3,0))\n        self._amount_state()\n''',
        'amount description UI',
    )

    s = replace_once(
        s,
        '''        self.amount_threshold.configure(state="normal" if enabled else "disabled")\n        self.amount_account.configure(state="normal" if enabled else "disabled")\n''',
        '''        self.amount_threshold.configure(state="normal" if enabled else "disabled")\n        self.amount_account.configure(state="normal" if enabled else "disabled")\n        self.amount_description.configure(state="normal" if enabled else "disabled")\n''',
        'amount description state',
    )

    s = replace_once(
        s,
        '''        amount_operator = ""\n        amount_threshold = ""\n        amount_account = ""\n        if self.vars["amount_enabled"].get():\n            amount_operator = self.vars["amount_operator"].get().strip()\n            amount_account = self.vars["amount_account"].get().strip()\n''',
        '''        amount_operator = ""\n        amount_threshold = ""\n        amount_account = ""\n        amount_description = ""\n        if self.vars["amount_enabled"].get():\n            amount_operator = self.vars["amount_operator"].get().strip()\n            amount_account = self.vars["amount_account"].get().strip()\n            amount_description = self.vars["amount_description"].get().strip()\n''',
        'save amount description variable',
    )

    s = replace_once(
        s,
        '''            description, amount_operator, amount_threshold, amount_account,\n        )\n''',
        '''            description, amount_operator, amount_threshold, amount_account, amount_description,\n        )\n''',
        'Rule constructor amount description',
    )

    s = replace_once(
        s,
        '''            amount_rule = f"{r.amount_operator} R {r.amount_threshold} → {r.amount_account}" if (r.amount_operator and r.amount_account) else ""\n''',
        '''            amount_rule = f"{r.amount_operator} R {r.amount_threshold} → {r.amount_account}" if (r.amount_operator and r.amount_account) else ""\n            if amount_rule and r.amount_description:\n                amount_rule += f" • desc: {r.amount_description}"\n''',
        'rules table amount description',
    )

    s = replace_once(
        s,
        '''            w = csv.writer(f); w.writerow(["direction", "name", "mode", "pattern", "account", "description", "amount_operator", "amount_threshold", "amount_account", "vat", "tax_type", "pastel_ref", "priority", "enabled"])\n            for r in self.store.all_rules():\n                w.writerow([r.direction, r.name, r.mode, r.pattern, r.account, r.description, r.amount_operator, r.amount_threshold, r.amount_account, int(r.vat), r.tax_type, r.pastel_ref, r.priority, int(r.enabled)])\n''',
        '''            w = csv.writer(f); w.writerow(["direction", "name", "mode", "pattern", "account", "description", "amount_operator", "amount_threshold", "amount_account", "amount_description", "vat", "tax_type", "pastel_ref", "priority", "enabled"])\n            for r in self.store.all_rules():\n                w.writerow([r.direction, r.name, r.mode, r.pattern, r.account, r.description, r.amount_operator, r.amount_threshold, r.amount_account, r.amount_description, int(r.vat), r.tax_type, r.pastel_ref, r.priority, int(r.enabled)])\n''',
        'rule backup export amount description',
    )

    s = replace_once(
        s,
        '''                    r = Rule(None, row.get("name", "").strip(), row.get("mode", "SMART").strip(), row.get("pattern", "").strip(), row.get("account", "").strip(), row.get("vat", "0").strip() in {"1", "true", "True", "yes", "Yes"}, int(row.get("tax_type", "0") or 0), row.get("pastel_ref", "").strip(), int(row.get("priority", "100") or 100), row.get("enabled", "1").strip() not in {"0", "false", "False"}, direction, row.get("description", "").strip(), row.get("amount_operator", "").strip(), row.get("amount_threshold", "").strip(), row.get("amount_account", "").strip())\n''',
        '''                    r = Rule(None, row.get("name", "").strip(), row.get("mode", "SMART").strip(), row.get("pattern", "").strip(), row.get("account", "").strip(), row.get("vat", "0").strip() in {"1", "true", "True", "yes", "Yes"}, int(row.get("tax_type", "0") or 0), row.get("pastel_ref", "").strip(), int(row.get("priority", "100") or 100), row.get("enabled", "1").strip() not in {"0", "false", "False"}, direction, row.get("description", "").strip(), row.get("amount_operator", "").strip(), row.get("amount_threshold", "").strip(), row.get("amount_account", "").strip(), row.get("amount_description", "").strip())\n''',
        'rule backup import amount description',
    )

    s = replace_once(
        s,
        '''            if t.amount_condition_applied and rule.amount_operator and rule.amount_account:\n                rule.amount_account = account\n            else:\n                rule.account = account\n            rule.description = description\n''',
        '''            if t.amount_condition_applied and rule.amount_operator and rule.amount_account:\n                rule.amount_account = account\n                rule.amount_description = description\n            else:\n                rule.account = account\n                rule.description = description\n''',
        'correction branch amount description',
    )

    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.3: amount-based allocation can use its own alternative description.\n    alt_small = Transaction(130, date(2026, 8, 6), Decimal("-450.00"), "DEBIT", "ALT DESC TEST 5555", direction="PAYMENT")\n    alt_large = Transaction(131, date(2026, 8, 6), Decimal("-750.00"), "DEBIT", "ALT DESC TEST 5555", direction="PAYMENT")\n    alt_rule = Rule(130, "ALT DESC 5555", "SMART", "ALT DESC TEST 5555", "7100001", False, 0, direction="PAYMENT", description="Normal description", amount_operator="<", amount_threshold="500.00", amount_account="7200001", amount_description="Small payment description")\n    apply_rules([alt_small, alt_large], [alt_rule], 0)\n    assert alt_small.account == "7200001" and alt_small.description == "Small payment description" and alt_small.amount_condition_applied\n    assert alt_large.account == "7100001" and alt_large.description == "Normal description" and not alt_large.amount_condition_applied\n\n'''
    s = replace_once(s, marker, tests + marker, 'amount description self tests')

    p.write_text(s, encoding='utf-8')
    print(f'Transformed {p} to v1.11.3 with alternative amount description support')


if __name__ == '__main__':
    main(sys.argv[1])
