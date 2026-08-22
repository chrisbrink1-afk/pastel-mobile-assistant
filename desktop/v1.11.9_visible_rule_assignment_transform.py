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

    s = replace_once(s, 'APP_VERSION = "1.11.8"', 'APP_VERSION = "1.11.9"', 'version')

    # v1.11.8 placed the action row underneath the Treeview. On smaller display
    # sizes / Windows scaling that row could be clipped, leaving the user able to
    # tick transactions but unable to reach Assign selected. Put the action bar
    # above the table and keep it visible at all times.
    old_block = '''        ry = ttk.Scrollbar(self.amount_review_box, orient="vertical", command=self.amount_review_tree.yview)\n        self.amount_review_tree.configure(yscrollcommand=ry.set)\n        self.amount_review_tree.grid(row=0, column=0, columnspan=5, sticky="nsew")\n        ry.grid(row=0, column=5, sticky="ns")\n        self.amount_review_box.columnconfigure(0, weight=1)\n        self.amount_review_box.rowconfigure(0, weight=1)\n        self.amount_review_tree.bind("<Button-1>", self._amount_review_tree_click, add="+")\n        ttk.Button(self.amount_review_box, text="Select all shown", command=self._amount_review_select_all).grid(row=1, column=0, sticky="w", pady=(6,0))\n        ttk.Button(self.amount_review_box, text="Clear selection", command=self._amount_review_clear_selection).grid(row=1, column=1, sticky="w", padx=(6,0), pady=(6,0))\n        ttk.Button(self.amount_review_box, text="Assign selected…", command=self._amount_review_assign_selected).grid(row=1, column=2, sticky="w", padx=(12,0), pady=(6,0))\n        self.amount_review_summary = ttk.Label(self.amount_review_box, text="", foreground="#555555")\n        self.amount_review_summary.grid(row=1, column=3, columnspan=2, sticky="e", padx=(12,0), pady=(6,0))\n'''

    new_block = '''        ry = ttk.Scrollbar(self.amount_review_box, orient="vertical", command=self.amount_review_tree.yview)\n        self.amount_review_tree.configure(yscrollcommand=ry.set, height=6)\n\n        # Always-visible allocation toolbar. This deliberately sits ABOVE the\n        # transaction table so Windows display scaling cannot hide the action.\n        self.amount_review_toolbar = ttk.Frame(self.amount_review_box)\n        self.amount_review_toolbar.grid(row=0, column=0, columnspan=6, sticky="ew", pady=(0,7))\n        ttk.Label(self.amount_review_toolbar, text="Tick the transactions to allocate, then:", font=("Segoe UI", 9, "bold")).pack(side="left")\n        self.amount_review_assign_button = ttk.Button(\n            self.amount_review_toolbar, text="Assign selected…", command=self._amount_review_assign_selected, style="Accent.TButton"\n        )\n        self.amount_review_assign_button.pack(side="left", padx=(10,6))\n        ttk.Button(self.amount_review_toolbar, text="Select all shown", command=self._amount_review_select_all).pack(side="left", padx=3)\n        ttk.Button(self.amount_review_toolbar, text="Clear selection", command=self._amount_review_clear_selection).pack(side="left", padx=3)\n        self.amount_review_summary = ttk.Label(self.amount_review_toolbar, text="", foreground="#555555")\n        self.amount_review_summary.pack(side="right", padx=(12,0))\n\n        self.amount_review_tree.grid(row=1, column=0, columnspan=5, sticky="nsew")\n        ry.grid(row=1, column=5, sticky="ns")\n        self.amount_review_box.columnconfigure(0, weight=1)\n        self.amount_review_box.rowconfigure(1, weight=1)\n        self.amount_review_tree.bind("<Button-1>", self._amount_review_tree_click, add="+")\n'''
    s = replace_once(s, old_block, new_block, 'move rule-window allocation toolbar above table')

    # Keep the button obviously actionable after selection and visually confirm
    # the exact number of rows that will be changed.
    old_summary = '''        selected_count = len(self.amount_review_selected)\n        self.amount_review_summary.configure(text=f"{len(candidates)} qualifying • {selected_count} selected")\n'''
    new_summary = '''        selected_count = len(self.amount_review_selected)\n        self.amount_review_summary.configure(text=f"{len(candidates)} qualifying • {selected_count} selected")\n        if hasattr(self, "amount_review_assign_button"):\n            self.amount_review_assign_button.configure(\n                text=f"Assign selected ({selected_count})…" if selected_count else "Assign selected…",\n                state="normal" if selected_count else "disabled",\n            )\n'''
    s = replace_once(s, old_summary, new_summary, 'selected count and button state')

    # Add an explicit keyboard shortcut for the same action while the embedded
    # review table is in use. This is supplemental; the visible button is primary.
    old_bind = '''        self.amount_review_tree.bind("<Button-1>", self._amount_review_tree_click, add="+")\n\n        self.vars["amount_threshold"].trace_add("write", lambda *_: self._refresh_amount_review_table())\n'''
    new_bind = '''        self.amount_review_tree.bind("<Button-1>", self._amount_review_tree_click, add="+")\n        self.amount_review_tree.bind("<Return>", lambda _e: self._amount_review_assign_selected(), add="+")\n\n        self.vars["amount_threshold"].trace_add("write", lambda *_: self._refresh_amount_review_table())\n'''
    s = replace_once(s, old_bind, new_bind, 'rule table enter shortcut')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.9 with always-visible rule-window allocation controls")


if __name__ == "__main__":
    main(sys.argv[1])
