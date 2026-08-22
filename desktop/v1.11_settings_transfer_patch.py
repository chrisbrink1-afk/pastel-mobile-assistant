from pathlib import Path
import sys


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {n}")
    return text.replace(old, new, 1)


def main(path):
    p = Path(path)
    s = p.read_text(encoding="utf-8")

    s = replace_once(
        s,
        'DB_PATH = app_data_dir() / "pastel_payment_assistant.db"\n\n\ndef D(value) -> Decimal:',
        '''DB_PATH = app_data_dir() / "pastel_payment_assistant.db"\nSETTINGS_TRANSFER_KEYS = ("contra_account", "vat_tax_type", "vat_rate", "fiscal_start_month", "project_code")\n\n\ndef read_settings_transfer(path: str) -> Dict[str, str]:\n    p = Path(path)\n    if p.suffix.lower() == ".db":\n        conn = sqlite3.connect(p)\n        try:\n            rows = conn.execute("SELECT key, value FROM settings").fetchall()\n        finally:\n            conn.close()\n        raw = {str(k): str(v) for k, v in rows}\n    else:\n        with open(p, "r", encoding="utf-8-sig") as f:\n            data = json.load(f)\n        if not isinstance(data, dict):\n            raise ValueError("Settings backup must contain a JSON object.")\n        raw = data.get("settings", data)\n        if not isinstance(raw, dict):\n            raise ValueError("Settings backup does not contain a settings object.")\n    out = {k: str(raw[k]) for k in SETTINGS_TRANSFER_KEYS if k in raw}\n    if not out:\n        raise ValueError("No compatible Pastel Payment Assistant settings were found in this file.")\n    return out\n\n\ndef D(value) -> Decimal:''',
        "settings transfer helpers",
    )

    old_ui = '''        ttk.Button(f, text="Save settings", command=self.save_settings, style="Accent.TButton").grid(row=len(rows)*2, column=0, sticky="w", pady=16)\n        note = ("The app creates review-first Pastel cash-book import files. Selected outgoing rows are exported to a Payments CSV; "\n                "selected incoming rows are exported to a Receipts CSV. Review each imported batch in Pastel before Update/Process.")\n        ttk.Label(f, text=note, wraplength=820).grid(row=len(rows)*2+1, column=0, columnspan=3, sticky="w")'''
    new_ui = '''        buttons = ttk.Frame(f)\n        buttons.grid(row=len(rows)*2, column=0, columnspan=3, sticky="w", pady=16)\n        ttk.Button(buttons, text="Save settings", command=self.save_settings, style="Accent.TButton").pack(side="left", padx=(0,8))\n        ttk.Button(buttons, text="Export settings backup…", command=self.export_settings_backup).pack(side="left", padx=4)\n        ttk.Button(buttons, text="Import settings backup / v1.10 database…", command=self.import_settings_backup).pack(side="left", padx=4)\n        transfer_note = ("Upgrading from v1.10 to v1.11 on the same Windows PC keeps these settings automatically because both versions use the same settings database. "\n                         "For another PC, Import Settings can read either a v1.11 JSON settings backup or a copied v1.10 pastel_payment_assistant.db file.")\n        ttk.Label(f, text=transfer_note, wraplength=820, foreground="#555555").grid(row=len(rows)*2+1, column=0, columnspan=3, sticky="w", pady=(0,8))\n        note = ("The app creates review-first Pastel cash-book import files. Selected outgoing rows are exported to a Payments CSV; "\n                "selected incoming rows are exported to a Receipts CSV. Review each imported batch in Pastel before Update/Process.")\n        ttk.Label(f, text=note, wraplength=820).grid(row=len(rows)*2+2, column=0, columnspan=3, sticky="w")'''
    s = replace_once(s, old_ui, new_ui, "settings UI")

    old_methods = '''    def save_settings(self, quiet=False):\n        for k, v in self.setting_vars.items():\n            self.store.set_setting(k, v.get().strip())\n        if self.txns or self.receipts:\n            self.reapply_rules(silent=True)\n        if not quiet:\n            messagebox.showinfo(APP_NAME, "Settings saved.")\n\n    def load_csv(self):'''
    new_methods = '''    def save_settings(self, quiet=False):\n        for k, v in self.setting_vars.items():\n            self.store.set_setting(k, v.get().strip())\n        if self.txns or self.receipts:\n            self.reapply_rules(silent=True)\n        if not quiet:\n            messagebox.showinfo(APP_NAME, "Settings saved.")\n\n    def export_settings_backup(self):\n        self.save_settings(quiet=True)\n        p = filedialog.asksaveasfilename(\n            title="Export settings backup",\n            defaultextension=".json",\n            filetypes=[("Pastel settings backup", "*.json"), ("All files", "*.*")],\n            initialfile="Pastel_Payment_Assistant_Settings_Backup.json",\n        )\n        if not p:\n            return\n        data = {\n            "format": "PastelPaymentAssistantSettings",\n            "format_version": 1,\n            "app_version": APP_VERSION,\n            "settings": {k: self.store.get_setting(k, "") for k in SETTINGS_TRANSFER_KEYS},\n        }\n        try:\n            with open(p, "w", encoding="utf-8") as f:\n                json.dump(data, f, indent=2, ensure_ascii=False)\n        except Exception as e:\n            messagebox.showerror(APP_NAME, f"Could not export settings backup:\\n{e}")\n            return\n        messagebox.showinfo(APP_NAME, f"Settings backup saved:\\n{p}")\n\n    def import_settings_backup(self):\n        p = filedialog.askopenfilename(\n            title="Import settings backup or v1.10 database",\n            filetypes=[\n                ("Pastel settings backup / database", "*.json *.db"),\n                ("JSON settings backup", "*.json"),\n                ("Pastel Payment Assistant database", "*.db"),\n                ("All files", "*.*"),\n            ],\n        )\n        if not p:\n            return\n        try:\n            incoming = read_settings_transfer(p)\n        except Exception as e:\n            messagebox.showerror(APP_NAME, f"Could not import settings:\\n{e}")\n            return\n        preview = "\\n".join(f"{k}: {incoming.get(k, '')}" for k in SETTINGS_TRANSFER_KEYS if k in incoming)\n        if not messagebox.askyesno(APP_NAME, "Import these settings and replace the current values?\\n\\n" + preview):\n            return\n        for k, value in incoming.items():\n            if k in self.setting_vars:\n                self.setting_vars[k].set(value)\n        self.save_settings(quiet=True)\n        source = "v1.10 database" if Path(p).suffix.lower() == ".db" else "settings backup"\n        messagebox.showinfo(APP_NAME, f"Imported {len(incoming)} setting(s) from the {source}.\\n\\nThe imported values are now active in v1.11.")\n\n    def load_csv(self):'''
    s = replace_once(s, old_methods, new_methods, "settings methods")

    p.write_text(s, encoding="utf-8")
    print(f"Added settings transfer support to {p}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: v1.11_settings_transfer_patch.py <candidate.pyw>")
    main(sys.argv[1])
