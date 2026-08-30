from __future__ import annotations

import time


R103_REVISION = "R10.3"

R103_UPDATE_FEATURES = (
    {
        "id": "update_r103_inline_walkthrough",
        "title": "Tutorial now runs inside AUTOLEDGER",
        "body": (
            "R10.3 removes the separate tutorial pop-up. The Guided Walkthrough now stays inside the normal AUTOLEDGER interface, "
            "highlights the real control you must use, and places a compact instruction bubble beside that control."
        ),
    },
    {
        "id": "update_r103_static_highlight",
        "title": "Clear highlighting instead of distracting animation",
        "body": (
            "The moving DO THIS NOW pointer has been removed. Required controls now receive a clear static outline, while a nearby "
            "hint bubble explains exactly what to enter, select, click or review."
        ),
    },
    {
        "id": "update_r103_action_gated",
        "title": "Every required step waits for the real action",
        "body": (
            "The walkthrough remains action-gated. Next stays unavailable until AUTOLEDGER detects that the current task has actually "
            "been completed, so the tutorial behaves like a walkthrough rather than a slide show."
        ),
    },
)

R103_HELP_TOPICS = (
    {
        "id": "guided_walkthrough_r103_inline",
        "title": "Using the in-place Guided Walkthrough",
        "page": "dashboard",
        "keywords": "guided walkthrough inline highlight speech bubble hint tutorial no popup do this step by step",
        "body": (
            "The R10.3 Guided Walkthrough runs inside AUTOLEDGER rather than in a separate tutorial window. On each action step, "
            "AUTOLEDGER outlines the real field, button or work area that needs attention and positions an instruction bubble nearby. "
            "Complete the highlighted action in the normal program. Next unlocks when AUTOLEDGER confirms the step is complete."
        ),
    },
)

_INTERACTIVE_CLASSES = {
    "entry", "tentry", "combobox", "tcombobox", "spinbox", "tspinbox",
    "checkbutton", "tcheckbutton", "radiobutton", "tradiobutton",
    "button", "tbutton", "text", "listbox", "treeview",
}


def register_r103_curriculum(guided_tutorial_module, revision: str = R103_REVISION) -> None:
    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R103_UPDATE_FEATURES


def install_r103_walkthrough(core, edition: str, licence_info=None, revision: str = R103_REVISION) -> None:
    """Replace the R10.2 tutorial Toplevel/pointer with an in-place highlighted walkthrough."""
    App = core.App

    existing = {t.get("id") for t in getattr(core, "TUTORIAL_TOPICS", ())}
    topics = list(getattr(core, "TUTORIAL_TOPICS", ()))
    for topic in R103_HELP_TOPICS:
        if topic["id"] not in existing:
            topics.append(dict(topic))
    core.TUTORIAL_TOPICS = tuple(topics)

    r102_step_ids = App._r102_step_ids
    r102_definition = App._r102_step_definition
    r102_find_target = App._r102_find_target
    r102_stop_pointer = getattr(App, "_r102_stop_pointer", None)

    def _cancel_job(self, name: str):
        job = getattr(self, name, None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        setattr(self, name, None)

    def _widget_class(widget) -> str:
        try:
            return str(widget.winfo_class() or "").casefold()
        except Exception:
            return ""

    def _is_interactive(widget) -> bool:
        cls = _widget_class(widget)
        if cls in _INTERACTIVE_CLASSES:
            return True
        return any(token in cls for token in ("entry", "combo", "button", "spinbox", "treeview", "listbox"))

    def _descendants(root, depth: int = 3):
        items = []
        queue = [(root, 0)]
        seen = set()
        while queue:
            parent, level = queue.pop(0)
            if id(parent) in seen or level > depth:
                continue
            seen.add(id(parent))
            try:
                children = list(parent.winfo_children())
            except Exception:
                children = []
            items.extend(children)
            if level < depth:
                queue.extend((child, level + 1) for child in children)
        return items

    def _interactive_near_label(self, label):
        if label is None or _is_interactive(label):
            return label
        try:
            label.update_idletasks()
            lx = label.winfo_rootx()
            ly = label.winfo_rooty()
            lw = max(1, label.winfo_width())
            lh = max(1, label.winfo_height())
            lcx = lx + lw / 2
            lcy = ly + lh / 2
        except Exception:
            return label

        scopes = []
        parent = getattr(label, "master", None)
        if parent is not None:
            scopes.append(parent)
            grand = getattr(parent, "master", None)
            if grand is not None:
                scopes.append(grand)

        candidates = []
        seen = set()
        for scope in scopes:
            for widget in _descendants(scope, 2):
                if id(widget) in seen or widget is label or not _is_interactive(widget):
                    continue
                seen.add(id(widget))
                try:
                    widget.update_idletasks()
                    if not widget.winfo_ismapped():
                        continue
                    wx = widget.winfo_rootx()
                    wy = widget.winfo_rooty()
                    ww = max(1, widget.winfo_width())
                    wh = max(1, widget.winfo_height())
                    wcx = wx + ww / 2
                    wcy = wy + wh / 2
                except Exception:
                    continue
                dx = abs(wcx - lcx)
                dy = abs(wcy - lcy)
                score = dx * 0.35 + dy * 1.4
                if abs(wcy - lcy) <= max(lh, wh) * 0.8:
                    score -= 140
                if wx >= lx + lw - 8:
                    score -= 35
                cls = _widget_class(widget)
                if "entry" in cls or "combo" in cls or "spinbox" in cls:
                    score -= 25
                candidates.append((score, widget))
        if not candidates:
            return label
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def _find_target(self, candidates):
        raw = r102_find_target(self, tuple(candidates or ()))
        return _interactive_near_label(self, raw)

    def _clear_visuals(self):
        for frame in list(getattr(self, "_r103_highlight_frames", ()) or ()):
            try:
                frame.destroy()
            except Exception:
                pass
        self._r103_highlight_frames = []
        for name in ("_r103_bubble", "_r103_tail"):
            widget = getattr(self, name, None)
            if widget is not None:
                try:
                    widget.destroy()
                except Exception:
                    pass
            setattr(self, name, None)
        self._r103_target = None
        self._r103_host = None

    def _current(self):
        return r102_definition(self, self._r10_guided_steps[self._r10_guided_index])

    def _gate_complete(self):
        try:
            return bool(_current(self)["gate"]())
        except Exception:
            return False

    def _button_info(self, button, host):
        try:
            host.update_idletasks()
            hx, hy = host.winfo_rootx(), host.winfo_rooty()
            hw, hh = host.winfo_width(), host.winfo_height()
            bx, by = button.winfo_rootx(), button.winfo_rooty()
            bw, bh = button.winfo_width(), button.winfo_height()
            return {
                "text": str(button.cget("text")),
                "mapped": bool(button.winfo_ismapped()),
                "onscreen": bx >= hx and by >= hy and bx + bw <= hx + hw and by + bh <= hy + hh,
                "state": str(button.cget("state")),
            }
        except Exception:
            return {"text": "", "mapped": False, "onscreen": False, "state": ""}

    def _place_highlight(self, host, target):
        self._r103_highlight_frames = []
        if target is None:
            return
        try:
            host.update_idletasks(); target.update_idletasks()
            hx, hy = host.winfo_rootx(), host.winfo_rooty()
            x = target.winfo_rootx() - hx
            y = target.winfo_rooty() - hy
            w = max(8, target.winfo_width())
            h = max(8, target.winfo_height())
        except Exception:
            return
        pad = 5
        thick = 3
        specs = (
            (x - pad, y - pad, w + pad * 2, thick),
            (x - pad, y + h + pad - thick, w + pad * 2, thick),
            (x - pad, y - pad, thick, h + pad * 2),
            (x + w + pad - thick, y - pad, thick, h + pad * 2),
        )
        for fx, fy, fw, fh in specs:
            bar = core.tk.Frame(host, bg="#f59e0b", bd=0, highlightthickness=0)
            bar.place(x=int(fx), y=int(fy), width=max(1, int(fw)), height=max(1, int(fh)))
            try:
                bar.lift()
            except Exception:
                pass
            self._r103_highlight_frames.append(bar)

    def _place_bubble(self, step, target):
        _clear_visuals(self)
        host = self
        if target is not None:
            try:
                host = target.winfo_toplevel()
            except Exception:
                host = self
        self._r103_target = target
        self._r103_host = host

        _place_highlight(self, host, target)

        bubble = core.tk.Frame(
            host, bg="#fffaf0", bd=0, highlightthickness=2, highlightbackground="#f59e0b",
            padx=12, pady=10,
        )
        self._r103_bubble = bubble

        top = core.tk.Frame(bubble, bg="#fffaf0")
        top.pack(fill="x")
        self._r10_guided_step_var = core.tk.StringVar()
        self._r10_guided_title_var = core.tk.StringVar()
        self._r10_guided_gate_var = core.tk.StringVar()
        total = len(self._r10_guided_steps)
        self._r10_guided_step_var.set(f"Step {self._r10_guided_index + 1} of {total}")
        self._r10_guided_title_var.set(step["title"])
        core.tk.Label(
            top, textvariable=self._r10_guided_step_var, bg="#fffaf0", fg="#9a3412",
            font=("Segoe UI", 8, "bold"), anchor="w",
        ).pack(anchor="w")
        core.tk.Label(
            bubble, textvariable=self._r10_guided_title_var, bg="#fffaf0", fg="#172033",
            font=("Segoe UI", 12, "bold"), justify="left", anchor="w", wraplength=330,
        ).pack(fill="x", pady=(3, 5))
        self._r103_body_label = core.tk.Label(
            bubble, text=step["body"], bg="#fffaf0", fg="#334155", font=("Segoe UI", 9),
            justify="left", anchor="w", wraplength=330,
        )
        self._r103_body_label.pack(fill="x")
        self._r103_gate_label = core.tk.Label(
            bubble, textvariable=self._r10_guided_gate_var, bg="#fff7ed", fg="#9a3412",
            font=("Segoe UI", 8, "bold"), justify="left", anchor="w", wraplength=330,
            padx=7, pady=5,
        )
        self._r103_gate_label.pack(fill="x", pady=(8, 7))

        footer = core.tk.Frame(bubble, bg="#fffaf0")
        footer.pack(fill="x")
        self._r102_skip_button = core.ttk.Button(
            footer, text="Skip Tutorial", command=lambda: _skip(self), style="Modern.TButton"
        )
        self._r102_skip_button.pack(side="left")
        self._r10_guided_next = core.ttk.Button(
            footer, text="Finish" if self._r10_guided_index == total - 1 else "Next",
            command=lambda: _move(self, 1), style="Accent.TButton"
        )
        self._r10_guided_next.pack(side="right")
        self._r10_guided_back = core.ttk.Button(
            footer, text="Back", command=lambda: _move(self, -1), style="Modern.TButton"
        )
        self._r10_guided_back.pack(side="right", padx=(0, 6))
        self._r10_guided_back.configure(state="normal" if self._r10_guided_index > 0 else "disabled")

        try:
            host.update_idletasks(); bubble.update_idletasks()
            hw, hh = max(500, host.winfo_width()), max(400, host.winfo_height())
            bw = min(370, max(320, bubble.winfo_reqwidth()))
            bh = min(max(210, bubble.winfo_reqheight()), max(210, hh - 24))
            margin = 12
            direction = ""
            if target is not None:
                hx, hy = host.winfo_rootx(), host.winfo_rooty()
                tx = target.winfo_rootx() - hx
                ty = target.winfo_rooty() - hy
                tw = max(8, target.winfo_width())
                th = max(8, target.winfo_height())
                if tx + tw + 18 + bw <= hw - margin:
                    x, y, direction = tx + tw + 18, ty - 12, "◀"
                elif tx - 18 - bw >= margin:
                    x, y, direction = tx - 18 - bw, ty - 12, "▶"
                elif ty + th + 18 + bh <= hh - margin:
                    x, y, direction = tx, ty + th + 18, "▲"
                else:
                    x, y, direction = tx, ty - 18 - bh, "▼"
            else:
                x, y = hw - bw - 18, 18
            x = max(margin, min(int(x), max(margin, hw - bw - margin)))
            y = max(margin, min(int(y), max(margin, hh - bh - margin)))
            bubble.place(x=x, y=y, width=bw)
            bubble.lift()

            if target is not None and direction:
                tail = core.tk.Label(host, text=direction, bg="#fffaf0", fg="#f59e0b", font=("Segoe UI Symbol", 15, "bold"))
                self._r103_tail = tail
                if direction == "◀":
                    tail.place(x=max(0, x - 15), y=min(hh - 28, y + 18), width=18, height=28)
                elif direction == "▶":
                    tail.place(x=min(hw - 18, x + bw - 2), y=min(hh - 28, y + 18), width=18, height=28)
                elif direction == "▲":
                    tail.place(x=min(hw - 28, x + 18), y=max(0, y - 16), width=28, height=18)
                else:
                    tail.place(x=min(hw - 28, x + 18), y=min(hh - 18, y + bh - 2), width=28, height=18)
                tail.lift()
        except Exception:
            try:
                bubble.place(relx=1.0, x=-390, y=18, width=370)
                bubble.lift()
            except Exception:
                pass

    def _render_step(self):
        if not getattr(self, "_r103_inline_active", False):
            return
        step = _current(self)
        target = _find_target(self, tuple(step.get("target") or ()))
        _place_bubble(self, step, target)
        _update_gate(self)

    def _show_step(self):
        _cancel_job(self, "_r103_gate_job")
        _cancel_job(self, "_r103_render_job")
        step = _current(self)
        try:
            if step.get("page"):
                self._navigate_modern(step["page"])
        except Exception:
            pass
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            self._r103_render_job = self.after(100, lambda: _render_step(self))
        except Exception:
            _render_step(self)

    def _update_gate(self):
        if not getattr(self, "_r103_inline_active", False):
            return
        complete = _gate_complete(self)
        try:
            self._r10_guided_next.configure(state="normal" if complete else "disabled")
            self._r10_guided_gate_var.set(
                "DONE — click Next to continue." if complete
                else "DO THIS NOW — complete the highlighted action in AUTOLEDGER."
            )
            self._r103_gate_label.configure(
                bg="#ecfdf5" if complete else "#fff7ed",
                fg="#166534" if complete else "#9a3412",
            )
        except Exception:
            pass
        try:
            self._r103_gate_job = self.after(250, lambda: _update_gate(self))
        except Exception:
            pass

    def _move(self, delta: int):
        if delta > 0 and not _gate_complete(self):
            return
        current_id = self._r10_guided_steps[self._r10_guided_index]
        if delta < 0 and current_id == "rule_save" and bool(getattr(self, "_r102_last_rule_saved", False)):
            try:
                self._r10_guided_gate_var.set(
                    "The rule has already been saved. Continue with Next, or restart the walkthrough to review the rule fields again."
                )
            except Exception:
                pass
            return
        new_index = self._r10_guided_index + delta
        if new_index >= len(self._r10_guided_steps):
            _finish(self)
            return
        if 0 <= new_index < len(self._r10_guided_steps):
            self._r10_guided_index = new_index
            _show_step(self)

    def _close(self):
        _cancel_job(self, "_r103_gate_job")
        _cancel_job(self, "_r103_render_job")
        try:
            if r102_stop_pointer is not None:
                r102_stop_pointer(self)
        except Exception:
            pass
        _clear_visuals(self)
        self._r10_guided_window = None
        self._r103_inline_active = False
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
        if getattr(self, "_r103_inline_active", False):
            return
        if mode not in {"clean", "update"}:
            mode = "clean"
        self._r10_guided_mode = mode
        self._r10_guided_steps = r102_step_ids(self, mode)
        self._r10_guided_index = 0
        self._r10_tutorial_validation_ok = False
        self._r10_tutorial_export_done = False
        self._r102_last_rule_saved = False
        self._r102_rule_dialog = None
        self._r102_walkthrough_active = True
        self._r103_inline_active = True
        self._r10_guided_window = None
        try:
            if getattr(self, "ui_mode", "modern") != "modern":
                self._apply_ui_mode("modern", initial=True)
        except Exception:
            pass
        try:
            self.deiconify(); self.lift()
        except Exception:
            pass
        _show_step(self)

    def _snapshot(self) -> dict:
        bubble = getattr(self, "_r103_bubble", None)
        host = getattr(self, "_r103_host", None) or self
        target = getattr(self, "_r103_target", None)
        try:
            self.update_idletasks()
        except Exception:
            pass
        bubble_mapped = False
        try:
            bubble_mapped = bool(bubble is not None and bubble.winfo_ismapped())
        except Exception:
            pass
        target_class = _widget_class(target) if target is not None else ""
        return {
            "visible": bool(getattr(self, "_r103_inline_active", False)),
            "inline": True,
            "separate_window": False,
            "title": str(self._r10_guided_title_var.get()).strip() if bubble is not None else "",
            "step": str(self._r10_guided_step_var.get()).strip() if bubble is not None else "",
            "index": int(getattr(self, "_r10_guided_index", -1)),
            "step_id": self._r10_guided_steps[self._r10_guided_index] if getattr(self, "_r10_guided_steps", None) else "",
            "bubble_mapped": bubble_mapped,
            "bubble_class": _widget_class(bubble) if bubble is not None else "",
            "host_class": _widget_class(host),
            "target_class": target_class,
            "target_interactive": bool(target is not None and _is_interactive(target)),
            "highlight_count": sum(1 for x in getattr(self, "_r103_highlight_frames", ()) if getattr(x, "winfo_exists", lambda: 0)()),
            "back": _button_info(self, getattr(self, "_r10_guided_back", None), host) if bubble is not None else {},
            "next": _button_info(self, getattr(self, "_r10_guided_next", None), host) if bubble is not None else {},
            "skip": _button_info(self, getattr(self, "_r102_skip_button", None), host) if bubble is not None else {},
        }

    def _smoke(self, mode: str = "update") -> dict:
        start_walkthrough(self, mode)
        deadline = time.time() + 2.0
        snap = {}
        while time.time() < deadline:
            try:
                self.update()
            except Exception:
                break
            snap = _snapshot(self)
            if snap.get("visible") and snap.get("bubble_mapped") and snap.get("title"):
                break
            time.sleep(0.02)
        return snap

    def _show_step_by_id(self, step_id: str):
        if not getattr(self, "_r103_inline_active", False):
            start_walkthrough(self, "clean")
        try:
            self._r10_guided_index = self._r10_guided_steps.index(step_id)
        except ValueError:
            raise KeyError(step_id)
        _show_step(self)

    App._r103_find_target = _find_target
    App._r103_clear_visuals = _clear_visuals
    App._r103_walkthrough_snapshot = _snapshot
    App._r103_walkthrough_smoke = _smoke
    App._r103_show_step_by_id = _show_step_by_id
    App._r102_walkthrough_snapshot = _snapshot
    App._r102_walkthrough_smoke = _smoke
    App._r10_guided_show_step = _show_step
    App._r10_guided_move = _move
    App._r10_close_guided = _close
    App._r10_skip_guided = _skip
    App._r10_finish_guided = _finish
    App.start_guided_tutorial = start_walkthrough
