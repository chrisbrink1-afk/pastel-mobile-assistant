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

    s = replace_once(s, 'APP_VERSION = "1.11.10"', 'APP_VERSION = "1.11.11"', 'version')

    s = replace_once(
        s,
        '''        self.resizable(True, True)\n        self.minsize(700, 520)\n\n        initial_key = rule.pattern if rule else (smart_key(txn.details, txn.txn_type) if txn else "")\n''',
        '''        self.resizable(True, True)\n        self.minsize(520, 360)\n        _screen_w = self.winfo_screenwidth()\n        _screen_h = self.winfo_screenheight()\n        _initial_w = max(560, min(980, _screen_w - 80))\n        _initial_h = max(420, min(760, _screen_h - 100))\n        self.geometry(f"{_initial_w}x{_initial_h}")\n\n        initial_key = rule.pattern if rule else (smart_key(txn.details, txn.txn_type) if txn else "")\n''',
        'screen-safe resizable dialog geometry',
    )

    old_root = '''        root = ttk.Frame(self, padding=14)\n        root.grid(sticky="nsew")\n        self.columnconfigure(0, weight=1)\n        self.rowconfigure(0, weight=1)\n        root.columnconfigure(1, weight=1)\n        row = 0\n'''
    new_root = '''        # Scrollable Rule-dialog viewport. Resizing is the primary experience;\n        # the scrollbars are the fallback for small screens / high DPI scaling.\n        viewport = ttk.Frame(self)\n        viewport.grid(row=0, column=0, sticky="nsew")\n        self.columnconfigure(0, weight=1)\n        self.rowconfigure(0, weight=1)\n        viewport.columnconfigure(0, weight=1)\n        viewport.rowconfigure(0, weight=1)\n\n        self.rule_canvas = tk.Canvas(viewport, highlightthickness=0, borderwidth=0)\n        self.rule_vscroll = ttk.Scrollbar(viewport, orient="vertical", command=self.rule_canvas.yview)\n        self.rule_hscroll = ttk.Scrollbar(viewport, orient="horizontal", command=self.rule_canvas.xview)\n        self.rule_canvas.configure(yscrollcommand=self.rule_vscroll.set, xscrollcommand=self.rule_hscroll.set)\n        self.rule_canvas.grid(row=0, column=0, sticky="nsew")\n        self.rule_vscroll.grid(row=0, column=1, sticky="ns")\n        self.rule_hscroll.grid(row=1, column=0, sticky="ew")\n\n        root = ttk.Frame(self.rule_canvas, padding=14)\n        self.rule_canvas_window = self.rule_canvas.create_window((0, 0), window=root, anchor="nw")\n        root.columnconfigure(1, weight=1)\n\n        def _sync_rule_scrollregion(_event=None):\n            bbox = self.rule_canvas.bbox("all")\n            if bbox:\n                self.rule_canvas.configure(scrollregion=bbox)\n\n        def _fit_rule_content(event):\n            # Fill available space when the window is large, but retain the\n            # content's requested dimensions when the viewport is smaller so\n            # horizontal/vertical scrolling exposes every control.\n            root.update_idletasks()\n            width = max(root.winfo_reqwidth(), event.width)\n            height = max(root.winfo_reqheight(), event.height)\n            self.rule_canvas.itemconfigure(self.rule_canvas_window, width=width, height=height)\n            _sync_rule_scrollregion()\n\n        root.bind("<Configure>", _sync_rule_scrollregion, add="+")\n        self.rule_canvas.bind("<Configure>", _fit_rule_content, add="+")\n        row = 0\n'''
    s = replace_once(s, old_root, new_root, 'scrollable RuleDialog viewport')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.11 with resizable and scrollable Assign/Edit Rule dialog")


if __name__ == "__main__":
    main(sys.argv[1])
