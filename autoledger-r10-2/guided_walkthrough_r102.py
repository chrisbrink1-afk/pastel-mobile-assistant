from __future__ import annotations

import time


R102_REVISION = "R10.2"

R102_UPDATE_FEATURES = (
    {
        "id": "update_r102_walkthrough",
        "title": "The tutorial is now a true guided walkthrough",
        "body": (
            "R10.2 replaces the slide-like tutorial presentation with a compact walkthrough assistant that stays beside AUTOLEDGER. "
            "The assistant points at the real control you must use in the main program and waits for you to complete the required action "
            "before Next becomes available."
        ),
    },
    {
        "id": "update_r102_navigation",
        "title": "Tutorial controls always stay on screen",
        "body": (
            "Back, Next and Skip Tutorial are now fixed in a permanent button bar. Long instructions scroll inside the assistant instead "
            "of pushing the navigation buttons off the bottom of the screen."
        ),
    },
    {
        "id": "update_r102_rule_walkthrough",
        "title": "Saved Rules are taught field by field",
        "body": (
            "The walkthrough now stays with you while you create a Saved Rule and explains Rule name, matching text, matching method, "
            "General Ledger account, VAT treatment, Priority, optional amount-based allocation and Save Rule before continuing."
        ),
    },
)

R102_HELP_TOPICS = (
    {
        "id": "guided_walkthrough_r102",
        "title": "How the Guided Walkthrough works",
        "page": "dashboard",
        "keywords": "guided walkthrough interactive tutorial back next skip do this now highlighted control wait complete",
        "body": (
            "The Guided Walkthrough is not a slide show. AUTOLEDGER keeps a compact instruction assistant beside the main program, "
            "points at the real control you must use, and checks the result. On required steps Next remains disabled until the action "
            "has actually been completed. Back, Next and Skip Tutorial stay visible at all times."
        ),
    },
    {
        "id": "guided_walkthrough_rules_r102",
        "title": "Guided Saved Rule setup",
        "page": "payments",
        "keywords": "guided rule rule name match matching method gl vat priority amount save tutorial",
        "body": (
            "During the Guided Walkthrough, AUTOLEDGER opens the normal Saved Rule window and teaches its important fields one by one. "
            "Priority normally stays at 100. Higher numbers such as 200 or 300 are used when a more specific rule must take precedence "
            "over a broader rule. Amount-based allocation is optional and can be left off for a basic rule."
        ),
    },
)

WORKFLOW_STEPS = (
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
    "rule_open",
    "rule_name",
    "rule_match",
    "rule_method",
    "rule_gl",
    "rule_vat",
    "rule_priority",
    "rule_amount_optional",
    "rule_save",
    "rule_result",
    "select_export",
    "validate",
    "export",
    "complete",
)


def register_r102_curriculum(guided_tutorial_module, revision: str = R102_REVISION) -> None:
    """Register the update curriculum before install_guided_tutorial is called."""
    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R102_UPDATE_FEATURES


def install_r102_walkthrough(core, edition: str, licence_info=None, revision: str = R102_REVISION) -> None:
    """Replace the R10/R10.1 slide-like tutorial shell with a real guided walkthrough.

    The existing R10 action-detection helpers and persistent version/update state are
    intentionally retained. R10.2 changes the interaction layer: instructions stay
    compact, navigation is permanently visible, actual program controls are pointed
    to, required actions are gated, and Saved Rule setup is taught field by field.
    """
    App = core.App

    existing = {t.get("id") for t in getattr(core, "TUTORIAL_TOPICS", ())}
    topics = list(getattr(core, "TUTORIAL_TOPICS", ()))
    for topic in R102_HELP_TOPICS:
        if topic["id"] not in existing:
            topics.append(dict(topic))
    core.TUTORIAL_TOPICS = tuple(topics)

    RuleDialog = getattr(core, "RuleDialog", None)
    if RuleDialog is not None and not getattr(RuleDialog, "_r102_tracking_installed", False):
        original_rule_init = RuleDialog.__init__

        def tracked_rule_init(dlg, *args, **kwargs):
            original_rule_init(dlg, *args, **kwargs)
            app = getattr(dlg, "app", None)
            if app is None or not getattr(app, "_r102_walkthrough_active", False):
                return
            app._r102_rule_dialog = dlg
            app._r102_last_rule_saved = False
            try:
                app._r102_rule_count_before_dialog = len(app.store.all_rules())
            except Exception:
                app._r102_rule_count_before_dialog = 0
            try:
                dlg.grab_release()
            except Exception:
                pass

            def remember_close(event=None):
                try:
                    if event is not None and event.widget is not dlg:
                        return
                except Exception:
                    pass
                try:
                    app._r102_last_rule_saved = bool(getattr(dlg, "result", None))
                except Exception:
                    app._r102_last_rule_saved = False
                if getattr(app, "_r102_rule_dialog", None) is dlg:
                    app._r102_rule_dialog = None

            try:
                dlg.bind("<Destroy>", remember_close, add="+")
            except Exception:
                pass

        RuleDialog.__init__ = tracked_rule_init
        RuleDialog._r102_tracking_installed = True

    old_help = getattr(App, "start_tutorial", None)

    def _rule_dialog(self):
        dlg = getattr(self, "_r102_rule_dialog", None)
        if dlg is None:
            return None
        try:
            if dlg.winfo_exists():
                return dlg
        except Exception:
            pass
        self._r102_rule_dialog = None
        return None

    def _rule_value(self, key: str, default=""):
        dlg = _rule_dialog(self)
        if dlg is None:
            return default
        try:
            return dlg.vars[key].get()
        except Exception:
            return default

    def _whole_number(value) -> bool:
        try:
            int(str(value).strip())
            return True
        except Exception:
            return False

    def _valid_rule_vat(self) -> bool:
        dlg = _rule_dialog(self)
        if dlg is None:
            return False
        try:
            if not bool(dlg.vars["vat"].get()):
                return True
            return _whole_number(dlg.vars["tax"].get())
        except Exception:
            return False

    def _rule_saved(self) -> bool:
        return bool(getattr(self, "_r102_last_rule_saved", False))

    def _step_ids(self, mode: str) -> list[str]:
        ids: list[str] = []
        if (mode or "clean").lower() == "update":
            ids.append("update_intro")
            try:
                import guided_tutorial as gt
                ids.extend(x["id"] for x in gt.UPDATE_FEATURES_BY_REVISION.get(revision, ()))
            except Exception:
                ids.extend(x["id"] for x in R102_UPDATE_FEATURES)
        ids.extend(WORKFLOW_STEPS)
        return ids

    def _definition(self, step_id: str) -> dict:
        if step_id not in {
            "rule_open", "rule_name", "rule_match", "rule_method", "rule_gl",
            "rule_vat", "rule_priority", "rule_amount_optional", "rule_save",
        }:
            return self._r10_step_definition(step_id)

        direction_page = "payments" if getattr(self, "txns", None) else "receipts"
        definitions = {
            "rule_open": {
                "title": "Create your first Saved Rule",
                "body": (
                    "Keep the transaction selected and click Save rule from selected in AUTOLEDGER. "
                    "A Saved Rule tells AUTOLEDGER how to recognise and allocate the same kind of bank transaction in future. "
                    "Do not rush through the rule window — I will stay with you and explain the important fields one at a time."
                ),
                "page": direction_page,
                "target": ("Save rule from selected",),
                "gate": lambda: _rule_dialog(self) is not None,
            },
            "rule_name": {
                "title": "Saved Rule — Rule name",
                "body": (
                    "Rule name is the friendly name you will recognise later in Saved Rules. AUTOLEDGER normally fills this from the "
                    "selected transaction. Read it and make it clearer if necessary. For example, 'Vodacom monthly debit'. "
                    "A rule needs a name before you can continue."
                ),
                "page": None,
                "target": ("Rule name",),
                "gate": lambda: bool(str(_rule_value(self, "name", "")).strip()),
            },
            "rule_match": {
                "title": "Saved Rule — Name / number to match",
                "body": (
                    "This is the bank text AUTOLEDGER looks for when deciding whether the rule applies. It is normally filled from the "
                    "selected transaction. Keep enough identifying text to recognise the supplier or reference, but avoid unnecessary "
                    "changing parts such as dates when possible."
                ),
                "page": None,
                "target": ("Name / number to match",),
                "gate": lambda: bool(str(_rule_value(self, "pattern", "")).strip()),
            },
            "rule_method": {
                "title": "Saved Rule — Matching method",
                "body": (
                    "Matching method controls how strictly AUTOLEDGER compares the bank description. Smart name + number is a useful "
                    "default for many bank references. Contains looks for the text anywhere, Starts with requires it at the beginning, "
                    "and Exact requires the complete text to match. Check the selected method before continuing."
                ),
                "page": None,
                "target": ("Matching method",),
                "gate": lambda: bool(str(_rule_value(self, "mode_label", "")).strip()),
            },
            "rule_gl": {
                "title": "Saved Rule — General Ledger account",
                "body": (
                    "Enter the Pastel General Ledger account that this type of payment or receipt should be allocated to. "
                    "This is the transaction's expense, income, asset or liability GL — it is NOT the Cash Book bank GL from Settings. "
                    "Use the real account from the customer's Pastel chart of accounts."
                ),
                "page": None,
                "target": ("General ledger account",),
                "gate": lambda: bool(str(_rule_value(self, "account", "")).strip()),
            },
            "rule_vat": {
                "title": "Saved Rule — VAT treatment",
                "body": (
                    "Choose No VAT when this transaction should not carry VAT, or VAT when it should. If VAT is selected, confirm the "
                    "Pastel tax type as well. The tax type is company-specific — the tutorial's earlier example of tax type 1 is only "
                    "an example and must not replace the customer's real Pastel setup."
                ),
                "page": None,
                "target": ("VAT treatment", "Pastel tax type:"),
                "gate": lambda: _valid_rule_vat(self),
            },
            "rule_priority": {
                "title": "Saved Rule — Priority",
                "body": (
                    "Priority decides which rule is considered first when more than one rule can match the same transaction. "
                    "Higher numbers are considered first. Leave normal rules at 100. Use a higher value such as 200 or 300 only when "
                    "a more specific exception must take precedence over a broader rule."
                ),
                "page": None,
                "target": ("Priority",),
                "gate": lambda: _whole_number(_rule_value(self, "priority", "")),
            },
            "rule_amount_optional": {
                "title": "Saved Rule — Optional amount-based allocation",
                "body": (
                    "This section is optional. Leave Use amount-based allocation rule unticked for a normal beginner rule. "
                    "Turn it on only when the same bank identity must be treated differently above, below or at a particular amount. "
                    "The full searchable Help explains the automatic and review-each options in detail."
                ),
                "page": None,
                "target": ("Optional amount-based allocation", "Use amount-based allocation rule"),
                "gate": lambda: _rule_dialog(self) is not None,
            },
            "rule_save": {
                "title": "Save the rule",
                "body": (
                    "Review the fields once more, then click Save rule in the rule window. AUTOLEDGER will close the rule window and "
                    "reapply saved rules to the loaded statement. Next remains locked until AUTOLEDGER confirms that the rule was actually saved."
                ),
                "page": None,
                "target": ("Save rule",),
                "gate": lambda: _rule_saved(self),
            },
        }
        return definitions[step_id]

    def _all_walkthrough_roots(self):
        roots = [self]
        dlg = _rule_dialog(self)
        if dlg is not None:
            roots.insert(0, dlg)
        return roots

    def _find_target(self, candidates):
        wanted = tuple(str(x).casefold() for x in candidates if x)
        if not wanted:
            return None
        seen = set()
        queue = list(_all_walkthrough_roots(self))
        while queue:
            parent = queue.pop(0)
            if id(parent) in seen:
                continue
            seen.add(id(parent))
            try:
                children = list(parent.winfo_children())
            except Exception:
                children = []
            queue.extend(children)
            for child in children:
                try:
                    text = str(child.cget("text") or "").strip().casefold()
                except Exception:
                    text = ""
                if text and any(w in text for w in wanted):
                    return child
        return None

    def _stop_pointer(self):
        job = getattr(self, "_r102_pointer_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._r102_pointer_job = None
        pointer = getattr(self, "_r102_pointer_window", None)
        if pointer is not None:
            try:
                pointer.destroy()
            except Exception:
                pass
        self._r102_pointer_window = None

    def _position_card(self, target=None):
        win = getattr(self, "_r10_guided_window", None)
        if win is None:
            return
        try:
            win.update_idletasks()
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            width = min(430, max(360, sw - 80))
            height = min(410, max(330, sh - 120))
            margin = 12
            if target is not None:
                target.update_idletasks()
                tx, ty = target.winfo_rootx(), target.winfo_rooty()
                tw = target.winfo_width()
                right = tx + tw + margin
                left = tx - width - margin
                if right + width <= sw:
                    x = right
                elif left >= 0:
                    x = left
                else:
                    x = max(0, sw - width - margin)
                y = min(max(margin, ty - 70), max(margin, sh - height - margin))
            else:
                self.update_idletasks()
                x = min(max(margin, self.winfo_rootx() + self.winfo_width() - width), max(margin, sw - width - margin))
                y = min(max(margin, self.winfo_rooty() + 40), max(margin, sh - height - margin))
            win.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
        except Exception:
            try:
                win.geometry("410x380")
            except Exception:
                pass

    def _start_pointer(self, candidates):
        _stop_pointer(self)
        target = _find_target(self, tuple(candidates or ()))
        _position_card(self, target)
        if target is None:
            return
        try:
            target.update_idletasks()
            px, py = target.winfo_rootx(), target.winfo_rooty()
            pw, ph = target.winfo_width(), target.winfo_height()
        except Exception:
            return

        pointer = core.tk.Toplevel(self)
        self._r102_pointer_window = pointer
        pointer.overrideredirect(True)
        try:
            pointer.attributes("-topmost", True)
        except Exception:
            pass
        label = core.tk.Label(
            pointer, text="▶  DO THIS NOW", bg="#f59e0b", fg="#111827",
            font=("Segoe UI", 9, "bold"), padx=9, pady=5, relief="solid", borderwidth=2,
        )
        label.pack()
        pointer.update_idletasks()
        ww, wh = pointer.winfo_width(), pointer.winfo_height()
        x = px + pw + 8
        if x + ww > pointer.winfo_screenwidth():
            x = max(0, px - ww - 8)
        y = max(0, py + (ph - wh) // 2)
        self._r102_pointer_base = (x, y)
        self._r102_pointer_phase = 0

        def pulse():
            win = getattr(self, "_r102_pointer_window", None)
            if win is None:
                return
            try:
                bx, by = self._r102_pointer_base
                phase = int(getattr(self, "_r102_pointer_phase", 0))
                win.geometry(f"+{bx + (5 if phase else 0)}+{by}")
                label.configure(bg="#fde047" if phase else "#f59e0b")
                self._r102_pointer_phase = 0 if phase else 1
                self._r102_pointer_job = self.after(320, pulse)
            except Exception:
                _stop_pointer(self)

        pulse()

    def _current(self):
        return _definition(self, self._r10_guided_steps[self._r10_guided_index])

    def _gate_complete(self):
        try:
            return bool(_current(self)["gate"]())
        except Exception:
            return False

    def _update_gate(self):
        win = getattr(self, "_r10_guided_window", None)
        if win is None:
            return
        try:
            if not win.winfo_exists():
                return
        except Exception:
            return
        complete = _gate_complete(self)
        try:
            self._r10_guided_next.configure(state="normal" if complete else "disabled")
            self._r10_guided_gate_var.set(
                "DONE — click Next to continue." if complete
                else "WAITING FOR YOU — complete the highlighted action in AUTOLEDGER."
            )
            self._r102_gate_label.configure(
                bg="#ecfdf5" if complete else "#fff7ed", fg="#166534" if complete else "#9a3412",
            )
        except Exception:
            pass
        previous = getattr(self, "_r102_last_gate_complete", None)
        if complete and previous is False:
            try:
                self._r102_gate_label.configure(relief="solid", borderwidth=1)
                self.after(650, lambda: self._r102_gate_label.configure(relief="flat", borderwidth=0))
            except Exception:
                pass
        self._r102_last_gate_complete = complete
        try:
            self._r102_gate_job = self.after(250, lambda: _update_gate(self))
        except Exception:
            pass

    def _show_step(self):
        _stop_pointer(self)
        job = getattr(self, "_r102_gate_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        step = _current(self)
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
        self._r10_guided_body.see("1.0")
        self._r10_guided_body.configure(state="disabled")
        self._r10_guided_back.configure(state="normal" if self._r10_guided_index > 0 else "disabled")
        self._r10_guided_next.configure(text="Finish" if self._r10_guided_index == total - 1 else "Next")
        self._r102_last_gate_complete = None
        try:
            self.after(120, lambda: _start_pointer(self, tuple(step.get("target") or ())))
        except Exception:
            _start_pointer(self, tuple(step.get("target") or ()))
        _update_gate(self)

    def _move(self, delta: int):
        if delta > 0 and not _gate_complete(self):
            return
        current_id = self._r10_guided_steps[self._r10_guided_index]
        if delta < 0 and _rule_dialog(self) is None and current_id == "rule_save" and _rule_saved(self):
            try:
                self._r10_guided_gate_var.set(
                    "The rule has already been saved. Continue with Next, or restart the tutorial to review its fields again."
                )
            except Exception:
                pass
            return
        new_index = self._r10_guided_index + delta
        if new_index >= len(self._r10_guided_steps):
            self._r10_finish_guided()
            return
        if 0 <= new_index < len(self._r10_guided_steps):
            self._r10_guided_index = new_index
            _show_step(self)

    def _close(self):
        _stop_pointer(self)
        job = getattr(self, "_r102_gate_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._r102_gate_job = None
        win = getattr(self, "_r10_guided_window", None)
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
        self._r10_guided_window = None
        self._r102_walkthrough_active = False

    def _skip(self):
        try:
            self._r10_record_guided_state("skipped", self._r10_guided_mode)
        except Exception:
            pass
        try:
            self.status_var.set("Guided walkthrough skipped. You can run it again from Tutorial & Help.")
        except Exception:
            pass
        _close(self)

    def _finish(self):
        try:
            self._r10_record_guided_state("completed", self._r10_guided_mode)
        except Exception:
            pass
        try:
            self.status_var.set("Guided walkthrough completed. Searchable Help remains available whenever you need it.")
        except Exception:
            pass
        _close(self)

    def start_walkthrough(self, mode: str | None = None):
        old = getattr(self, "_r10_guided_window", None)
        if old is not None:
            try:
                if old.winfo_exists():
                    old.lift(); old.focus_force(); return
            except Exception:
                pass
        if mode not in {"clean", "update"}:
            mode = "clean"
        self._r10_guided_mode = mode
        self._r10_guided_steps = _step_ids(self, mode)
        self._r10_guided_index = 0
        self._r10_tutorial_validation_ok = False
        self._r10_tutorial_export_done = False
        self._r102_last_rule_saved = False
        self._r102_rule_dialog = None
        self._r102_walkthrough_active = True
        try:
            if getattr(self, "ui_mode", "modern") != "modern":
                self._apply_ui_mode("modern", initial=True)
        except Exception:
            pass

        win = core.tk.Toplevel(self)
        self._r10_guided_window = win
        win.title(f"{core.APP_NAME} — Guided Walkthrough")
        win.configure(bg="#f4f7fb")
        win.minsize(360, 330)
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        header = core.tk.Frame(win, bg="#0f2744", padx=14, pady=10)
        header.grid(row=0, column=0, sticky="ew")
        core.tk.Label(header, text="AUTOLEDGER — I WILL GUIDE YOU", bg="#0f2744", fg="#9dd8cb", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self._r10_guided_step_var = core.tk.StringVar()
        core.tk.Label(header, textvariable=self._r10_guided_step_var, bg="#0f2744", fg="#ffffff", font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        panel = core.tk.Frame(win, bg="#ffffff", padx=14, pady=12, highlightthickness=1, highlightbackground="#e2e8f0")
        panel.grid(row=1, column=0, sticky="nsew", padx=10, pady=(10, 6))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        self._r10_guided_title_var = core.tk.StringVar()
        core.tk.Label(panel, textvariable=self._r10_guided_title_var, bg="#ffffff", fg="#172033", font=("Segoe UI", 14, "bold"), wraplength=365, justify="left").grid(row=0, column=0, columnspan=2, sticky="ew")

        self._r10_guided_body = core.tk.Text(panel, wrap="word", bd=0, bg="#ffffff", fg="#334155", font=("Segoe UI", 10), spacing1=2, spacing3=6, height=7)
        body_scroll = core.ttk.Scrollbar(panel, orient="vertical", command=self._r10_guided_body.yview)
        self._r10_guided_body.configure(yscrollcommand=body_scroll.set)
        self._r10_guided_body.grid(row=1, column=0, sticky="nsew", pady=(9, 0))
        body_scroll.grid(row=1, column=1, sticky="ns", pady=(9, 0))
        self._r10_guided_body.configure(state="disabled")

        self._r10_guided_gate_var = core.tk.StringVar()
        self._r102_gate_label = core.tk.Label(win, textvariable=self._r10_guided_gate_var, bg="#fff7ed", fg="#9a3412", font=("Segoe UI", 9, "bold"), wraplength=380, justify="left", anchor="w", padx=10, pady=7)
        self._r102_gate_label.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))

        footer = core.tk.Frame(win, bg="#f4f7fb", padx=10, pady=9)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)
        self._r102_skip_button = core.ttk.Button(footer, text="Skip Tutorial", command=lambda: _skip(self), style="Modern.TButton")
        self._r102_skip_button.grid(row=0, column=0, sticky="w")
        nav = core.tk.Frame(footer, bg="#f4f7fb")
        nav.grid(row=0, column=2, sticky="e")
        self._r10_guided_back = core.ttk.Button(nav, text="Back", command=lambda: _move(self, -1), style="Modern.TButton")
        self._r10_guided_back.pack(side="left", padx=(0, 6))
        self._r10_guided_next = core.ttk.Button(nav, text="Next", command=lambda: _move(self, 1), style="Accent.TButton")
        self._r10_guided_next.pack(side="left")

        win.protocol("WM_DELETE_WINDOW", lambda: _skip(self))
        _position_card(self, None)
        _show_step(self)
        try:
            win.deiconify(); win.lift()
        except Exception:
            pass

    def _walkthrough_snapshot(self) -> dict:
        win = getattr(self, "_r10_guided_window", None)
        if win is None:
            return {"visible": False}
        try:
            win.update_idletasks()
        except Exception:
            pass

        def button_info(btn):
            try:
                wx, wy = win.winfo_rootx(), win.winfo_rooty()
                ww, wh = win.winfo_width(), win.winfo_height()
                bx, by = btn.winfo_rootx(), btn.winfo_rooty()
                bw, bh = btn.winfo_width(), btn.winfo_height()
                return {
                    "text": str(btn.cget("text")), "mapped": bool(btn.winfo_ismapped()),
                    "onscreen": bx >= wx and by >= wy and bx + bw <= wx + ww and by + bh <= wy + wh,
                    "state": str(btn.cget("state")),
                }
            except Exception:
                return {"text": "", "mapped": False, "onscreen": False, "state": ""}

        try:
            title = str(self._r10_guided_title_var.get())
            body = str(self._r10_guided_body.get("1.0", "end-1c"))
            step = str(self._r10_guided_step_var.get())
        except Exception:
            title = body = step = ""
        return {
            "visible": bool(win.winfo_exists()), "title": title.strip(), "body": body.strip(), "step": step.strip(),
            "index": int(getattr(self, "_r10_guided_index", -1)),
            "step_id": self._r10_guided_steps[self._r10_guided_index] if getattr(self, "_r10_guided_steps", None) else "",
            "back": button_info(self._r10_guided_back), "next": button_info(self._r10_guided_next), "skip": button_info(self._r102_skip_button),
            "width": int(win.winfo_width()), "height": int(win.winfo_height()),
        }

    def _walkthrough_smoke(self, mode: str = "update") -> dict:
        start_walkthrough(self, mode)
        deadline = time.time() + 2.0
        snap = {}
        while time.time() < deadline:
            try:
                self.update()
            except Exception:
                break
            snap = _walkthrough_snapshot(self)
            if snap.get("visible") and snap.get("title") and snap.get("body") and snap.get("back", {}).get("onscreen") and snap.get("next", {}).get("onscreen") and snap.get("skip", {}).get("onscreen"):
                break
            time.sleep(0.02)
        return snap

    def help_with_r102(self, *args, **kwargs):
        result = old_help(self, *args, **kwargs) if old_help is not None else None
        btn = getattr(self, "_r10_help_guided_button", None)
        if btn is not None:
            try:
                btn.configure(text="Run Guided Walkthrough", command=lambda: (self._tutorial_close(), self.after(80, lambda: self.start_guided_tutorial("clean"))))
            except Exception:
                pass
        return result

    App._r102_rule_dialog_current = _rule_dialog
    App._r102_step_ids = _step_ids
    App._r102_step_definition = _definition
    App._r102_find_target = _find_target
    App._r102_stop_pointer = _stop_pointer
    App._r102_start_pointer = _start_pointer
    App._r102_position_card = _position_card
    App._r102_walkthrough_snapshot = _walkthrough_snapshot
    App._r102_walkthrough_smoke = _walkthrough_smoke
    App._r10_guided_show_step = _show_step
    App._r10_guided_move = _move
    App._r10_close_guided = _close
    App._r10_skip_guided = _skip
    App._r10_finish_guided = _finish
    App.start_guided_tutorial = start_walkthrough
    if old_help is not None:
        App.start_tutorial = help_with_r102
