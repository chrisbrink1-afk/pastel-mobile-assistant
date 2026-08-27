from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import autoledger_core as core

PRODUCT_VERSION = "2.2.5"
COMPANY_NAME = "AUTOLEDGER SYSTEMS PTY LTD"


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
    core.APP_NAME = f"AUTOLEDGER {title}"
    core.APP_VERSION = f"{PRODUCT_VERSION} R6 TEST"
    core.APP_DATA_NAMESPACE = f"AUTOLEDGER_V225_TEST_{title}"
    core.APP_DATA_FALLBACK = f".autoledger_v225_test_{title.lower()}"
    core.DB_PATH = Path(core.app_data_dir()) / "pastel_payment_assistant.db"
    if hasattr(core, "TUTORIAL_TOPICS"):
        core.TUTORIAL_TOPICS = _replace_branding(core.TUTORIAL_TOPICS)


def _usage_path() -> Path:
    root = Path(core.app_data_dir())
    root.mkdir(parents=True, exist_ok=True)
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
    edition_title = "Free" if edition == "FREE" else "Pro"

    def edition_status_text():
        if edition == "FREE":
            _, remaining = free_usage_summary()
            return f"FREE  •  1 profile  •  {remaining}/100 entries remaining this month"
        customer = (licence_info or {}).get("customer") or "Licensed"
        return f"PRO  •  Unlimited profiles  •  Unlimited entries  •  {customer}"

    def show_edition_info(self):
        if edition == "FREE":
            used, remaining = free_usage_summary()
            text = (
                "AUTOLEDGER Free v2.2.5 R6 TEST\n\n"
                "1 company profile\n"
                f"{used}/100 statement entries used this month\n"
                f"{remaining} entries remaining\n\n"
                "Your financial data remains stored locally on this PC.\n\n"
                "Upgrade to AUTOLEDGER Pro for unlimited profiles and statement entries."
            )
        else:
            payload = licence_info or {}
            text = (
                "AUTOLEDGER Pro v2.2.5 R6 TEST\n\n"
                f"Licensed to: {payload.get('customer', 'Licensed user')}\n"
                f"Licence ID: {payload.get('license_id', '—')}\n\n"
                "Unlimited profiles\nUnlimited statement entries\n"
                "Local data storage\nOffline licence validation"
            )
        core.messagebox.showinfo(f"AUTOLEDGER {edition_title}", text, parent=self)

    def refresh_badge(self):
        var = getattr(self, "_autoledger_edition_status_var", None)
        if var is not None:
            try:
                var.set(edition_status_text())
            except Exception:
                pass

    def wrapped_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            self.title(f"AUTOLEDGER {edition_title} v{PRODUCT_VERSION} R6 TEST")
        except Exception:
            pass
        try:
            status_var = core.tk.StringVar(master=self, value=edition_status_text())
            self._autoledger_edition_status_var = status_var
            bg = "#E8F1FF" if edition == "FREE" else "#E7F6EC"
            fg = "#164A87" if edition == "FREE" else "#176B3A"
            badge = core.tk.Button(
                self, textvariable=status_var, command=lambda: show_edition_info(self),
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

    App.__init__ = wrapped_init
    App.show_edition_info = show_edition_info
    App._refresh_edition_badge = refresh_badge
    if original_header is not None:
        App._set_modern_page_header = wrapped_header
    if original_load_csv is not None:
        App.load_csv = wrapped_load_csv
    if original_refresh_profiles is not None:
        App._refresh_profile_ui = wrapped_refresh_profiles


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
    fake = {"customer": "R6 BUILD TEST", "license_id": "SMOKE"} if edition.upper() == "PRO" else None
    configure(edition, fake)
    app = core.App()
    try:
        app.withdraw()
        app.update_idletasks()
        expected = f"AUTOLEDGER {'Free' if edition.upper() == 'FREE' else 'Pro'}"
        if expected not in app.title():
            raise RuntimeError(f"Unexpected window title: {app.title()}")
    finally:
        app.destroy()
