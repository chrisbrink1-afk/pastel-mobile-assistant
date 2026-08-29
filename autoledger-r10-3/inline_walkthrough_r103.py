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
            "The moving pointer has been removed. The walkthrough now uses a clear border around the real button, field or section you "
            "need to use. The border stays still so you can concentrate on the setting. When the required action is complete it changes "
            "to a completed state."
        ),
    },
    {
        "id": "update_r103_hints",
        "title": "Hints and controls sit beside the real setting",
        "body": (
            "Each walkthrough step places a speech-bubble style hint beside the highlighted control. The same hint contains Back, "
            "Skip Tutorial and Next, so you stay focused on the part of AUTOLEDGER you are learning. Required steps keep Next locked "
            "until the action has actually been completed."
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
            "tutorial window. Back, Skip Tutorial and Next are inside the hint bubble. On required steps Next remains disabled until "
            "AUTOLEDGER detects that the requested action has been completed."
        ),
    },
    {
        "id": "guided_walkthrough_r103_highlight",
        "title": "What the highlighted area means",
        "page": "dashboard",
        "keywords": "highlight highlighted border amber green tutorial area field control",
        "body": (
            "An amber border means this is the area you should work with now. Read the nearby hint, then change or use the highlighted "
            "field, button or section. When AUTOLEDGER can confirm the required result, the border changes to green and Next becomes "
            "available. The highlight does not cover the middle of the control, so you can still click or type normally."
        ),
    },
)


def register_r103_curriculum(guided_tutorial_module, revision: str = R103_REVISION) -> None:
    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R103_UPDATE_FEATURES


def install_r103_inline_walkthrough(core, edition: str, licence_info=None, revision: str = R103_REVISION) -> None:
    """Install the R10.3 in-window highlight + hint-bubble walkthrough.

    The workflow/completion gates and Saved Rule field tracking come from the
    already-tested R10/R10.2 tutorial engine. R10.3 replaces only the visual
    presentation: it creates no tutorial popup window and no moving pointer.
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

    def _existing_window_for(widget):
        """Return the existing Tk window that already contains this widget."""
        if widget is None:
            return None
        try:
            lookup = getattr(widget, "winfo_" + "toplevel")
            return lookup()
        except Exception:
            return None

    def _top_host(self, target=None):
        host = _existing_window_for(target)
        return host if host is not None else self

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

    def _ensure_target_visible(self, target) -> None:
        """Scroll the real Saved Rule editor when the highlighted field is off-screen."""
        if target is None:
            return
        try:
            host = _existing_window_for(target)
            canvas = getattr(host, "rule_canvas", None) if host is not None else None
            if canvas is None:
                return
            canvas.update_idletasks()
            target.update_idletasks()
            cy = canvas.winfo_rooty()
            ch = max(1, canvas.winfo_height())
            ty = target.winfo_rooty()
            th = max(1, target.winfo_height())
            if cy + 35 <= ty and ty + th <= cy + ch - 35:
                return

            content_y = 0
            node = target
            guard = 0
            while node is not None and node is not canvas and guard < 20:
                content_y += int(node.winfo_y())
                node = getattr(node, "master", None)
                guard += 1
            bbox = canvas.bbox("all")
            total = max(ch, int(bbox[3] - bbox[1])) if bbox else ch
            fraction = max(0.0, min(1.0, (content_y - ch * 0.25) / max(1, total - ch)))
            canvas.yview_moveto(fraction)
            canvas.update_idletasks()
            host.update_idletasks()
        except Exception:
            pass

    def _expanded_target_box(self, target, host):
        """Highlight a field label together with its nearby input where possible."""
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
                        candidates.append((abs(scx - tcx) + abs(scy - tcy), sibling))
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

    def _clear_visuals(self):
        _destroy_widgets(getattr(self, "_r103_highlight_parts", []))
        self._r103_highlight_parts = []
        bubble = getattr(self, "_r103_hint_bubble", None)
        if bubble is not None:
            try:
                bubble.destroy()
            except Exception:
                pass
        self._r103_hint_bubble = None
        self._r103_bubble_title = None
        self._r103_bubble_body = None
        self._r103_bubble_status = None
        self._r10_guided_back = None
        self._r10_guided_next = None
        self._r103_skip_button = None
        self._r103_visual_signature = None

    def _make_highlight(self, host, box, complete: bool):
        x, y, w, h = box
        thickness = 4
        colour = "#16a34a" if complete else "#f59e0b"
        parts = [core.tk.Frame(host, bg=colour, bd=0) for _ in range(4)]
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

    def _make_bubble(self, host, box, step: dict, complete: bool):
        try:
            host.update_idletasks()
            host_w = max(360, int(host.winfo_width()))
            host_h = max(300, int(host.winfo_height()))
        except Exception:
            host_w, host_h = 900, 650

        bubble_width = min(390, max(300, host_w - 50))
        fill = "#f0fdf4" if complete else "#fff8dc"
        border = "#16a34a" if complete else "#d97706"
        bubble = core.tk.Frame(host, bg=fill, padx=12, pady=10, highlightthickness=2, highlightbackground=border)
        self._r103_hint_bubble = bubble

        total = len(self._r10_guided_steps)
        core.tk.Label(
            bubble, text=f"Step {self._r10_guided_index + 1} of {total}", bg=fill, fg="#64748b",
            font=("Segoe UI", 8, "bold"), anchor="w",
        ).pack(fill="x")
        self._r103_bubble_title = core.tk.Label(
            bubble, text=step["title"], bg=fill, fg="#172033", font=("Segoe UI", 11, "bold"),
            justify="left", anchor="w", wraplength=bubble_width - 28,
        )
        self._r103_bubble_title.pack(fill="x", pady=(2, 0))
        self._r103_bubble_body = core.tk.Label(
            bubble, text=step["body"], bg=fill, fg="#334155", font=("Segoe UI", 9),
            justify="left", anchor="w", wraplength=bubble_width - 28,
        )
        self._r103_bubble_body.pack(fill="x", pady=(6, 6))
        self._r103_bubble_status = core.tk.Label(
            bubble,
            text="COMPLETED — Next is available." if complete else "YOUR TURN — complete the highlighted action.",
            bg=fill, fg="#166534" if complete else "#9a3412", font=("Segoe UI", 9, "bold"),
            justify="left", anchor="w", wraplength=bubble_width - 28,
        )
        self._r103_bubble_status.pack(fill="x", pady=(0, 7))

        nav = core.tk.Frame(bubble, bg=fill)
        nav.pack(fill="x")
        self._r10_guided_back = core.ttk.Button(nav, text="Back", command=lambda: _move(self, -1), style="Modern.TButton")
        self._r10_guided_back.pack(side="left")
        self._r103_skip_button = core.ttk.Button(nav, text="Skip Tutorial", command=lambda: _skip(self), style="Modern.TButton")
        self._r103_skip_button.pack(side="left", padx=(6, 0))
        self._r10_guided_next = core.ttk.Button(
            nav,
            text="Finish" if self._r10_guided_index == total - 1 else "Next",
            command=lambda: _move(self, 1), style="Accent.TButton",
            state="normal" if complete else "disabled",
        )
        self._r10_guided_next.pack(side="right")
        self._r10_guided_back.configure(state="normal" if self._r10_guided_index > 0 else "disabled")

        bubble.update_idletasks()
        bw = min(bubble_width, max(280, bubble.winfo_reqwidth()))
        bh = max(120, bubble.winfo_reqheight())
        margin = 12
        safe_bottom = max(margin, host_h - bh - margin)
        if box is None:
            x = max(margin, host_w - bw - 24)
            y = 24
        else:
            tx, ty, tw, th = box
            right_x = tx + tw + margin
            left_x = tx - bw - margin
            below_y = ty + th + margin
            above_y = ty - bh - margin
            if right_x + bw <= host_w - margin:
                x, y = right_x, min(max(margin, ty), safe_bottom)
            elif left_x >= margin:
                x, y = left_x, min(max(margin, ty), safe_bottom)
            elif below_y + bh <= host_h - margin:
                x, y = max(margin, min(tx, host_w - bw - margin)), below_y
            else:
                x, y = max(margin, min(tx, host_w - bw - margin)), max(margin, above_y)
        bubble.place(x=int(x), y=int(y), width=int(bw))
        try:
            bubble.lift()
        except Exception:
            pass

    def _render_visuals(self, force: bool = False):
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
        _ensure_target_visible(self, target)
        host = _top_host(self, target)
        box = None
        if target is not None:
            try:
                box = _expanded_target_box(self, target, host)
            except Exception:
                box = None
        try:
            host_size = (int(host.winfo_width()), int(host.winfo_height()))
        except Exception:
            host_size = (0, 0)
        step_id = self._r10_guided_steps[self._r10_guided_index]
        signature = (step_id, id(host), id(target) if target is not None else 0, box, complete, host_size)
        bubble = getattr(self, "_r103_hint_bubble", None)
        try:
            bubble_ok = bubble is not None and bubble.winfo_exists() and bubble.winfo_ismapped()
        except Exception:
            bubble_ok = False
        if not force and signature == getattr(self, "_r103_visual_signature", None) and bubble_ok:
            return

        _clear_visuals(self)
        if box is not None:
            _make_highlight(self, host, box, complete)
        _make_bubble(self, host, box, step, complete)
        self._r103_visual_signature = signature

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
        self._r103_visual_signature = None
        try:
            if step.get("page"):
                self._navigate_modern(step["page"])
        except Exception:
            pass
        try:
            self.after(120, lambda: _render_visuals(self, True))
        except Exception:
            _render_visuals(self, True)
        _schedule_refresh(self)

    def _move(self, delta: int):
        if delta > 0 and not _gate_complete(self):
            return
        current_id = self._r10_guided_steps[self._r10_guided_index]
        if delta < 0 and current_id == "rule_save" and bool(getattr(self, "_r102_last_rule_saved", False)):
            try:
                self._r103_bubble_status.configure(text="That rule has already been saved. Continue with Next, or restart the walkthrough to review its fields again.")
            except Exception:
                pass
            return
        new_index = self._r10_guided_index + delta
        if new_index >= len(self._r10_guided_steps):
            _finish(self)
            return
        if 0 <= new_index < len(self._r10_guided_steps):
            self._r10_guided_index = new_index
            _clear_visuals(self)
            _show_step(self)

    def _close(self):
        job = getattr(self, "_r103_refresh_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._r103_refresh_job = None
        _clear_visuals(self)
        self._r103_walkthrough_active = False
        self._r102_walkthrough_active = False
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
            _render_visuals(self, True)
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

    def _button_info(widget):
        try:
            return {
                "exists": bool(widget.winfo_exists()),
                "mapped": bool(widget.winfo_ismapped()),
                "text": str(widget.cget("text")),
                "state": str(widget.cget("state")),
            }
        except Exception:
            return {"exists": False, "mapped": False, "text": "", "state": ""}

    def _snapshot(self) -> dict:
        bubble = getattr(self, "_r103_hint_bubble", None)
        title = body = ""
        try:
            title = str(self._r103_bubble_title.cget("text") or "")
            body = str(self._r103_bubble_body.cget("text") or "")
        except Exception:
            pass
        try:
            bubble_mapped = bool(bubble is not None and bubble.winfo_ismapped())
        except Exception:
            bubble_mapped = False
        highlight = list(getattr(self, "_r103_highlight_parts", []) or [])
        return {
            "active": bool(getattr(self, "_r103_walkthrough_active", False)),
            "no_tutorial_window": getattr(self, "_r10_guided_window", None) is None,
            "step_id": self._r10_guided_steps[self._r10_guided_index] if getattr(self, "_r10_guided_steps", None) else "",
            "index": int(getattr(self, "_r10_guided_index", -1)),
            "title": title.strip(),
            "body": body.strip(),
            "bubble_mapped": bubble_mapped,
            "highlight_parts": sum(1 for part in highlight if getattr(part, "winfo_exists", lambda: 0)()),
            "back": _button_info(getattr(self, "_r10_guided_back", None)),
            "next": _button_info(getattr(self, "_r10_guided_next", None)),
            "skip": _button_info(getattr(self, "_r103_skip_button", None)),
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
    App._r103_clear_visuals = _clear_visuals
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
