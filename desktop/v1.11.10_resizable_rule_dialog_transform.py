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

    s = replace_once(s, 'APP_VERSION = "1.11.9"', 'APP_VERSION = "1.11.10"', 'version')

    # The Assign/Edit Rule window used to be explicitly locked to its requested
    # size. Allow the user to resize it in both directions.
    s = replace_once(
        s,
        '        self.resizable(False, False)\n\n        initial_key = rule.pattern if rule else (smart_key(txn.details, txn.txn_type) if txn else "")\n',
        '        self.resizable(True, True)\n        self.minsize(700, 520)\n\n        initial_key = rule.pattern if rule else (smart_key(txn.details, txn.txn_type) if txn else "")\n',
        'enable RuleDialog resizing',
    )

    # Make the dialog's root frame consume the resized Toplevel area and let the
    # main value column widen with the window.
    s = replace_once(
        s,
        '        root = ttk.Frame(self, padding=14)\n        root.grid(sticky="nsew")\n        row = 0\n',
        '        root = ttk.Frame(self, padding=14)\n        root.grid(sticky="nsew")\n        self.columnconfigure(0, weight=1)\n        self.rowconfigure(0, weight=1)\n        root.columnconfigure(1, weight=1)\n        row = 0\n',
        'make RuleDialog root expandable',
    )

    # Give vertical expansion to the amount-review section, which contains the
    # qualifying transaction table added in v1.11.8/v1.11.9.
    s = replace_once(
        s,
        '        amount_box = ttk.LabelFrame(root, text="Optional amount-based allocation", padding=8)\n        amount_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8,4)); row += 1\n',
        '        amount_box = ttk.LabelFrame(root, text="Optional amount-based allocation", padding=8)\n        amount_box.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=(8,4))\n        root.rowconfigure(row, weight=1)\n        amount_box.columnconfigure(0, weight=1)\n        amount_box.rowconfigure(6, weight=1)\n        row += 1\n',
        'expand amount review section',
    )

    # The embedded review box already stretches internally; ensure the frame is
    # allowed to fill the extra width and height passed down from amount_box.
    s = replace_once(
        s,
        '        self.amount_review_box.grid(row=6, column=0, columnspan=6, sticky="nsew", pady=(8,0))\n',
        '        self.amount_review_box.grid(row=6, column=0, columnspan=6, sticky="nsew", pady=(8,0))\n        for _c in range(6):\n            amount_box.columnconfigure(_c, weight=1 if _c == 0 else 0)\n',
        'keep embedded review table expandable',
    )

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.10 with resizable Assign/Edit Rule dialog")


if __name__ == "__main__":
    main(sys.argv[1])
