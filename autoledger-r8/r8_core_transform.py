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

    old = '''        self.tutorial_back_button = ttk.Button(footer, text="Back", command=lambda: self._tutorial_move(-1), style="Modern.TButton")
        self.tutorial_back_button.pack(side="right", padx=(6, 0))
        self.tutorial_next_button = ttk.Button(footer, text="Next", command=lambda: self._tutorial_move(1), style="Accent.TButton")
        self.tutorial_next_button.pack(side="right")
'''
    new = '''        # Tutorial navigation is kept in the lower-right corner.
        # Pack Next first so it becomes the right-most action; Back sits immediately to its left.
        self.tutorial_next_button = ttk.Button(footer, text="Next", command=lambda: self._tutorial_move(1), style="Accent.TButton")
        self.tutorial_next_button.pack(side="right")
        self.tutorial_back_button = ttk.Button(footer, text="Back", command=lambda: self._tutorial_move(-1), style="Modern.TButton")
        self.tutorial_back_button.pack(side="right", padx=(0, 6))
'''
    s = replace_once(s, old, new, "tutorial Back/Next lower-right order")
    p.write_text(s, encoding="utf-8")
    print(f"Updated {p}: tutorial Back/Next buttons")

if __name__ == "__main__":
    main(sys.argv[1])
