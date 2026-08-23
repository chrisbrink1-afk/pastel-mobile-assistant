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
    old = '''    def _tutorial_close(self):\n        win = getattr(self, "tutorial_window", None)\n        if win is not None:\n            try:\n                win.destroy()\n            except Exception:\n                pass\n        self.tutorial_window = None\n\n'''
    new = '''    def _tutorial_close(self):\n        win = getattr(self, "tutorial_window", None)\n        if win is not None:\n            try:\n                win.destroy()\n            except Exception:\n                pass\n        self.tutorial_window = None\n        previous = getattr(self, "_tutorial_previous_mode", "modern")\n        if previous == "classic" and getattr(self, "ui_mode", "modern") != "classic":\n            self._apply_ui_mode("classic", initial=True)\n\n'''
    s = replace_once(s, old, new, 'tutorial restores previous classic mode')
    p.write_text(s, encoding="utf-8")
    print(f"Updated {p}: tutorial restores previous UI mode")


if __name__ == "__main__":
    main(sys.argv[1])
