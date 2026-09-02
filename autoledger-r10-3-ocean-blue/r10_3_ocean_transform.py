from pathlib import Path
import sys


def require_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"{label}: required anchor not found")
    return text.replace(old, new, 1)


def patch_common(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    s = require_replace(s, 'UPDATE_REVISION = "R10.2"', 'UPDATE_REVISION = "R10.3"', 'revision')
    s = require_replace(s, 'core.APP_VERSION = f"{PRODUCT_VERSION} {UPDATE_REVISION} TEST"', 'core.APP_VERSION = f"{PRODUCT_VERSION} {UPDATE_REVISION}"', 'visible app version')
    s = s.replace('f"AUTOLEDGER Free v{PRODUCT_VERSION} {UPDATE_REVISION} TEST\\n\\n"', 'f"AUTOLEDGER Free v{PRODUCT_VERSION} {UPDATE_REVISION}\\n\\n"')
    s = s.replace('f"AUTOLEDGER Pro v{PRODUCT_VERSION} {UPDATE_REVISION} TEST\\n\\n"', 'f"AUTOLEDGER Pro v{PRODUCT_VERSION} {UPDATE_REVISION}\\n\\n"')
    s = s.replace('self.title(f"AUTOLEDGER {edition_title} v{PRODUCT_VERSION} {UPDATE_REVISION} TEST")', 'self.title(f"AUTOLEDGER {edition_title} v{PRODUCT_VERSION} {UPDATE_REVISION}")')
    s = s.replace('{"customer": "R10.2 BUILD TEST", "license_id": "SMOKE"}', '{"customer": "R10.3 SMOKE", "license_id": "SMOKE"}')
    s = s.replace('if expected not in app.title() or "R10" not in app.title():', 'if expected not in app.title() or UPDATE_REVISION not in app.title():')

    # Keep the R6-era namespaces and filenames exactly as-is for upgrade continuity.
    if 'AUTOLEDGER_V225_TEST_' not in s or 'free_usage_r6.json' not in s:
        raise RuntimeError('R6-era data compatibility markers are missing')

    # Edition badge and licence-manager styling.
    s = s.replace('bg = "#E8F1FF" if edition == "FREE" else "#E7F6EC"', 'bg = "#EAF6FF" if edition == "FREE" else "#DDF2FF"')
    s = s.replace('fg = "#164A87" if edition == "FREE" else "#176B3A"', 'fg = "#064A7A"')
    for old, new in {
        '#f4f7fb':'#F4F8FC',
        '#e2e8f0':'#D5E4F0',
        '#172033':'#064A7A',
        '#334155':'#243B53',
        '#64748b':'#5D7185',
    }.items():
        s = s.replace(old, new)

    # Windows uses the ICO; PNG fallback also keeps source/UI smoke tests portable.
    old_icon = '''        try:\n            icon_ico = _resource_path("assets/AUTOLEDGER_ICON.ico")\n            if icon_ico.exists():\n                self.iconbitmap(default=str(icon_ico))\n                self._autoledger_icon_path = str(icon_ico)\n        except Exception:\n            pass\n'''
    new_icon = '''        icon_loaded = False\n        try:\n            icon_ico = _resource_path("assets/AUTOLEDGER_ICON.ico")\n            if icon_ico.exists():\n                self.iconbitmap(default=str(icon_ico))\n                self._autoledger_icon_path = str(icon_ico)\n                icon_loaded = True\n        except Exception:\n            pass\n        if not icon_loaded:\n            try:\n                icon_png = _resource_path("assets/AUTOLEDGER_ICON.png")\n                if icon_png.exists():\n                    self._autoledger_icon_photo = core.tk.PhotoImage(file=str(icon_png))\n                    self.iconphoto(True, self._autoledger_icon_photo)\n                    self._autoledger_icon_path = str(icon_png)\n            except Exception:\n                pass\n'''
    s = require_replace(s, old_icon, new_icon, 'brand icon loading')

    if 'R10.3 TEST' in s:
        raise RuntimeError('customer-facing R10.3 TEST wording remains in common source')
    path.write_text(s, encoding="utf-8")


def patch_core(path: Path) -> None:
    s = path.read_text(encoding="utf-8")

    # Remove working-draft wording and align product description to the approved website scope.
    s = s.replace(
        'self.status_var.set("v2.2 Clean feedback build — no personal data was bundled. The adaptive Tutorial & Help will open automatically for a genuinely new workspace and can be run again at any time.")',
        'self.status_var.set("Ready. Select the correct company profile, confirm Settings, then load a bank CSV to begin.")'
    )
    s = s.replace(
        'ttk.Label(title_box, text=f"v{APP_VERSION} Clean feedback workspace", style="ModernSubtitle.TLabel").pack(anchor="w")',
        'ttk.Label(title_box, text=f"v{APP_VERSION}  •  General Ledger payments & receipts", style="ModernSubtitle.TLabel").pack(anchor="w")'
    )

    # Ocean Blue base palette. These are intentionally broad presentation-only replacements.
    colours = {
        '#f4f7fb':'#F4F8FC',
        '#eef3f8':'#EAF3FA',
        '#e2e8f0':'#D5E4F0',
        '#172033':'#064A7A',
        '#334155':'#243B53',
        '#64748b':'#5D7185',
        '#475569':'#40576B',
        '#2563eb':'#0875C9',
        '#1d4ed8':'#0767B2',
        '#1e40af':'#064A7A',
        '#dbeafe':'#DDF2FF',
        '#e8f0ff':'#E8F4FB',
        '#ecfdf5':'#EAF6FF',
        '#166534':'#064A7A',
        '#0f766e':'#0875C9',
        '#9dd8cb':'#8ED8FF',
    }
    for old, new in colours.items():
        s = s.replace(old, new)

    # Sidebar is deliberately a dark Windows-style navigation rail.
    sidebar_old = 'self.sidebar = tk.Frame(self.main_shell, bg="#ffffff", width=220, highlightthickness=1, highlightbackground="#D5E4F0")'
    sidebar_new = 'self.sidebar = tk.Frame(self.main_shell, bg="#064A7A", width=220, highlightthickness=0)'
    s = require_replace(s, sidebar_old, sidebar_new, 'sidebar frame')

    # The R10.2 source has changed its padding a few times; patch only the label styling, not spacing.
    s = s.replace('tk.Label(self.sidebar, text="WORKSPACE", bg="#ffffff", fg="#94a3b8"', 'tk.Label(self.sidebar, text="WORKSPACE", bg="#064A7A", fg="#8ED8FF"')
    s = s.replace('bg="#ffffff", fg="#243B53", activebackground="#f1f5f9", activeforeground="#064A7A"', 'bg="#064A7A", fg="#DDEEFF", activebackground="#075D99", activeforeground="#FFFFFF"')
    s = s.replace('bg="#ffffff", fg="#0875C9", activebackground="#EAF6FF", activeforeground="#0875C9"', 'bg="#064A7A", fg="#8ED8FF", activebackground="#075D99", activeforeground="#FFFFFF"')
    s = s.replace('tk.Frame(self.sidebar, bg="#D5E4F0"', 'tk.Frame(self.sidebar, bg="#2F75A3"')
    s = s.replace('tk.Label(self.sidebar, text="ACTIVE COMPANY", bg="#ffffff", fg="#94a3b8"', 'tk.Label(self.sidebar, text="ACTIVE COMPANY", bg="#064A7A", fg="#8ED8FF"')
    s = s.replace('tk.Label(self.sidebar, textvariable=self.profile_var, bg="#ffffff", fg="#064A7A"', 'tk.Label(self.sidebar, textvariable=self.profile_var, bg="#064A7A", fg="#FFFFFF"')
    s = s.replace('tk.Label(self.sidebar, text="Modern and Classic views use the same company data.", bg="#ffffff", fg="#5D7185"', 'tk.Label(self.sidebar, text="Modern and Classic views use the same company data.", bg="#064A7A", fg="#B8DDF2"')

    # Active navigation state: selected item becomes the primary Ocean Blue.
    old_nav = '''            button.configure(\n                bg="#E8F4FB" if active else "#ffffff",\n                fg="#0767B2" if active else "#243B53",\n                activebackground="#E8F4FB" if active else "#f1f5f9",\n                activeforeground="#0767B2" if active else "#064A7A",\n                font=("Segoe UI", 10, "bold" if active else "normal"),\n            )\n'''
    new_nav = '''            button.configure(\n                bg="#0875C9" if active else "#064A7A",\n                fg="#FFFFFF" if active else "#DDEEFF",\n                activebackground="#0875C9" if active else "#075D99",\n                activeforeground="#FFFFFF",\n                font=("Segoe UI", 10, "bold" if active else "normal"),\n            )\n'''
    if old_nav in s:
        s = s.replace(old_nav, new_nav, 1)

    # Ttk button/theme definitions need an explicit accent value for Windows clam/vista fallbacks.
    s = s.replace('background="#0875C9", foreground="#ffffff"', 'background="#0875C9", foreground="#FFFFFF"')
    s = s.replace('background=[("active", "#0767B2"), ("pressed", "#064A7A")]', 'background=[("active", "#0767B2"), ("pressed", "#064A7A")]')

    if 'Clean feedback workspace' in s or 'Clean feedback build' in s:
        raise RuntimeError('development feedback wording remains in core source')
    if '#064A7A' not in s or '#0875C9' not in s:
        raise RuntimeError('Ocean Blue core palette was not applied')
    path.write_text(s, encoding="utf-8")


def patch_walkthrough(path: Path) -> None:
    s = path.read_text(encoding="utf-8")

    # R10.3 has its own update curriculum while keeping every R10.2 action/gate mechanic.
    anchor = 'R102_HELP_TOPICS = ('
    curriculum = '''R103_UPDATE_FEATURES = (\n    {\n        "id": "update_r103_ocean_blue",\n        "title": "A cleaner Ocean Blue interface",\n        "body": (\n            "R10.3 refreshes AUTOLEDGER with the Ocean Blue visual identity used by the official website. "\n            "Navigation, buttons, panels, edition status and the Guided Walkthrough now use a consistent Windows-first design."\n        ),\n    },\n    {\n        "id": "update_r103_professional_finish",\n        "title": "Production-ready presentation",\n        "body": (\n            "Customer-facing TEST and development wording has been removed. AUTOLEDGER now presents the product and revision cleanly "\n            "while preserving the same R10.2 accounting logic, Free limits, Pro entitlement compatibility and local data."\n        ),\n    },\n    {\n        "id": "update_r103_walkthrough_preserved",\n        "title": "The true Guided Walkthrough is preserved",\n        "body": (\n            "The R10.2 action-gated walkthrough remains in place: it points to real controls, keeps Back, Next and Skip Tutorial visible, "\n            "and waits for required actions before allowing the user to continue."\n        ),\n    },\n)\n\n'''
    if 'R103_UPDATE_FEATURES' not in s:
        s = require_replace(s, anchor, curriculum + anchor, 'R10.3 curriculum anchor')
    s = require_replace(
        s,
        'guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R102_UPDATE_FEATURES',
        'guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R103_UPDATE_FEATURES if revision.upper() == "R10.3" else R102_UPDATE_FEATURES',
        'revision curriculum registration'
    )

    for old, new in {
        '#f4f7fb':'#F4F8FC',
        '#0f2744':'#064A7A',
        '#9dd8cb':'#8ED8FF',
        '#e2e8f0':'#D5E4F0',
        '#172033':'#064A7A',
        '#334155':'#243B53',
        '#f59e0b':'#1EA4F2',
        '#fde047':'#7DD3FC',
        '#166534':'#064A7A',
    }.items():
        s = s.replace(old, new)
    s = s.replace('text="▶  DO THIS NOW", bg="#1EA4F2", fg="#111827"', 'text="▶  DO THIS NOW", bg="#1EA4F2", fg="#FFFFFF"')
    s = s.replace('bg="#ecfdf5" if complete else "#fff7ed", fg="#064A7A" if complete else "#9a3412"', 'bg="#EAF6FF" if complete else "#FFF7ED", fg="#064A7A" if complete else "#9A3412"')
    s = s.replace('bg="#fff7ed", fg="#9a3412"', 'bg="#FFF7ED", fg="#9A3412"')

    if '#1EA4F2' not in s or '#064A7A' not in s:
        raise RuntimeError('Ocean Blue walkthrough palette was not applied')
    path.write_text(s, encoding="utf-8")


def patch_pro_runner(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    s = s.replace('# TEST-BUILD COMPATIBILITY:', '# LICENSING COMPATIBILITY:')
    s = s.replace('def require_test_entitlement():', 'def require_local_entitlement():')
    s = s.replace('"Unlock AUTOLEDGER Pro v2.2.5 R8 TEST",', '"Unlock AUTOLEDGER Pro",')
    s = s.replace(
        '"This TEST build is using local entitlement validation until the "\n                    "production one-PC activation service is deployed.",',
        '"AUTOLEDGER will validate this permanent Pro entitlement on this PC. "\n                    "Your accounting and bank-statement data remain local.",'
    )
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
    print(f'Applied robust R10.3 Ocean Blue transform to {root}')


if __name__ == '__main__':
    main(sys.argv[1])
