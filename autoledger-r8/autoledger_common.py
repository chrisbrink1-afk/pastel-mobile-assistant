from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import autoledger_core as core

PRODUCT_VERSION = "2.2.5"
UPDATE_REVISION = "R8"
COMPANY_NAME = "AUTOLEDGER SYSTEMS PTY LTD"

# IMPORTANT UPDATE-COMPATIBILITY RULES:
# - Keep the same AppData namespaces as R6 so profiles/settings/usage persist.
# - Keep Free usage in free_usage_r6.json so an update cannot reset the allowance.
# - Pro licensing remains in pro_licence_r6.json and uses the same ALP225R6
#   signing lineage/public verifier. Normal updates must never force reactivation.


def _resource_path(relative: str) -> Path:
    """Return a bundled PyInstaller resource path or the development path."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def _replace_branding(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("Pastel Payment Assistant", "AUTOLEDGER")
    if isinstance(value, list):
        return [_replace_branding(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_replace_branding(v) for v in value)
    if isinstance(value, dict):
        return {k: _replace_branding(v) for k, v in value.items()}
    return value


def configure_common(edition: str) -> None:
    edition = edition.upper()
    title = "Free" if edition == "FREE" else "Pro"
    suffix = title
    core.APP_NAME = f"AUTOLEDGER {title}"
    core.APP_VERSION = f"{PRODUCT_VERSION} {UPDATE_REVISION} TEST"
    # Deliberately unchanged from R6: this is an in-place product update.
    core.APP_DATA_NAMESPACE = f"AUTOLEDGER_V225_TEST_{suffix}"
    core.APP_DATA_FALLBACK = f".autoledger_v225_test_{suffix.lower()}"
    core.DB_PATH = Path(core.app_data_dir()) / "pastel_payment_assistant.db"
    if hasattr(core, "TUTORIAL_TOPICS"):
        core.TUTORIAL_TOPICS = _replace_branding(core.TUTORIAL_TOPICS)


def _usage_path() -> Path:
    root = Path(core.app_data_dir())
    root.mkdir(parents=True, exist_ok=True)
    # Keep R6 filename so installing an update does not reset Free usage.
    return root / "free_usage_r6.json"


def _load_usage(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("months", {}), dict):
            return data
    except Exception:
        pass
    return {"version": 1, "months": {}}


def _save_usage(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def free_usage_summary() -> tuple[int, int]:
    limit = 100
    now = core.datetime.now()
    month_key = now.strftime("%Y-%m")
    usage = _load_usage(_usage_path())
    used = int(usage.get("months", {}).get(month_key, {}).get("used", 0) or 0)
    return used, max(0, limit - used)


def install_free_controls() -> None:
    limit = 100
    original_create_profile = core.ProfileManager.create_profile
    original_parser_load = core.BankCSVParser.load

    def free_create_profile(self, name):
        try:
            count = len(self.names)
        except Exception:
            count = 1
        if count >= 1:
            raise ValueError(
                "AUTOLEDGER Free supports one company profile. "
                "Upgrade to AUTOLEDGER Pro for unlimited profiles."
            )
        return original_create_profile(self, name)

    def free_new_profile(self):
        core.messagebox.showinfo(
            "AUTOLEDGER Free",
            "AUTOLEDGER Free supports one company profile.\n\n"
            "You can rename the existing Default profile for your company.\n\n"
            "Upgrade to AUTOLEDGER Pro for unlimited company profiles.",
            parent=self,
        )

    def limited_parser_load(path):
        result = original_parser_load(path)
        payments, receipts, parser_name = result
        entry_count = len(payments) + len(receipts)
        source = Path(path)
        try:
            file_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        except Exception:
            stat = source.stat()
            file_hash = hashlib.sha256(
                f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
            ).hexdigest()

        now = core.datetime.now()
        month_key = now.strftime("%Y-%m")
        usage_file = _usage_path()
        usage = _load_usage(usage_file)
        months = usage.setdefault("months", {})
        month = months.setdefault(month_key, {"used": 0, "statements": {}})
        statements = month.setdefault("statements", {})
        if file_hash in statements:
            return result

        used = int(month.get("used", 0) or 0)
        remaining = max(0, limit - used)
        if entry_count > remaining:
            raise RuntimeError(
                "AUTOLEDGER Free monthly limit reached.\n\n"
                f"This statement contains {entry_count} transaction entries, but only "
                f"{remaining} of {limit} entries remain for {now.strftime('%B %Y')}.\n\n"
                "The statement was NOT loaded or truncated. Upgrade to AUTOLEDGER Pro "
                "for unlimited statement transactions/entries."
            )

        statements[file_hash] = {
            "entries": entry_count,
            "filename": source.name,
            "processed_at": now.isoformat(timespec="seconds"),
        }
        month["used"] = used + entry_count
        for old_key in sorted(months.keys(), reverse=True)[6:]:
            months.pop(old_key, None)
        _save_usage(usage_file, usage)
        return result

    core.ProfileManager.create_profile = free_create_profile
    core.App.new_profile = free_new_profile
    core.BankCSVParser.load = staticmethod(limited_parser_load)


def install_edition_ui(edition: str, licence_info: dict | None = None) -> None:
    edition = edition.upper()
    App = core.App
    original_init = App.__init__
    original_header = getattr(App, "_set_modern_page_header", None)
    original_load_csv = getattr(App, "load_csv", None)
    original_refresh_profiles = getattr(App, "_refresh_profile_ui", None)
    original_start_tutorial = getattr(App, "start_tutorial", None)
    original_tutorial_show = getattr(App, "_tutorial_show_current", None)
    edition_title = "Free" if edition == "FREE" else "Pro"

    def edition_status_text():
        if edition == "FREE":
            _, remaining = free_usage_summary()
            return f"FREE  •  1 profile  •  {remaining}/100 entries remaining this month"
        customer = (licence_info or {}).get("customer") or "Licensed"
        return f"PRO  •  Unlimited profiles  •  Unlimited entries  •  {customer}"

    def show_pro_licence_manager(self):
        if edition != "PRO":
            return show_edition_info(self)
        from pro_licensing import deactivate_current_device

        payload = licence_info or {}
        win = core.tk.Toplevel(self)
        win.title("AUTOLEDGER Pro Licence")
        win.geometry("560x390")
        win.minsize(520, 350)
        win.transient(self)
        win.grab_set()
        win.configure(bg="#f4f7fb")
        try:
            icon_path = getattr(self, "_autoledger_icon_path", None)
            if icon_path:
                win.iconbitmap(default=icon_path)
        except Exception:
            pass

        panel = core.tk.Frame(win, bg="#ffffff", padx=22, pady=20, highlightthickness=1, highlightbackground="#e2e8f0")
        panel.pack(fill="both", expand=True, padx=18, pady=18)
        core.tk.Label(panel, text="AUTOLEDGER Pro Licence", bg="#ffffff", fg="#172033", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        core.tk.Label(
            panel,
            text=(
                f"Licensed to: {payload.get('customer', 'Licensed user')}\n"
                f"Licence ID: {payload.get('license_id', '—')}\n"
                f"Device: {payload.get('_device_name', 'This PC')}\n"
                f"Activation status: {payload.get('_activation_status', 'licensed')}\n"
                f"Valid offline until: {payload.get('_activation_valid_until', '—')}"
            ),
            bg="#ffffff", fg="#334155", font=("Segoe UI", 10), justify="left", anchor="w"
        ).pack(fill="x", pady=(14, 12))
        core.tk.Label(
            panel,
            text=(
                "One AUTOLEDGER Pro licence permits one active PC. Minor hardware changes such as RAM, SSD or graphics-card upgrades do not normally require a transfer. "
                "For a new PC or motherboard, deactivate this PC first, then install AUTOLEDGER Pro on the replacement PC and enter the SAME permanent Pro key."
            ),
            bg="#ffffff", fg="#64748b", font=("Segoe UI", 9), justify="left", anchor="w", wraplength=500
        ).pack(fill="x", pady=(0, 18))

        buttons = core.tk.Frame(panel, bg="#ffffff")
        buttons.pack(side="bottom", fill="x")
        core.ttk.Button(buttons, text="Close", command=win.destroy, style="Modern.TButton").pack(side="right")

        def transfer():
            ok = core.messagebox.askyesno(
                "Transfer AUTOLEDGER Pro licence",
                "Deactivate this PC so the SAME Pro licence can be activated on a replacement PC?\n\n"
                "AUTOLEDGER will close after successful deactivation. Your accounting data is not deleted.",
                parent=win,
            )
            if not ok:
                return
            if deactivate_current_device(parent=win):
                try:
                    win.destroy()
                except Exception:
                    pass
                self.after(150, self.destroy)

        core.ttk.Button(
            buttons, text="Deactivate / Transfer Licence", command=transfer, style="Accent.TButton"
        ).pack(side="right", padx=(0, 8))

    def show_edition_info(self):
        if edition == "FREE":
            used, remaining = free_usage_summary()
            text = (
                f"AUTOLEDGER Free v{PRODUCT_VERSION} {UPDATE_REVISION} TEST\n\n"
                "1 company profile\n"
                f"{used}/100 statement entries used this month\n"
                f"{remaining} entries remaining\n\n"
                "Your financial data remains stored locally on this PC.\n\n"
                "Upgrade to AUTOLEDGER Pro for unlimited profiles and statement entries."
            )
        else:
            payload = licence_info or {}
            text = (
                f"AUTOLEDGER Pro v{PRODUCT_VERSION} {UPDATE_REVISION} TEST\n\n"
                f"Licensed to: {payload.get('customer', 'Licensed user')}\n"
                f"Licence ID: {payload.get('license_id', '—')}\n\n"
                "Unlimited profiles\nUnlimited statement entries\n"
                "Local data storage\nOffline licence validation\n\n"
                "This update retains your existing AUTOLEDGER Pro licence."
            )
        core.messagebox.showinfo(f"AUTOLEDGER {edition_title}", text, parent=self)

    def refresh_badge(self):
        var = getattr(self, "_autoledger_edition_status_var", None)
        if var is not None:
            try:
                var.set(edition_status_text())
            except Exception:
                pass

    def _apply_brand_assets(self):
        """Install the supplied AUTOLEDGER logo/banner and Windows application icon."""
        try:
            icon_ico = _resource_path("assets/AUTOLEDGER_ICON.ico")
            if icon_ico.exists():
                self.iconbitmap(default=str(icon_ico))
                self._autoledger_icon_path = str(icon_ico)
        except Exception:
            pass

        # Modern header: replace the original text title block with the user's LOGO banner.
        try:
            modern_path = _resource_path("assets/AUTOLEDGER_LOGO_MODERN.png")
            profile_box = self.profile_combo_modern.master
            if modern_path.exists():
                children = list(self.modern_header.winfo_children())
                for child in children:
                    if child == profile_box:
                        break
                    try:
                        child.destroy()
                    except Exception:
                        pass
                self._autoledger_logo_modern = core.tk.PhotoImage(file=str(modern_path))
                label = core.tk.Label(
                    self.modern_header,
                    image=self._autoledger_logo_modern,
                    bg="#ffffff",
                    bd=0,
                    highlightthickness=0,
                )
                label.pack(side="left", before=profile_box, padx=(0, 16))
                self._autoledger_logo_modern_label = label
        except Exception:
            pass

        # Classic toolbar: replace the plain application-name text with a compact logo banner.
        try:
            classic_path = _resource_path("assets/AUTOLEDGER_LOGO_MODERN.png")
            profile_box = self.profile_combo_classic.master
            if classic_path.exists():
                for child in list(self.classic_toolbar.winfo_children()):
                    if child == profile_box:
                        break
                    try:
                        if child.winfo_class() in ("TLabel", "Label"):
                            child.destroy()
                    except Exception:
                        pass
                classic_source = core.tk.PhotoImage(file=str(classic_path))
                self._autoledger_logo_classic_source = classic_source
                self._autoledger_logo_classic = classic_source.subsample(2, 2)
                label = core.tk.Label(
                    self.classic_toolbar,
                    image=self._autoledger_logo_classic,
                    bd=0,
                    highlightthickness=0,
                )
                label.pack(side="left", before=profile_box, padx=(0, 12))
                self._autoledger_logo_classic_label = label
        except Exception:
            pass

    def _format_tutorial_navigation(self):
        """Keep Back/Next together at the lower-right in conventional order."""
        try:
            back = self.tutorial_back_button
            nxt = self.tutorial_next_button
            back.pack_forget()
            nxt.pack_forget()
            # With side='right', the first packed widget is closest to the right edge.
            # Pack Next first, then Back, to render: [Back] [Next] at lower right.
            nxt.pack(side="right", padx=(6, 0))
            back.pack(side="right")
            if back.cget("text") != "Back":
                back.configure(text="Back")
        except Exception:
            pass

    def wrapped_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            self.title(f"AUTOLEDGER {edition_title} v{PRODUCT_VERSION} {UPDATE_REVISION} TEST")
        except Exception:
            pass
        _apply_brand_assets(self)
        try:
            status_var = core.tk.StringVar(master=self, value=edition_status_text())
            self._autoledger_edition_status_var = status_var
            bg = "#E8F1FF" if edition == "FREE" else "#E7F6EC"
            fg = "#164A87" if edition == "FREE" else "#176B3A"
            badge = core.tk.Button(
                self, textvariable=status_var, command=(lambda: show_pro_licence_manager(self)) if edition == "PRO" else (lambda: show_edition_info(self)),
                relief="solid", borderwidth=1, padx=10, pady=4,
                bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                font=("Segoe UI", 9, "bold"), cursor="hand2",
            )
            badge.place(relx=1.0, rely=1.0, x=-12, y=-10, anchor="se")
            badge.lift()
            self._autoledger_edition_badge = badge
        except Exception:
            pass

    def wrapped_header(self, title, subtitle):
        return original_header(self, title, f"{subtitle}   •   {edition_status_text()}")

    def wrapped_load_csv(self, *args, **kwargs):
        try:
            return original_load_csv(self, *args, **kwargs)
        finally:
            refresh_badge(self)

    def wrapped_refresh_profiles(self, *args, **kwargs):
        try:
            return original_refresh_profiles(self, *args, **kwargs)
        finally:
            refresh_badge(self)

    def wrapped_start_tutorial(self, *args, **kwargs):
        result = original_start_tutorial(self, *args, **kwargs)
        _format_tutorial_navigation(self)
        return result

    def wrapped_tutorial_show(self, *args, **kwargs):
        result = original_tutorial_show(self, *args, **kwargs)
        _format_tutorial_navigation(self)
        return result

    App.__init__ = wrapped_init
    App.show_edition_info = show_edition_info
    App.show_pro_licence_manager = show_pro_licence_manager
    App._refresh_edition_badge = refresh_badge
    App._apply_autoledger_brand_assets = _apply_brand_assets
    App._format_autoledger_tutorial_navigation = _format_tutorial_navigation
    if original_header is not None:
        App._set_modern_page_header = wrapped_header
    if original_load_csv is not None:
        App.load_csv = wrapped_load_csv
    if original_refresh_profiles is not None:
        App._refresh_profile_ui = wrapped_refresh_profiles
    if original_start_tutorial is not None:
        App.start_tutorial = wrapped_start_tutorial
    if original_tutorial_show is not None:
        App._tutorial_show_current = wrapped_tutorial_show


def configure(edition: str, licence_info: dict | None = None) -> None:
    configure_common(edition)
    if edition.upper() == "FREE":
        install_free_controls()
    install_edition_ui(edition, licence_info)


def run_app(edition: str, licence_info: dict | None = None) -> None:
    configure(edition, licence_info)
    app = core.App()
    app.mainloop()


def smoke_test(edition: str) -> None:
    fake = {"customer": "R8 BUILD TEST", "license_id": "SMOKE"} if edition.upper() == "PRO" else None
    configure(edition, fake)
    app = core.App()
    try:
        app.withdraw()
        app.update_idletasks()
        expected = f"AUTOLEDGER {'Free' if edition.upper() == 'FREE' else 'Pro'}"
        if expected not in app.title() or "R8" not in app.title():
            raise RuntimeError(f"Unexpected window title: {app.title()}")
        if not hasattr(app, "_autoledger_logo_modern"):
            raise RuntimeError("Modern AUTOLEDGER logo banner was not loaded")
        if not hasattr(app, "_autoledger_icon_path"):
            raise RuntimeError("AUTOLEDGER window icon was not loaded")
        # Prove the requested tutorial navigation exists in the finished app.
        if hasattr(app, "start_tutorial"):
            app.start_tutorial(auto=False)
            app.update_idletasks()
            if not hasattr(app, "tutorial_back_button") or not hasattr(app, "tutorial_next_button"):
                raise RuntimeError("Tutorial Back/Next controls are missing")
            if app.tutorial_back_button.winfo_manager() != "pack" or app.tutorial_next_button.winfo_manager() != "pack":
                raise RuntimeError("Tutorial Back/Next controls are not visible")
            try:
                app._tutorial_close()
            except Exception:
                pass
    finally:
        app.destroy()
