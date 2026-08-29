from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

GUIDED_TUTORIAL_REVISION = "R10"
GUIDED_TUTORIAL_STATE_FILE = "guided_tutorial_state.json"
INSTALL_CONTEXT_FILE = "install_context_r10.json"

# PERMANENT UPDATE RULE:
# Every future AUTOLEDGER revision must add its new/changed features here.
# CI must reject a revision that has no update-feature curriculum.
UPDATE_FEATURES_BY_REVISION = {
    "R10": (
        {
            "id": "update_guided_tutorial",
            "title": "Interactive guided tutorial",
            "body": (
                "R10 introduces a step-by-step guided tutorial. AUTOLEDGER now points to the control you must use, "
                "explains what it means in plain language, and keeps Next locked until the required action is complete. "
                "You can still choose Skip tutorial at any time."
            ),
        },
        {
            "id": "update_version_aware",
            "title": "Tutorials now understand updates",
            "body": (
                "After a software update, AUTOLEDGER shows NEW IN THIS UPDATE first. A clean installation never shows that "
                "heading. Future releases must add their new or changed features to this update section before release."
            ),
        },
        {
            "id": "update_help_complete",
            "title": "Tutorial and searchable Help work together",
            "body": (
                "The guided tutorial teaches the normal workflow. Searchable Help remains the full reference for every "
                "button, field, option, warning and feature, including Priority and rule matching."
            ),
        },
    ),
}

EXTRA_HELP_TOPICS = (
    {
        "id": "guided_tutorial",
        "title": "Interactive Guided Tutorial",
        "page": "dashboard",
        "keywords": "guided tutorial beginner first install step by step animated arrow next locked",
        "body": (
            "The Guided Tutorial walks a new user from company-profile setup through Settings, loading a bank CSV, "
            "reviewing transactions, creating a saved rule, validation and Pastel export. An animated pointer shows the "
            "control to use. Next stays disabled on required-action steps until AUTOLEDGER can confirm the action is complete. "
            "Skip tutorial is always available."
        ),
    },
    {
        "id": "tutorial_after_update",
        "title": "NEW IN THIS UPDATE tutorial",
        "page": "dashboard",
        "keywords": "new in this update updated version upgrade tutorial first screen",
        "body": (
            "When AUTOLEDGER detects that an older installation has been updated, the first guided-tutorial screen is "
            "NEW IN THIS UPDATE. It explains the new or changed features before the normal workflow refresher. A clean "
            "installation does not show NEW IN THIS UPDATE because that wording would confuse a first-time user."
        ),
    },
    {
        "id": "tutorial_examples",
        "title": "Example values used by the tutorial",
        "page": "settings",
        "keywords": "tutorial example 8400000 cash book gl tax type vat fiscal month test values",
        "body": (
            "Tutorial values are examples only. For practice, the tutorial may suggest 8400000 as an example Cash Book bank "
            "GL, tax type 1 as an example whole-number Pastel tax type, VAT rate 15%, and fiscal start month 3. Your real "
            "Pastel company may use different account and tax codes. Confirm the real values in Pastel before processing live data."
        ),
    },
    {
        "id": "tutorial_completion_gates",
        "title": "Why Next is sometimes disabled in the tutorial",
        "page": "dashboard",
        "keywords": "next disabled locked cannot continue complete action tutorial gate",
        "body": (
            "On a required-action tutorial step, Next remains disabled until AUTOLEDGER detects the required result. Examples "
            "include renaming/creating the company profile, saving essential settings, loading a CSV, having a usable saved "
            "rule, passing validation and completing a Pastel export. This prevents a first-time user from clicking through "
            "instructions without doing the setup."
        ),
    },
    {
        "id": "run_tutorial_again",
        "title": "Run the Guided Tutorial again",
        "page": "dashboard",
        "keywords": "run tutorial again restart guided tutorial help",
        "body": (
            "Open Tutorial & Help and choose Run Guided Tutorial to start the complete guided workflow again. Manual runs use "
            "the normal beginner workflow and do not pretend that a clean installation is an update."
        ),
    },
)


def guided_step_ids(mode: str, revision: str = GUIDED_TUTORIAL_REVISION) -> list[str]:
    """Pure helper used by CI to prove clean/update ordering."""
    mode = (mode or "clean").lower()
    ids: list[str] = []
    if mode == "update":
        ids.append("update_intro")
        ids.extend(item["id"] for item in UPDATE_FEATURES_BY_REVISION.get(revision, ()))
    ids.extend([
        "welcome",
        "profile",
        "cashbook_gl",
        "vat_tax_type",
        "vat_rate",
        "fiscal_month",
        "project_code",
        "save_settings",
        "load_csv",
        "review_transaction",
        "create_rule",
        "rule_result",
        "select_export",
        "validate",
        "export",
        "complete",
    ])
    return ids


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def install_guided_tutorial(core, edition: str, licence_info=None, revision: str = GUIDED_TUTORIAL_REVISION) -> None:
    """Install the R10 interactive tutorial without changing accounting logic."""
    if revision not in UPDATE_FEATURES_BY_REVISION or not UPDATE_FEATURES_BY_REVISION[revision]:
        raise RuntimeError(f"{revision} has no NEW IN THIS UPDATE curriculum. Release blocked.")

    # Searchable Help must document the guided tutorial itself.
    existing_ids = {t.get("id") for t in getattr(core, "TUTORIAL_TOPICS", ())}
    topics = list(getattr(core, "TUTORIAL_TOPICS", ()))
    for topic in EXTRA_HELP_TOPICS:
        if topic["id"] not in existing_ids:
            topics.append(dict(topic))
    core.TUTORIAL_TOPICS = tuple(topics)

    App = core.App
    original_help = getattr(App, "start_tutorial", None)
    original_show_validation = getattr(App, "show_validation", None)
    original_export_files = getattr(App, "export_files", None)
    original_refresh_profiles = getattr(App, "_refresh_profile_ui", None)

    def _state_path(self) -> Path:
        return Path(core.app_data_dir()) / GUIDED_TUTORIAL_STATE_FILE

    def _context_path(self) -> Path:
        return Path(core.app_data_dir()) / INSTALL_CONTEXT_FILE

    def _classify_install_mode(self) -> str:
        context = _read_json(_context_path(self))
        if str(context.get("revision", "")).upper() == revision.upper():
            kind = str(context.get("install_kind", "")).lower()
            if kind in {"clean", "update"}:
                return kind
        # Fallback for an older installation updated before the installer marker existed.
        try:
            snap = core.tutorial_workspace_snapshot(self.store, self.txns, self.receipts)
            old_tutorial = (self.store.get_setting(getattr(core, "TUTORIAL_SETTING_KEY", "__tutorial_v2_state"), "") or "").strip()
            if snap.get("has_activity") or old_tutorial:
                return "update"
        except Exception:
            pass
        return "clean"

    def _should_auto_start_guided(self) -> bool:
        state = _read_json(_state_path(self))
        return str(state.get("last_prompted_revision", "")).upper() != revision.upper()

    def _record_guided_state(self, outcome: str, mode: str) -> None:
        state = _read_json(_state_path(self))
        state.update({
            "version": 1,
            "last_prompted_revision": revision,
            "last_outcome": outcome,
            "last_mode": mode,
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        _write_json(_state_path(self), state)

    def _guided_snapshot(self) -> dict:
        try:
            snap = core.tutorial_workspace_snapshot(self.store, self.txns, self.receipts)
        except Exception:
            snap = {}
        try:
            snap["profile_name"] = self.profile_manager.profile_name(self.active_profile_id)
        except Exception:
            snap["profile_name"] = ""
        try:
            snap["rule_count"] = len(self.store.all_rules())
        except Exception:
            snap["rule_count"] = 0
        return snap

    def _setting(self, key: str, default: str = "") -> str:
        try:
            return (self.setting_vars[key].get() or "").strip()
        except Exception:
            try:
                return (self.store.get_setting(key, default) or "").strip()
            except Exception:
                return default

    def _selected_transaction_exists(self) -> bool:
        for direction in ("PAYMENT", "RECEIPT"):
            try:
                tree = self.trees.get(direction)
                if tree is not None and tree.selection():
                    return True
            except Exception:
                pass
        return False

    def _has_export_ready_row(self) -> bool:
        try:
            return any(t.include and t.account and not t.ambiguous for t in (self.txns + self.receipts))
        except Exception:
            return False

    def _settings_saved(self) -> bool:
        for key, default in (
            ("contra_account", ""),
            ("vat_tax_type", ""),
            ("vat_rate", "15"),
            ("fiscal_start_month", "3"),
            ("project_code", ""),
        ):
            try:
                if (self.store.get_setting(key, default) or "").strip() != _setting(self, key, default):
                    return False
            except Exception:
                return False
        return True

    def _step_definition(self, step_id: str) -> dict:
        update_lookup = {x["id"]: x for x in UPDATE_FEATURES_BY_REVISION.get(revision, ())}
        if step_id in update_lookup:
            item = update_lookup[step_id]
            return {"title": item["title"], "body": item["body"], "page": "dashboard", "target": (), "gate": lambda: True}

        def whole_number(value: str) -> bool:
            try:
                int(value)
                return True
            except Exception:
                return False

        def valid_rate() -> bool:
            try:
                return float(_setting(self, "vat_rate", "15")) > 0
            except Exception:
                return False

        def valid_month() -> bool:
            try:
                return 1 <= int(_setting(self, "fiscal_start_month", "3")) <= 12
            except Exception:
                return False

        defs = {
            "update_intro": {
                "title": "NEW IN THIS UPDATE",
                "body": (
                    f"AUTOLEDGER has been updated to {revision}. Before the normal tutorial, we will show you the new or changed "
                    "features in this revision. This heading is shown only after an update; a clean installation never sees it."
                ),
                "page": "dashboard", "target": (), "gate": lambda: True,
            },
            "welcome": {
                "title": "Welcome — we will do this together",
                "body": (
                    "This tutorial takes you through a real AUTOLEDGER workflow one step at a time. Do the highlighted action in "
                    "the main AUTOLEDGER window. On required steps, Next unlocks only after the action is complete. You may choose "
                    "Skip tutorial at any time and run it again later from Tutorial & Help."
                ),
                "page": "dashboard", "target": ("Tutorial & Help",), "gate": lambda: True,
            },
            "profile": {
                "title": "Step 1 — Set up the company profile",
                "body": (
                    "A profile keeps one company's settings, saved rules and history separate from another company. If this is the "
                    "Default profile, rename it to your company name. AUTOLEDGER Pro can also create another profile with New. "
                    "For Free, rename the single Default profile. Next unlocks when the active profile is no longer named Default."
                ),
                "page": "dashboard", "target": ("Rename", "New"),
                "gate": lambda: bool(_guided_snapshot(self).get("profile_name")) and _guided_snapshot(self).get("profile_name", "").strip().casefold() != "default",
            },
            "cashbook_gl": {
                "title": "Step 2 — Enter the Cash Book bank GL",
                "body": (
                    "Open Settings and enter the Pastel General Ledger account linked to this bank/cash book. Tutorial example: "
                    "8400000. This is an example only — your real Pastel company may use a different bank GL. The field must contain "
                    "a value no longer than 7 characters before Next unlocks."
                ),
                "page": "settings", "target": ("Cash Book bank GL account",),
                "gate": lambda: bool(_setting(self, "contra_account")) and len(_setting(self, "contra_account")) <= 7,
            },
            "vat_tax_type": {
                "title": "Step 3 — Enter the Pastel VAT tax type",
                "body": (
                    "Enter the whole-number tax type used by this Pastel company. Tutorial example: 1. Pastel tax-type numbering can "
                    "differ between companies, so confirm the real code in Pastel before processing live transactions. Next unlocks "
                    "when a whole number has been entered."
                ),
                "page": "settings", "target": ("VAT tax type number",),
                "gate": lambda: whole_number(_setting(self, "vat_tax_type")),
            },
            "vat_rate": {
                "title": "Step 4 — Confirm the VAT rate",
                "body": (
                    "Confirm the VAT percentage AUTOLEDGER should use for VAT-inclusive calculations. A common South African example "
                    "is 15%. Change it only if the company/period requires another rate. Next unlocks when the value is a positive number."
                ),
                "page": "settings", "target": ("VAT rate",), "gate": valid_rate,
            },
            "fiscal_month": {
                "title": "Step 5 — Confirm the fiscal year start month",
                "body": (
                    "Enter the month number in which the Pastel financial year starts. Tutorial example: 3 for March. AUTOLEDGER uses "
                    "this to calculate Pastel periods 1 to 12. Confirm the real year start in Pastel Setup → Periods."
                ),
                "page": "settings", "target": ("Fiscal year start month",), "gate": valid_month,
            },
            "project_code": {
                "title": "Step 6 — Project code is optional",
                "body": (
                    "If the Pastel company uses a project/cost code, enter it here (maximum 5 characters). If it does not use projects, "
                    "leave the field blank. Blank is a valid completed choice, so you may continue after checking this setting."
                ),
                "page": "settings", "target": ("Project code",),
                "gate": lambda: len(_setting(self, "project_code")) <= 5,
            },
            "save_settings": {
                "title": "Step 7 — Save the profile settings",
                "body": (
                    "Click Save settings. This writes the values you just checked to the active company profile. Next unlocks only when "
                    "the stored settings match the values currently shown on screen."
                ),
                "page": "settings", "target": ("Save settings",), "gate": lambda: _settings_saved(self),
            },
            "load_csv": {
                "title": "Step 8 — Load the bank CSV",
                "body": (
                    "Click Load bank CSV / Load statement and choose the CSV exported by your bank. A CSV is a spreadsheet-style text "
                    "file containing the statement transactions. AUTOLEDGER separates money out into Payments and money in into Receipts. "
                    "Next unlocks only after at least one transaction has loaded successfully."
                ),
                "page": "dashboard", "target": ("Load bank CSV", "Load statement"),
                "gate": lambda: bool(getattr(self, "txns", None) or getattr(self, "receipts", None)),
            },
            "review_transaction": {
                "title": "Step 9 — Select a transaction to work with",
                "body": (
                    "Open Payments (or Receipts if the CSV has only money in) and click one transaction row. Read its Date, bank details, "
                    "Amount, GL, VAT, Rule and Status. Orange/unassigned means it still needs a usable GL allocation. Next unlocks after "
                    "you select a transaction row."
                ),
                "page": "payments" if getattr(self, "txns", None) else "receipts", "target": ("Payments", "Receipts"),
                "gate": lambda: _selected_transaction_exists(self),
            },
            "create_rule": {
                "title": "Step 10 — Create or confirm a saved rule",
                "body": (
                    "With a transaction selected, use Save rule from selected. A rule tells AUTOLEDGER how the same type of transaction "
                    "should be allocated in future. Check Rule name, Name/number to match, Matching method, GL, VAT/tax type and Priority. "
                    "Leave normal Priority at 100. Use 200 or 300 only when a more specific rule must beat a broader rule. Next unlocks "
                    "when the active profile has at least one saved rule."
                ),
                "page": "payments" if getattr(self, "txns", None) else "receipts", "target": ("Save rule from selected",),
                "gate": lambda: int(_guided_snapshot(self).get("rule_count") or 0) > 0,
            },
            "rule_result": {
                "title": "Step 11 — See what the rule did",
                "body": (
                    "AUTOLEDGER reapplies saved rules to the loaded statement. Check the transaction's GL, description, VAT and Rule/Status. "
                    "If it is wrong, use Correct auto-allocation rather than accepting a bad result. Next unlocks when there is at least "
                    "one selected, allocated, non-ambiguous transaction available for export."
                ),
                "page": "payments" if getattr(self, "txns", None) else "receipts", "target": ("Correct auto-allocation",),
                "gate": lambda: _has_export_ready_row(self),
            },
            "select_export": {
                "title": "Step 12 — Choose what will be exported",
                "body": (
                    "Only ticked transactions are included in the next export. Use Add Auto-Allocated and/or Add Manual Allocations when "
                    "appropriate. Those buttons are additive. Clear All removes the export ticks. Next unlocks when at least one ticked row "
                    "has a usable, non-ambiguous allocation."
                ),
                "page": "payments" if getattr(self, "txns", None) else "receipts", "target": ("Add Auto-Allocated", "Add Manual Allocations"),
                "gate": lambda: _has_export_ready_row(self),
            },
            "validate": {
                "title": "Step 13 — Validate before export",
                "body": (
                    "Click Check selected for errors / Validate. AUTOLEDGER checks the rows currently selected for export and blocks unsafe "
                    "data such as missing GL accounts, ambiguous rules or invalid Pastel field values. Fix every blocking error and run "
                    "validation again. Next unlocks only after you have actually run validation with no blocking errors."
                ),
                "page": "dashboard", "target": ("Check selected for errors", "Validate"),
                "gate": lambda: bool(getattr(self, "_r10_tutorial_validation_ok", False)),
            },
            "export": {
                "title": "Step 14 — Export to Pastel",
                "body": (
                    "Click Export selected to Pastel, choose a folder, and let AUTOLEDGER create the Payment and/or Receipt CSV files. "
                    "Import the Payment CSV on Pastel's Payments side and the Receipt CSV on the Receipts side, then review the Pastel batch "
                    "before Update/Process. Next unlocks only after AUTOLEDGER detects that an export file was created during this tutorial."
                ),
                "page": "dashboard", "target": ("Export selected to Pastel",),
                "gate": lambda: bool(getattr(self, "_r10_tutorial_export_done", False)),
            },
            "complete": {
                "title": "Tutorial complete",
                "body": (
                    "You have followed the AUTOLEDGER workflow: Profile → Settings → CSV → Transaction review → Saved Rule → Export selection "
                    "→ Validation → Pastel export. Searchable Help remains available for every feature. You can run this Guided Tutorial again "
                    "at any time from Tutorial & Help."
                ),
                "page": "dashboard", "target": (), "gate": lambda: True,
            },
        }
        return defs[step_id]

    def _find_widget_by_text(self, candidates: tuple[str, ...]):
        if not candidates:
            return None
        wanted = tuple(x.casefold() for x in candidates if x)
        queue = [self]
        while queue:
            parent = queue.pop(0)
            try:
                children = parent.winfo_children()
            except Exception:
                children = []
            queue.extend(children)
            for child in children:
                try:
                    text = str(child.cget("text") or "").casefold()
                except Exception:
                    text = ""
                if text and any(x in text for x in wanted):
                    return child
        return None

    def _stop_pointer(self) -> None:
        job = getattr(self, "_r10_pointer_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._r10_pointer_job = None
        pointer = getattr(self, "_r10_pointer_window", None)
        if pointer is not None:
            try:
                pointer.destroy()
            except Exception:
                pass
        self._r10_pointer_window = None

    def _start_pointer(self, candidates: tuple[str, ...]) -> None:
        _stop_pointer(self)
        target = _find_widget_by_text(self, candidates)
        if target is None:
            return
        try:
            target.update_idletasks()
            px = target.winfo_rootx()
            py = target.winfo_rooty()
            pw = target.winfo_width()
            ph = target.winfo_height()
        except Exception:
            return
        pointer = core.tk.Toplevel(self)
        self._r10_pointer_window = pointer
        pointer.overrideredirect(True)
        try:
            pointer.attributes("-topmost", True)
        except Exception:
            pass
        label = core.tk.Label(pointer, text="▶  DO THIS NOW", bg="#f59e0b", fg="#111827", font=("Segoe UI", 9, "bold"), padx=9, pady=5, relief="solid", borderwidth=1)
        label.pack()
        pointer.update_idletasks()
        ww = pointer.winfo_width()
        x = max(0, px + pw + 8)
        if x + ww > pointer.winfo_screenwidth():
            x = max(0, px - ww - 8)
        y = max(0, py + max(0, (ph - pointer.winfo_height()) // 2))
        self._r10_pointer_base = (x, y)
        self._r10_pointer_phase = 0

        def pulse():
            win = getattr(self, "_r10_pointer_window", None)
            if win is None:
                return
            try:
                base_x, base_y = self._r10_pointer_base
                phase = int(getattr(self, "_r10_pointer_phase", 0))
                win.geometry(f"+{base_x + (4 if phase else 0)}+{base_y}")
                label.configure(bg="#fbbf24" if phase else "#f59e0b")
                self._r10_pointer_phase = 0 if phase else 1
                self._r10_pointer_job = self.after(350, pulse)
            except Exception:
                _stop_pointer(self)
        pulse()

    def _guided_mode_steps(self, mode: str) -> list[str]:
        return guided_step_ids(mode, revision)

    def _guided_current(self) -> dict:
        return _step_definition(self, self._r10_guided_steps[self._r10_guided_index])

    def _guided_update_gate(self) -> None:
        win = getattr(self, "_r10_guided_window", None)
        if win is None:
            return
        try:
            if not win.winfo_exists():
                return
        except Exception:
            return
        step = _guided_current(self)
        complete = False
        try:
            complete = bool(step["gate"]())
        except Exception:
            complete = False
        try:
            self._r10_guided_next.configure(state="normal" if complete else "disabled")
            self._r10_guided_gate_var.set("✓ Required action complete" if complete else "Complete the highlighted action before continuing.")
        except Exception:
            pass
        self._r10_gate_job = self.after(450, lambda: _guided_update_gate(self))

    def _guided_show_step(self) -> None:
        _stop_pointer(self)
        step = _guided_current(self)
        try:
            if step.get("page"):
                self._navigate_modern(step["page"])
        except Exception:
            pass
        total = len(self._r10_guided_steps)
        self._r10_guided_step_var.set(f"Step {self._r10_guided_index + 1} of {total}")
        self._r10_guided_title_var.set(step["title"])
        self._r10_guided_body.configure(state="normal")
        self._r10_guided_body.delete("1.0", "end")
        self._r10_guided_body.insert("1.0", step["body"])
        self._r10_guided_body.configure(state="disabled")
        self._r10_guided_back.configure(state="normal" if self._r10_guided_index > 0 else "disabled")
        self._r10_guided_next.configure(text="Finish" if self._r10_guided_index == total - 1 else "Next")
        self.after(180, lambda: _start_pointer(self, tuple(step.get("target") or ())))
        _guided_update_gate(self)

    def _guided_move(self, delta: int) -> None:
        if delta > 0:
            try:
                if str(self._r10_guided_next.cget("state")) == "disabled":
                    return
            except Exception:
                pass
        new_index = self._r10_guided_index + delta
        if new_index >= len(self._r10_guided_steps):
            _finish_guided(self)
            return
        if 0 <= new_index < len(self._r10_guided_steps):
            self._r10_guided_index = new_index
            _guided_show_step(self)

    def _close_guided(self) -> None:
        _stop_pointer(self)
        job = getattr(self, "_r10_gate_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._r10_gate_job = None
        win = getattr(self, "_r10_guided_window", None)
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
        self._r10_guided_window = None

    def _skip_guided(self) -> None:
        _record_guided_state(self, "skipped", self._r10_guided_mode)
        try:
            self.status_var.set("Guided tutorial skipped. You can run it again from Tutorial & Help.")
        except Exception:
            pass
        _close_guided(self)

    def _finish_guided(self) -> None:
        _record_guided_state(self, "completed", self._r10_guided_mode)
        try:
            self.status_var.set("Guided tutorial completed. Searchable Help remains available whenever you need it.")
        except Exception:
            pass
        _close_guided(self)

    def start_guided_tutorial(self, mode: str | None = None) -> None:
        old = getattr(self, "_r10_guided_window", None)
        if old is not None:
            try:
                if old.winfo_exists():
                    old.lift(); old.focus_force(); return
            except Exception:
                pass
        if mode not in {"clean", "update"}:
            mode = "clean"  # manual run is a normal beginner tutorial, never fake update wording
        self._r10_guided_mode = mode
        self._r10_guided_steps = _guided_mode_steps(self, mode)
        self._r10_guided_index = 0
        self._r10_tutorial_validation_ok = False
        self._r10_tutorial_export_done = False
        try:
            if getattr(self, "ui_mode", "modern") != "modern":
                self._apply_ui_mode("modern", initial=True)
        except Exception:
            pass

        win = core.tk.Toplevel(self)
        self._r10_guided_window = win
        win.title(f"{core.APP_NAME} — Guided Tutorial")
        win.minsize(440, 520)
        win.configure(bg="#f4f7fb")
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass
        try:
            self.update_idletasks()
            width, height = 470, 620
            screen_w = win.winfo_screenwidth()
            right_x = self.winfo_rootx() + self.winfo_width() + 8
            x = right_x if right_x + width <= screen_w else max(0, self.winfo_rootx() - width - 8)
            y = max(0, self.winfo_rooty())
            win.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            win.geometry("470x620")

        header = core.tk.Frame(win, bg="#0f2744", padx=18, pady=14)
        header.pack(fill="x")
        core.tk.Label(header, text="AUTOLEDGER GUIDED TUTORIAL", bg="#0f2744", fg="#9dd8cb", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self._r10_guided_step_var = core.tk.StringVar()
        core.tk.Label(header, textvariable=self._r10_guided_step_var, bg="#0f2744", fg="#ffffff", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

        panel = core.tk.Frame(win, bg="#ffffff", padx=18, pady=16, highlightthickness=1, highlightbackground="#e2e8f0")
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        self._r10_guided_title_var = core.tk.StringVar()
        core.tk.Label(panel, textvariable=self._r10_guided_title_var, bg="#ffffff", fg="#172033", font=("Segoe UI", 16, "bold"), wraplength=405, justify="left").pack(anchor="w")
        self._r10_guided_body = core.tk.Text(panel, wrap="word", bd=0, bg="#ffffff", fg="#334155", font=("Segoe UI", 10), spacing1=3, spacing3=7, height=18)
        self._r10_guided_body.pack(fill="both", expand=True, pady=(12, 8))
        self._r10_guided_body.configure(state="disabled")
        self._r10_guided_gate_var = core.tk.StringVar()
        core.tk.Label(panel, textvariable=self._r10_guided_gate_var, bg="#eef6ff", fg="#334155", font=("Segoe UI", 9, "bold"), wraplength=405, justify="left", padx=10, pady=8).pack(fill="x")

        footer = core.tk.Frame(win, bg="#f4f7fb", padx=14, pady=(0, 14))
        footer.pack(fill="x")
        core.ttk.Button(footer, text="Skip tutorial", command=lambda: _skip_guided(self), style="Modern.TButton").pack(side="left")
        self._r10_guided_next = core.ttk.Button(footer, text="Next", command=lambda: _guided_move(self, 1), style="Accent.TButton")
        self._r10_guided_next.pack(side="right")
        self._r10_guided_back = core.ttk.Button(footer, text="Back", command=lambda: _guided_move(self, -1), style="Modern.TButton")
        self._r10_guided_back.pack(side="right", padx=(0, 6))
        win.protocol("WM_DELETE_WINDOW", lambda: _close_guided(self))
        _guided_show_step(self)

    def _maybe_start_tutorial(self) -> None:
        # Replaces the older new-profile-only startup behaviour. R10 is install/update aware.
        if _should_auto_start_guided(self):
            start_guided_tutorial(self, _classify_install_mode(self))

    def start_help_with_guided(self, *args, **kwargs):
        if original_help is None:
            return start_guided_tutorial(self, "clean")
        result = original_help(self, *args, **kwargs)
        win = getattr(self, "tutorial_window", None)
        if win is not None and not hasattr(self, "_r10_help_guided_button"):
            try:
                holder = core.tk.Frame(win, bg="#f4f7fb", padx=18, pady=(0, 10))
                holder.pack(fill="x")
                btn = core.ttk.Button(
                    holder,
                    text="Run Guided Tutorial",
                    command=lambda: (self._tutorial_close(), self.after(80, lambda: start_guided_tutorial(self, "clean"))),
                    style="Accent.TButton",
                )
                btn.pack(side="left")
                self._r10_help_guided_button = btn
            except Exception:
                pass
        return result

    def wrapped_validation(self, *args, **kwargs):
        try:
            errors, _, _ = self._combined_validation()
            self._r10_tutorial_validation_ok = not bool(errors)
        except Exception:
            self._r10_tutorial_validation_ok = False
        return original_show_validation(self, *args, **kwargs) if original_show_validation is not None else None

    def wrapped_export(self, *args, **kwargs):
        start = time.time() - 1.0
        result = original_export_files(self, *args, **kwargs) if original_export_files is not None else None
        try:
            folder = Path(self.store.get_setting("last_folder", str(Path.home())))
            candidates = list(folder.glob("Pastel_Payments_*.csv")) + list(folder.glob("Pastel_Receipts_*.csv"))
            if any(p.is_file() and p.stat().st_mtime >= start for p in candidates):
                self._r10_tutorial_export_done = True
        except Exception:
            pass
        return result

    def wrapped_refresh_profiles(self, *args, **kwargs):
        result = original_refresh_profiles(self, *args, **kwargs) if original_refresh_profiles is not None else None
        return result

    App._r10_guided_state_path = _state_path
    App._r10_install_context_path = _context_path
    App._r10_classify_install_mode = _classify_install_mode
    App._r10_should_auto_start_guided = _should_auto_start_guided
    App._r10_record_guided_state = _record_guided_state
    App._r10_guided_snapshot = _guided_snapshot
    App._r10_step_definition = _step_definition
    App._r10_find_widget_by_text = _find_widget_by_text
    App._r10_stop_pointer = _stop_pointer
    App._r10_start_pointer = _start_pointer
    App._r10_guided_show_step = _guided_show_step
    App._r10_guided_move = _guided_move
    App._r10_close_guided = _close_guided
    App._r10_skip_guided = _skip_guided
    App._r10_finish_guided = _finish_guided
    App.start_guided_tutorial = start_guided_tutorial
    App._maybe_start_tutorial = _maybe_start_tutorial
    if original_help is not None:
        App.start_tutorial = start_help_with_guided
    if original_show_validation is not None:
        App.show_validation = wrapped_validation
    if original_export_files is not None:
        App.export_files = wrapped_export
    if original_refresh_profiles is not None:
        App._refresh_profile_ui = wrapped_refresh_profiles
