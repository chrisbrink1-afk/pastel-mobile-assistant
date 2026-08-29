from __future__ import annotations

import time


R103_REVISION = "R10.3"

R103_UPDATE_FEATURES = (
    {
        "id": "update_r103_inline_walkthrough",
        "title": "The Guided Walkthrough now stays inside AUTOLEDGER",
        "body": (
            "The tutorial no longer opens its own instruction window. AUTOLEDGER now guides you inside the normal program screen, "
            "highlights the exact area you need to use, and shows a small hint bubble beside that area."
        ),
    },
    {
        "id": "update_r103_highlights",
        "title": "Clear highlights replace the moving pointer",
        "body": (
            "The old moving DO THIS NOW pointer has been removed. The walkthrough now uses a clear border around the real button, field "
            "or section you need to use. When the required action is complete the highlight changes to a completed state."
        ),
    },
    {
        "id": "update_r103_hints",
        "title": "Hints and instructions appear beside the real control",
        "body": (
            "Each walkthrough step places a speech-bubble style hint beside the highlighted control. Back, Skip Tutorial and Next remain "
            "available in an in-app walkthrough bar. Required steps still keep Next locked until the action has actually been completed."
        ),
    },
)

R103_HELP_TOPICS = (
    {
        "id": "guided_walkthrough_r103_inline",
        "title": "How the in-app Guided Walkthrough works",
        "page": "dashboard",
        "keywords": "guided walkthrough tutorial highlight field speech bubble hint tips no popup next locked",
        "body": (
            "The Guided Walkthrough runs inside the normal AUTOLEDGER interface. AUTOLEDGER automatically opens the correct page, "
            "highlights the real control or setting you need to use, and shows a small instruction bubble beside it. There is no separate "
            "tutorial window. Back, Skip Tutorial and Next appear in an in-app walkthrough bar. On required steps Next remains disabled "
            "until AUTOLEDGER detects that the requested action has been completed."
        ),
    },
    {
        "id": "guided_walkthrough_r103_highlight",
        "title": "What the highlighted area means",
        "page": "dashboard",
        "keywords": "highlight highlighted border amber green tutorial area field control",
        "body": (
            "An amber border means this is the area you should work with now. Read the nearby hint, then change or use the highlighted "
            "field, button or section. When AUTOLEDGER can confirm the required result, the walkthrough status changes to complete and "
            "Next becomes available."
        ),
    },
)


def register_r103_curriculum(guided_tutorial_module, revision: str = R103_REVISION) -> None:
    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R103_UPDATE_FEATURES


def install_r103_inline_walkthrough(core, edition: str, licence_info=None, revision: str = R103_REVISION) -> None:
    """Replace the R10.2 popup walkthrough shell with an in-window guided overlay.

    R10.3 keeps the R10/R10.2 workflow, completion gates, rule-field tracking,
    clean-vs-update behaviour and permanent tutorial state. It changes only the
    walkthrough presentation:
      * no tutorial Toplevel/window is created;
      * the real target is highlighted with four non-blocking border strips;
      * a hint bubble is placed beside the target inside the existing window;
      * Back / Skip Tutorial / Next live in an in-app bar;
      * required-action gates continue to control Next.
    """
    App = core.App

    existing = {t.get("id") for t in getattr(core, "TUTORIAL_TOPICS", ())}
    topics = list(getattr(core, "TUTORIAL_TOPICS", ()))
    for topic in R103_HELP_TOPICS:
        if topic["id"] not in existing:
            topics.append(dict(topic))
    core.TUTORIAL_TOPICS = tuple(topics)

    old_help = getattr(App, "start_tutorial", None)

    def _current_step(self) -> dict:
        return self._r102_step_definition(self._r10_guided_steps[self._r10_guided_index])

    def _gate_complete(self) -> bool:
        try:
            return bool(_current_step(self)["gate"]())
        except Exception:
            return False

    def _top_host(self, target=None):
        if target is not None:
            try:
                host = target.winfo_toplevel()
                if host is not None:
                    return host
            except Exception:
                pass
        return self

    def _widget_box_in_host(widget, host):
        widget.update_idletasks()
        host.update_idletasks()
        return (
            int(widget.winfo_rootx() - host.winfo_rootx()),
            int(widget.winfo_rooty() - host.winfo_rooty()),
            max(1, int(widget.winfo_width())),
            max(1, int(widget.winfo_height())),
        )

    def _is_interactive(widget) -> bool:
        try:
            cls = str(widget.winfo_class()).casefold()
        except Exception:
            return False
        return any(part in cls for part in (
            "entry", "combobox", "spinbox", "button", "checkbutton",
            "radiobutton", "listbox", "treeview", "text",
        ))

    def _expanded_target_box(self, target, host):
        """Highlight a label together with its nearby input where possible."""
        box = _widget_box_in_host(target, host)
        widgets = [target]
        try:
            target_cls = str(target.winfo_class()).casefold()
        except Exception:
            target_cls = ""
        if "label" in target_cls:
            try:
                tx, ty, tw, th = box
                tcx = tx + tw / 2
                tcy = ty + th / 2
                candidates = []
                for sibling in target.master.winfo_children():
                    if sibling is target or not _is_interactive(sibling):
                        continue
                    try:
                        if not sibling.winfo_ismapped():
                            continue
                        sx, sy, sw, sh = _widget_box_in_host(sibling, host)
                        scx = sx + sw / 2
                        scy = sy + sh / 2
                        same_row = abs(scy - tcy) <= max(45, th * 2)
                        same_col = abs(scx - tcx) <= max(220, tw * 3)
                        if not (same_row or same_col):
                            continue
                        dist = abs(scx - tcx) + abs(scy - tcy)
                        candidates.append((dist, sibling))
                    except Exception:
                        continue
                if candidates:
                    candidates.sort(key=lambda item: item[0])
                    widgets.append(candidates[0][1])
            except Exception:
                pass

        boxes = []
        for widget in widgets:
            try:
                boxes.append(_widget_box_in_host(widget, host))
            except Exception:
                pass
        if not boxes:
            return box
        left = min(x for x, y, w, h in boxes)
        top = min(y for x, y, w, h in boxes)
        right = max(x + w for x, y, w, h in boxes)
        bottom = max(y + h for x, y, w, h in boxes)
        pad = 5
        return (left - pad, top - pad, right - left + pad * 2, bottom - top + pad * 2)

    def _destroy_widgets(items):
        for item in list(items or []):
            try:
                item.destroy()
            except Exception:
                pass

    def _clear_highlight(self):
        _destroy_widgets(getattr(self, "_r103_highlight_parts", []))
        self._r103_highlight_parts = []
        self._r103_highlight_target = None
        self._r103_highlight_host = None

    def _clear_bubble(self):
        bubble = getattr(self, "_r103_hint_bubble", None)
        if bubble is not None:
            try:
                bubble.destroy()
            except Exception:
                pass
        self._r103_hint_bubble = None
        self._r103_bubble_host = None
        self._r103_bubble_title = None
        self._r103_bubble_body = None
        self._r103_bubble_status = None

    def _clear_bar(self):
        bar = getattr(self, "_r103_walkthrough_bar", None)
        if bar is not None:
            try:
                bar.destroy()
            except Exception:
                pass
        self._r103_walkthrough_bar = None
        self._r103_bar_host = None
        self._r103_step_label = None
        self._r103_status_label = None
        self._r10_guided_back = None
        self._r10_guided_next = None
        self._r103_skip_button = None

    def _ensure_bar(self, host):
        current = getattr(self, "_r103_bar_host", None)
        bar = getattr(self, "_r103_walkthrough_bar", None)
        try:
            usable = bar is not None and bar.winfo_exists() and current is host
        except Exception:
            usable = False
        if usable:
            return bar
        _clear_bar(self)

        bar = core.tk.Frame(host, bg="#0f2744", padx=10, pady=8, highlightthickness=1, highlightbackground="#1f4d72")
        self._r103_walkthrough_bar = bar
        self._r103_bar_host = host
        bar.place(relx=0.0, rely=1.0, relwidth=1.0, anchor="sw")

        self._r103_step_label = core.tk.Label(bar, text="", bg="#0f2744", fg="#d9f3ed", font=("Segoe UI", 9, "bold"))
        self._r103_step_label.pack(side="left")
        self._r103_status_label = core.tk.Label(bar, text="", bg="#0f2744", fg="#ffffff", font=("Segoe UI", 9), padx=14)
        self._r103_status_label.pack(side="left", fill="x", expand=True)

        self._r103_skip_button = core.ttk.Button(bar, text="Skip Tutorial", command=lambda: _skip(self), style="Modern.TButton")
        self._r103_skip_button.pack(side="right")
        self._r10_guided_next = core.ttk.Button(bar, text="Next", command=lambda: _move(self, 1), style="Accent.TButton")
        self._r10_guided_next.pack(side="right", padx=(6, 6))
        self._r10_guided_back = core.ttk.Button(bar, text="Back", command=lambda: _move(self, -1), style="Modern.TButton")
        self._r10_guided_back.pack(side="right")
        try:
            bar.lift()
        except Exception:
            pass
        return bar

    def _make_highlight(self, host, box, complete: bool):
        _clear_highlight(self)
        x, y, w, h = box
        thickness = 4
        colour = "#16a34a" if complete else "#f59e0b"
        parts = [
            core.tk.Frame(host, bg=colour, bd=0),
            core.tk.Frame(host, bg=colour, bd=0),
            core.tk.Frame(host, bg=colour, bd=0),
            core.tk.Frame(host, bg=colour, bd=0),
        ]
        parts[0].place(x=x, y=y, width=max(1, w), height=thickness)
        parts[1].place(x=x, y=y + h - thickness, width=max(1, w), height=thickness)
        parts[2].place(x=x, y=y, width=thickness, height=max(1, h))
        parts[3].place(x=x + w - thickness, y=y, width=thickness, height=max(1, h))
        for part in parts:
            try:
                part.lift()
            except Exception:
                pass
        self._r103_highlight_parts = parts
        self._r103_highlight_host = host

    def _make_bubble(self, host, box, step: dict, complete: bool):
        _clear_bubble(self)
        try:
            host.update_idletasks()
            host_w = max(360, int(host.winfo_width()))
            host_h = max(300, int(host.winfo_height()))
        except Exception:
            host_w, host_h = 900, 650

        bubble_width = min(390, max(300, host_w - 60))
        fill = "#f0fdf4" if complete else "#fff8dc"
        border = "#16a34a" if complete else "#d97706"
        bubble = core.tk.Frame(host, bg=fill, padx=12, pady=10, highlightthickness=2, highlightbackground=border)
        self._r103_hint_bubble = bubble
        self._r103_bubble_host = host

        self._r103_bubble_title = core.tk.Label(
            bubble, text=step["title"], bg=fill, fg="#172033", font=("Segoe UI", 11, "bold"),
            justify="left", anchor="w", wraplength=bubble_width - 28,
        )
        self._r103_bubble_title.pack(fill="x")
        self._r103_bubble_body = core.tk.Label(
            bubble, text=step["body"], bg=fill, fg="#334155", font=("Segoe UI", 9),
            justify="left", anchor="w", wraplength=bubble_width - 28,
        )
        self._r103_bubble_body.pack(fill="x", pady=(6, 6))
        status_text = "DONE — click Next when you are ready." if complete else "DO THIS NOW — complete the highlighted action."
        self._r103_bubble_status = core.tk.Label(
            bubble, text=status_text, bg=fill, fg="#166534" if complete else "#9a3412",
            font=("Segoe UI", 9, "bold"), justify="left", anchor="w", wraplength=bubble_width - 28,
        )
        self._r103_bubble_status.pack(fill="x")

        bubble.update_idletasks()
        bw = min(bubble_width, max(260, bubble.winfo_reqwidth()))
        bh = max(90, bubble.winfo_reqheight())
        margin = 12
        if box is None:
            x = max(margin, min(host_w - bw - margin, host_w - bw - 24))
            y = 24
        else:
            tx, ty, tw, th = box
            right_x = tx + tw + margin
            left_x = tx - bw - margin
            below_y = ty + th + margin
            above_y = ty - bh - margin
            if right_x + bw <= host_w - margin:
                x = right_x
                y = max(margin, min(ty, host_h - bh - 70))
            elif left_x >= margin:
                x = left_x
                y = max(margin, min(ty, host_h - bh - 70))
            elif below_y + bh <= host_h - 70:
                x = max(margin, min(tx, host_w - bw - margin))
                y = below_y
            else:
                x = max(margin, min(tx, host_w - bw - margin))
                y = max(margin, above_y)
        bubble.place(x=int(x), y=int(y), width=int(bw))
        try:
            bubble.lift()
        except Exception:
            pass

    def _render_visuals(self):
        if not getattr(self, "_r103_walkthrough_active", False):
            return
        step = _current_step(self)
        complete = _gate_complete(self)
        candidates = tuple(step.get("target") or ())
        target = None
        if candidates:
            try:
                target = self._r102_find_target(candidates)
            except Exception:
                target = None
        host = _top_host(self, target)
        _ensure_bar(self, host)

        total = len(self._r10_guided_steps)
        try:
            self._r103_step_label.configure(text=f"Step {self._r10_guided_index + 1} of {total}")
            self._r103_status_label.configure(
                text="Completed — Next is available." if complete else "Complete the highlighted step before continuing."
            )
            self._r10_guided_back.configure(state="normal" if self._r10_guided_index > 0 else "disabled")
            self._r10_guided_next.configure(
                text="Finish" if self._r10_guided_index == total - 1 else "Next",
                state="normal" if complete else "disabled",
            )
        except Exception:
            pass

        if target is not None:
            try:
                box = _expanded_target_box(self, target, host)
                _make_highlight(self, host, box, complete)
                _make_bubble(self, host, box, step, complete)
                self._r103_highlight_target = target
            except Exception:
                _clear_highlight(self)
                _make_bubble(self, host, None, step, complete)
        else:
            _clear_highlight(self)
            _make_bubble(self, host, None, step, complete)

        try:
            self._r103_walkthrough_bar.lift()
        except Exception:
            pass

    def _schedule_refresh(self):
        old_job = getattr(self, "_r103_refresh_job", None)
        if old_job:
            try:
                self.after_cancel(old_job)
            except Exception:
                pass
        if not getattr(self, "_r103_walkthrough_active", False):
            self._r103_refresh_job = None
            return

        def refresh():
            if not getattr(self, "_r103_walkthrough_active", False):
                return
            try:
                _render_visuals(self)
            except Exception:
                pass
            try:
                self._r103_refresh_job = self.after(450, refresh)
            except Exception:
                self._r103_refresh_job = None

        try:
            self._r103_refresh_job = self.after(450, refresh)
        except Exception:
            self._r103_refresh_job = None

    def _show_step(self):
        step = _current_step(self)
        try:
            if step.get("page"):
                self._navigate_modern(step["page"])
        except Exception:
            pass
        try:
            self.after(100, lambda: _render_visuals(self))
        except Exception:
            _render_visuals(self)
        _schedule_refresh(self)

    def _move(self, delta: int):
        if delta > 0 and not _gate_complete(self):
            return
        current_id = self._r10_guided_steps[self._r10_guided_index]
        if delta < 0 and current_id == "rule_save" and bool(getattr(self, "_r102_last_rule_saved", False)):
            try:
                self._r103_status_label.configure(text="That rule has already been saved. Continue with Next or restart the walkthrough to review it again.")
            except Exception:
                pass
            return
        new_index = self._r10_guided_index + delta
        if new_index >= len(self._r10_guided_steps):
            _finish(self)
            return
        if 0 <= new_index < len(self._r10_guided_steps):
            self._r10_guided_index = new_index
            _clear_highlight(self)
            _clear_bubble(self)
            _show_step(self)

    def _close(self):
        job = getattr(self, "_r103_refresh_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._r103_refresh_job = None
        _clear_highlight(self)
        _clear_bubble(self)
        _clear_bar(self)
        self._r103_walkthrough_active = False
        self._r102_walkthrough_active = False
        # R10.3 deliberately has no tutorial window.
        self._r10_guided_window = None

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

    def start_inline_walkthrough(self, mode: str | None = None):
        if getattr(self, "_r103_walkthrough_active", False):
            try:
                _render_visuals(self)
            except Exception:
                pass
            return
        if mode not in {"clean", "update"}:
            mode = "clean"
        self._r10_guided_mode = mode
        self._r10_guided_steps = self._r102_step_ids(mode)
        self._r10_guided_index = 0
        self._r10_tutorial_validation_ok = False
        self._r10_tutorial_export_done = False
        self._r102_last_rule_saved = False
        self._r102_rule_dialog = None
        self._r102_walkthrough_active = True
        self._r103_walkthrough_active = True
        self._r10_guided_window = None
        try:
            if getattr(self, "ui_mode", "modern") != "modern":
                self._apply_ui_mode("modern", initial=True)
        except Exception:
            pass
        try:
            self.deiconify()
            self.lift()
            self.update_idletasks()
        except Exception:
            pass
        _show_step(self)

    def _snapshot(self) -> dict:
        def info(widget):
            try:
                return {
                    "exists": bool(widget.winfo_exists()),
                    "mapped": bool(widget.winfo_ismapped()),
                    "text": str(widget.cget("text")),
                    "state": str(widget.cget("state")),
                }
            except Exception:
                return {"exists": False, "mapped": False, "text": "", "state": ""}

        bubble = getattr(self, "_r103_hint_bubble", None)
        highlight = list(getattr(self, "_r103_highlight_parts", []) or [])
        title = ""
        body = ""
        try:
            title = str(self._r103_bubble_title.cget("text") or "")
            body = str(self._r103_bubble_body.cget("text") or "")
        except Exception:
            pass
        return {
            "active": bool(getattr(self, "_r103_walkthrough_active", False)),
            "no_tutorial_window": getattr(self, "_r10_guided_window", None) is None,
            "step_id": self._r10_guided_steps[self._r10_guided_index] if getattr(self, "_r10_guided_steps", None) else "",
            "index": int(getattr(self, "_r10_guided_index", -1)),
            "title": title.strip(),
            "body": body.strip(),
            "bubble_mapped": bool(bubble is not None and bubble.winfo_ismapped()) if bubble is not None else False,
            "highlight_parts": sum(1 for part in highlight if getattr(part, "winfo_exists", lambda: 0)()),
            "back": info(getattr(self, "_r10_guided_back", None)),
            "next": info(getattr(self, "_r10_guided_next", None)),
            "skip": info(getattr(self, "_r103_skip_button", None)),
        }

    def _inline_smoke(self, mode: str = "update") -> dict:
        start_inline_walkthrough(self, mode)
        deadline = time.time() + 2.0
        snap = {}
        while time.time() < deadline:
            try:
                self.update()
            except Exception:
                break
            snap = _snapshot(self)
            if snap.get("active") and snap.get("no_tutorial_window") and snap.get("bubble_mapped") and snap.get("title"):
                break
            time.sleep(0.03)
        return snap

    def help_with_r103(self, *args, **kwargs):
        result = old_help(self, *args, **kwargs) if old_help is not None else None
        btn = getattr(self, "_r10_help_guided_button", None)
        if btn is not None:
            try:
                btn.configure(
                    text="Run Guided Walkthrough",
                    command=lambda: (self._tutorial_close(), self.after(80, lambda: self.start_guided_tutorial("clean"))),
                )
            except Exception:
                pass
        return result

    App._r103_current_step = _current_step
    App._r103_gate_complete = _gate_complete
    App._r103_clear_highlight = _clear_highlight
    App._r103_clear_bubble = _clear_bubble
    App._r103_clear_bar = _clear_bar
    App._r103_render_visuals = _render_visuals
    App._r103_inline_snapshot = _snapshot
    App._r103_inline_smoke = _inline_smoke
    App._r10_guided_show_step = _show_step
    App._r10_guided_move = _move
    App._r10_close_guided = _close
    App._r10_skip_guided = _skip
    App._r10_finish_guided = _finish
    App.start_guided_tutorial = start_inline_walkthrough
    if old_help is not None:
        App.start_tutorial = help_with_r103
