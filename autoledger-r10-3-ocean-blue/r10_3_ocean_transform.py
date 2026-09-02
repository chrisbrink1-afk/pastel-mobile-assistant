from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def patch_common(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    s = replace_once(s, 'UPDATE_REVISION = "R10.2"', 'UPDATE_REVISION = "R10.3"', 'revision')
    s = replace_once(s, 'core.APP_VERSION = f"{PRODUCT_VERSION} {UPDATE_REVISION} TEST"', 'core.APP_VERSION = f"{PRODUCT_VERSION} {UPDATE_REVISION}"', 'APP_VERSION')
    s = replace_once(s, 'f"AUTOLEDGER Free v{PRODUCT_VERSION} {UPDATE_REVISION} TEST\\n\\n"', 'f"AUTOLEDGER Free v{PRODUCT_VERSION} {UPDATE_REVISION}\\n\\n"', 'Free edition info')
    s = replace_once(s, 'f"AUTOLEDGER Pro v{PRODUCT_VERSION} {UPDATE_REVISION} TEST\\n\\n"', 'f"AUTOLEDGER Pro v{PRODUCT_VERSION} {UPDATE_REVISION}\\n\\n"', 'Pro edition info')
    s = replace_once(s, 'self.title(f"AUTOLEDGER {edition_title} v{PRODUCT_VERSION} {UPDATE_REVISION} TEST")', 'self.title(f"AUTOLEDGER {edition_title} v{PRODUCT_VERSION} {UPDATE_REVISION}")', 'window title')
    s = replace_once(s, 'fake = {"customer": "R10.2 BUILD TEST", "license_id": "SMOKE"} if edition.upper() == "PRO" else None', 'fake = {"customer": "R10.3 SMOKE", "license_id": "SMOKE"} if edition.upper() == "PRO" else None', 'smoke fake')
    s = replace_once(s,
        '            bg = "#E8F1FF" if edition == "FREE" else "#E7F6EC"\n            fg = "#164A87" if edition == "FREE" else "#176B3A"',
        '            bg = "#EAF6FF" if edition == "FREE" else "#DDF2FF"\n            fg = "#064A7A"',
        'edition badge colours')
    s = s.replace('win.configure(bg="#f4f7fb")', 'win.configure(bg="#F4F8FC")')
    s = s.replace('highlightbackground="#e2e8f0"', 'highlightbackground="#D5E4F0"')
    s = s.replace('fg="#172033"', 'fg="#064A7A"')
    s = s.replace('fg="#334155"', 'fg="#243B53"')
    s = s.replace('fg="#64748b"', 'fg="#5D7185"')
    s = s.replace('if expected not in app.title() or "R10" not in app.title():', 'if expected not in app.title() or UPDATE_REVISION not in app.title():')

    old_icon = '''        try:\n            icon_ico = _resource_path("assets/AUTOLEDGER_ICON.ico")\n            if icon_ico.exists():\n                self.iconbitmap(default=str(icon_ico))\n                self._autoledger_icon_path = str(icon_ico)\n        except Exception:\n            pass\n'''
    new_icon = '''        icon_loaded = False\n        try:\n            icon_ico = _resource_path("assets/AUTOLEDGER_ICON.ico")\n            if icon_ico.exists():\n                self.iconbitmap(default=str(icon_ico))\n                self._autoledger_icon_path = str(icon_ico)\n                icon_loaded = True\n        except Exception:\n            pass\n        if not icon_loaded:\n            try:\n                icon_png = _resource_path("assets/AUTOLEDGER_ICON.png")\n                if icon_png.exists():\n                    self._autoledger_icon_photo = core.tk.PhotoImage(file=str(icon_png))\n                    self.iconphoto(True, self._autoledger_icon_photo)\n                    self._autoledger_icon_path = str(icon_png)\n            except Exception:\n                pass\n'''
    s = replace_once(s, old_icon, new_icon, 'icon loading block')
    path.write_text(s, encoding="utf-8")


def patch_core(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    s = replace_once(s,
        '            self.status_var.set("v2.2 Clean feedback build — no personal data was bundled. The adaptive Tutorial & Help will open automatically for a genuinely new workspace and can be run again at any time.")',
        '            self.status_var.set("Ready. Select the correct company profile, confirm Settings, then load a bank CSV to begin.")',
        'startup status')
    s = replace_once(s,
        '        ttk.Label(title_box, text=f"v{APP_VERSION} Clean feedback workspace", style="ModernSubtitle.TLabel").pack(anchor="w")',
        '        ttk.Label(title_box, text=f"v{APP_VERSION}  •  General Ledger payments & receipts", style="ModernSubtitle.TLabel").pack(anchor="w")',
        'modern header subtitle')

    old = '''        self.configure(bg="#f4f7fb")\n        s.configure("Treeview", rowheight=30, font=("Segoe UI", 9), background="#ffffff", fieldbackground="#ffffff", foreground="#253247")\n        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(7, 8), background="#eef3f8", foreground="#334155")\n        s.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 7), background="#2563eb", foreground="#ffffff")\n        s.map("Accent.TButton", background=[("active", "#1d4ed8"), ("pressed", "#1e40af")], foreground=[("disabled", "#cbd5e1"), ("!disabled", "#ffffff")])\n        s.configure("Modern.TButton", font=("Segoe UI", 9), padding=(9, 6))\n        s.configure("ModernHeader.TFrame", background="#ffffff")\n        s.configure("ModernPage.TFrame", background="#f4f7fb")\n        s.configure("ModernCard.TFrame", background="#ffffff", relief="solid", borderwidth=1)\n        s.configure("ModernTitle.TLabel", background="#ffffff", foreground="#172033", font=("Segoe UI", 18, "bold"))\n        s.configure("ModernSubtitle.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 9))\n        s.configure("DashboardTitle.TLabel", background="#f4f7fb", foreground="#172033", font=("Segoe UI", 22, "bold"))\n        s.configure("DashboardText.TLabel", background="#f4f7fb", foreground="#64748b", font=("Segoe UI", 10))\n        s.configure("CardLabel.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 9))\n        s.configure("CardValue.TLabel", background="#ffffff", foreground="#172033", font=("Segoe UI", 22, "bold"))\n        s.configure("CardNote.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 8))\n        s.configure("GuideTitle.TLabel", background="#ffffff", foreground="#172033", font=("Segoe UI", 12, "bold"))\n        s.configure("GuideText.TLabel", background="#ffffff", foreground="#475569", font=("Segoe UI", 9))\n        s.configure("StatusBar.TFrame", background="#ffffff")\n'''
    new = '''        self.configure(bg="#F4F8FC")\n        s.configure("Treeview", rowheight=30, font=("Segoe UI", 9), background="#FFFFFF", fieldbackground="#FFFFFF", foreground="#243B53")\n        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(7, 8), background="#EAF3FA", foreground="#064A7A")\n        s.map("Treeview.Heading", background=[("active", "#DDECF7")])\n        s.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 7), background="#0875C9", foreground="#FFFFFF", bordercolor="#0875C9")\n        s.map("Accent.TButton", background=[("active", "#0767B2"), ("pressed", "#064A7A"), ("disabled", "#AFCBDE")], foreground=[("disabled", "#EEF6FB"), ("!disabled", "#FFFFFF")])\n        s.configure("Modern.TButton", font=("Segoe UI", 9), padding=(9, 6), background="#F7FAFC", foreground="#064A7A")\n        s.map("Modern.TButton", background=[("active", "#E8F4FB"), ("pressed", "#DCECF7")], foreground=[("!disabled", "#064A7A")])\n        s.configure("ModernHeader.TFrame", background="#FFFFFF")\n        s.configure("ModernPage.TFrame", background="#F4F8FC")\n        s.configure("ModernCard.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)\n        s.configure("ModernTitle.TLabel", background="#FFFFFF", foreground="#064A7A", font=("Segoe UI", 18, "bold"))\n        s.configure("ModernSubtitle.TLabel", background="#FFFFFF", foreground="#5D7185", font=("Segoe UI", 9))\n        s.configure("DashboardTitle.TLabel", background="#F4F8FC", foreground="#064A7A", font=("Segoe UI", 22, "bold"))\n        s.configure("DashboardText.TLabel", background="#F4F8FC", foreground="#5D7185", font=("Segoe UI", 10))\n        s.configure("CardLabel.TLabel", background="#FFFFFF", foreground="#5D7185", font=("Segoe UI", 9))\n        s.configure("CardValue.TLabel", background="#FFFFFF", foreground="#064A7A", font=("Segoe UI", 22, "bold"))\n        s.configure("CardNote.TLabel", background="#FFFFFF", foreground="#6B7F91", font=("Segoe UI", 8))\n        s.configure("GuideTitle.TLabel", background="#FFFFFF", foreground="#064A7A", font=("Segoe UI", 12, "bold"))\n        s.configure("GuideText.TLabel", background="#FFFFFF", foreground="#40576B", font=("Segoe UI", 9))\n        s.configure("StatusBar.TFrame", background="#FFFFFF")\n'''
    s = replace_once(s, old, new, 'modern style block')
    s = replace_once(s, '            badge = tk.Label(row, text=number, bg="#dbeafe", fg="#1d4ed8", font=("Segoe UI", 9, "bold"), width=3, pady=3)', '            badge = tk.Label(row, text=number, bg="#DDF2FF", fg="#0875C9", font=("Segoe UI", 9, "bold"), width=3, pady=3)', 'workflow step badge')

    old_nav = '''            button.configure(\n                bg="#e8f0ff" if active else "#ffffff",\n                fg="#1d4ed8" if active else "#334155",\n                activebackground="#e8f0ff" if active else "#f1f5f9",\n                activeforeground="#1d4ed8" if active else "#172033",\n                font=("Segoe UI", 10, "bold" if active else "normal"),\n            )\n'''
    new_nav = '''            button.configure(\n                bg="#0875C9" if active else "#064A7A",\n                fg="#FFFFFF" if active else "#DDEEFF",\n                activebackground="#0875C9" if active else "#075D99",\n                activeforeground="#FFFFFF",\n                font=("Segoe UI", 10, "bold" if active else "normal"),\n            )\n'''
    s = replace_once(s, old_nav, new_nav, 'navigation active style')
    s = replace_once(s, '        self.sidebar = tk.Frame(self.main_shell, bg="#ffffff", width=220, highlightthickness=1, highlightbackground="#e2e8f0")\n        self.sidebar.pack_propagate(False)\n        tk.Label(self.sidebar, text="WORKSPACE", bg="#ffffff", fg="#94a3b8", font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=16, pady=(18, 8))', '        self.sidebar = tk.Frame(self.main_shell, bg="#064A7A", width=220, highlightthickness=0)\n        self.sidebar.pack_propagate(False)\n        tk.Label(self.sidebar, text="WORKSPACE", bg="#064A7A", fg="#8ED8FF", font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=16, pady=(18, 8))', 'sidebar frame')
    s = s.replace('bg="#ffffff", fg="#334155", activebackground="#f1f5f9", activeforeground="#172033"', 'bg="#064A7A", fg="#DDEEFF", activebackground="#075D99", activeforeground="#FFFFFF"')
    s = s.replace('bg="#f4f7fb"', 'bg="#F4F8FC"')
    s = s.replace('highlightbackground="#e2e8f0"', 'highlightbackground="#D5E4F0"')
    s = s.replace('fg="#172033"', 'fg="#064A7A"')
    s = s.replace('fg="#334155"', 'fg="#243B53"')
    s = s.replace('fg="#64748b"', 'fg="#5D7185"')
    s = s.replace('bg="#dbeafe"', 'bg="#DDF2FF"').replace('fg="#1d4ed8"', 'fg="#0875C9"')
    s = s.replace('bg="#ecfdf5"', 'bg="#EAF6FF"').replace('fg="#166534"', 'fg="#064A7A"')
    path.write_text(s, encoding="utf-8")


def patch_walkthrough(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    insertion = '''\nR103_UPDATE_FEATURES = (\n    {\n        "id": "update_r103_ocean_blue",\n        "title": "A cleaner Ocean Blue interface",\n        "body": (\n            "R10.3 refreshes AUTOLEDGER with the Ocean Blue visual identity used by the official website. "\n            "Navigation, buttons, panels, edition status and the Guided Walkthrough now use a consistent Windows-first design."\n        ),\n    },\n    {\n        "id": "update_r103_professional_finish",\n        "title": "Production-ready presentation",\n        "body": (\n            "Customer-facing TEST and development wording has been removed. AUTOLEDGER now presents the product and revision cleanly "\n            "while preserving the same R10.2 accounting logic, Free limits, Pro entitlement compatibility and local data."\n        ),\n    },\n    {\n        "id": "update_r103_walkthrough_preserved",\n        "title": "The true Guided Walkthrough is preserved",\n        "body": (\n            "The R10.2 action-gated walkthrough remains in place: it points to real controls, keeps Back, Next and Skip Tutorial visible, "\n            "and waits for required actions before allowing the user to continue."\n        ),\n    },\n)\n'''
    anchor = 'R102_HELP_TOPICS = ('
    if insertion.strip() not in s:
        s = s.replace(anchor, insertion + '\n' + anchor, 1)
    old_register = '    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R102_UPDATE_FEATURES'
    new_register = '    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R103_UPDATE_FEATURES if revision.upper() == "R10.3" else R102_UPDATE_FEATURES'
    s = replace_once(s, old_register, new_register, 'R10.3 update curriculum')
    replacements = {
        'win.configure(bg="#f4f7fb")':'win.configure(bg="#F4F8FC")',
        'header = core.tk.Frame(win, bg="#0f2744", padx=14, pady=10)':'header = core.tk.Frame(win, bg="#064A7A", padx=14, pady=10)',
        'bg="#0f2744", fg="#9dd8cb"':'bg="#064A7A", fg="#8ED8FF"',
        'bg="#0f2744", fg="#ffffff"':'bg="#064A7A", fg="#FFFFFF"',
        'highlightbackground="#e2e8f0"':'highlightbackground="#D5E4F0"',
        'fg="#172033"':'fg="#064A7A"',
        'bg="#ffffff", fg="#334155"':'bg="#ffffff", fg="#243B53"',
        'footer = core.tk.Frame(win, bg="#f4f7fb", padx=10, pady=9)':'footer = core.tk.Frame(win, bg="#F4F8FC", padx=10, pady=9)',
        'nav = core.tk.Frame(footer, bg="#f4f7fb")':'nav = core.tk.Frame(footer, bg="#F4F8FC")',
        'pointer, text="▶  DO THIS NOW", bg="#f59e0b", fg="#111827"':'pointer, text="▶  DO THIS NOW", bg="#1EA4F2", fg="#FFFFFF"',
        'label.configure(bg="#fde047" if phase else "#f59e0b")':'label.configure(bg="#7DD3FC" if phase else "#1EA4F2")',
        'bg="#ecfdf5" if complete else "#fff7ed", fg="#166534" if complete else "#9a3412"':'bg="#EAF6FF" if complete else "#FFF7ED", fg="#064A7A" if complete else "#9A3412"',
        'bg="#fff7ed", fg="#9a3412"':'bg="#FFF7ED", fg="#9A3412"',
    }
    for old, new in replacements.items():
        if old not in s:
            raise RuntimeError(f"walkthrough styling anchor not found: {old}")
        s = s.replace(old, new)
    path.write_text(s, encoding="utf-8")


def patch_pro_runner(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    s = s.replace('# TEST-BUILD COMPATIBILITY:', '# LICENSING COMPATIBILITY:')
    s = s.replace('def require_test_entitlement():', 'def require_local_entitlement():')
    s = s.replace('"Unlock AUTOLEDGER Pro v2.2.5 R8 TEST",', '"Unlock AUTOLEDGER Pro",')
    s = s.replace('"This TEST build is using local entitlement validation until the "\n                    "production one-PC activation service is deployed.",', '"AUTOLEDGER will validate this permanent Pro entitlement on this PC. "\n                    "Your accounting and bank-statement data remain local.",')
    s = s.replace('"_activation_status": "r8-test-local-entitlement",', '"_activation_status": "local-entitlement",')
    s = s.replace('payload = {**payload, "_activation_status": "r8-test-local-entitlement"}', 'payload = {**payload, "_activation_status": "local-entitlement"}')
    s = s.replace('require_pro_licence() if ENFORCE_ONLINE_ACTIVATION else require_test_entitlement()', 'require_pro_licence() if ENFORCE_ONLINE_ACTIVATION else require_local_entitlement()')
    path.write_text(s, encoding="utf-8")


def patch_pro_licensing(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    s = s.replace('"User-Agent": "AUTOLEDGER-Pro/2.2.5-R8"', '"User-Agent": "AUTOLEDGER-Pro/2.2.5-R10.3"')
    s = s.replace('"app_version": "2.2.5 R8 UPDATE"', '"app_version": "2.2.5 R10.3"')
    path.write_text(s, encoding="utf-8")


def main(root: str) -> None:
    root = Path(root)
    for edition in ('free', 'pro'):
        app = root / edition
        patch_common(app / 'autoledger_common.py')
        patch_core(app / 'autoledger_core.py')
        patch_walkthrough(app / 'guided_walkthrough_r102.py')
    patch_pro_runner(root / 'pro' / 'pro_runner.pyw')
    patch_pro_licensing(root / 'pro' / 'pro_licensing.py')
    print(f'Applied R10.3 Ocean Blue transform to {root}')


if __name__ == '__main__':
    main(sys.argv[1])
