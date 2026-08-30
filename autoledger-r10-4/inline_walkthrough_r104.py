from __future__ import annotations

import time

from r104_curriculum import R104_HELP_TOPICS, R104_REVISION, register_r104_curriculum
from r104_overlay import NonObscuringOverlay
from r104_targets import resolve_target, widget_class, widget_exists


def install_r104_walkthrough(core, edition: str, licence_info=None, revision: str = R104_REVISION) -> None:
    """Install the R10.4 tutorial presentation layer.

    R10.4 deliberately leaves all accounting logic and the proven R10.2 action gates
    intact. It supersedes only tutorial target resolution and tutorial rendering.
    """
    App = core.App

    existing = {t.get("id") for t in getattr(core, "TUTORIAL_TOPICS", ())}
    topics = list(getattr(core, "TUTORIAL_TOPICS", ()))
    for topic in R104_HELP_TOPICS:
        if topic["id"] not in existing:
            topics.append(dict(topic))
    core.TUTORIAL_TOPICS = tuple(topics)

    base_definition = getattr(App, "_r103_definition", None) or getattr(App, "_r102_step_definition", None)
    step_ids = getattr(App, "_r102_step_ids", None)
    if base_definition is None or step_ids is None:
        raise RuntimeError("R10.4 requires the validated R10.2/R10.3 walkthrough layers")

    def definition(self, step_id: str) -> dict:
        d = dict(base_definition(self, step_id))
        if step_id == "rule_priority":
            d["title"] = "Saved Rule — Priority (normally leave at 100)"
            d["body"] = (
                "Priority decides which Saved Rule wins only when more than one rule could match the same bank transaction. "
                "For a normal rule, leave Priority at 100. Use a higher number such as 200 or 300 only for a more specific rule that "
                "must take precedence over a broader rule. Higher numbers are considered first. Do not increase Priority merely because "
                "a rule feels important; change it only to resolve an intentional overlap between rules."
            )
        return d

    def current(self):
        return definition(self, self._r10_guided_steps[self._r10_guided_index])

    def gate_complete(self):
        try:
            return bool(current(self)["gate"]())
        except Exception:
            return False

    def _destroy_previous_overlays(self):
        for attr in ("_r104_overlay", "_r103_overlay"):
            overlay = getattr(self, attr, None)
            if overlay is not None:
                try:
                    overlay.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)
        # R10.4 never uses the old R10.2 pointer Toplevel.
        old_pointer = getattr(self, "_r102_pointer_window", None)
        if old_pointer is not None:
            try:
                old_pointer.destroy()
            except Exception:
                pass
        self._r102_pointer_window = None

    def close(self):
        for attr in ("_r104_tick_job", "_r103_tick_job"):
            job = getattr(self, attr, None)
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
            setattr(self, attr, None)
        _destroy_previous_overlays(self)
        self._r104_walkthrough_active = False
        self._r103_walkthrough_active = False
        self._r102_walkthrough_active = False
        old = getattr(self, "_r10_guided_window", None)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
        self._r10_guided_window = None

    def skip(self):
        try:
            self._r10_record_guided_state("skipped", self._r10_guided_mode)
        except Exception:
            pass
        try:
            self.status_var.set("Guided walkthrough skipped. You can run it again from Tutorial & Help.")
        except Exception:
            pass
        close(self)

    def finish(self):
        try:
            self._r10_record_guided_state("completed", self._r10_guided_mode)
        except Exception:
            pass
        try:
            self.status_var.set("Guided walkthrough completed. Searchable Help remains available whenever you need it.")
        except Exception:
            pass
        close(self)

    def move(self, delta: int):
        if delta > 0 and not gate_complete(self):
            return
        current_id = self._r10_guided_steps[self._r10_guided_index]
        if delta < 0 and current_id == "rule_save" and bool(getattr(self, "_r102_last_rule_saved", False)):
            try:
                self._r104_overlay.gate_var.set(
                    "The rule has already been saved. Continue with Next, or restart the walkthrough to review those fields again."
                )
            except Exception:
                pass
            return
        n = self._r10_guided_index + delta
        if n >= len(self._r10_guided_steps):
            finish(self)
            return
        if 0 <= n < len(self._r10_guided_steps):
            self._r10_guided_index = n
            render(self)

    def overlay_for(self):
        ov = getattr(self, "_r104_overlay", None)
        if ov is None:
            ov = NonObscuringOverlay(core, self, lambda: move(self, -1), lambda: move(self, 1), lambda: skip(self))
            self._r104_overlay = ov
        return ov

    def render(self):
        if not getattr(self, "_r104_walkthrough_active", False):
            return
        step_id = self._r10_guided_steps[self._r10_guided_index]
        step = definition(self, step_id)
        try:
            if step.get("page"):
                self._navigate_modern(step["page"])
                self.update_idletasks()
        except Exception:
            pass
        target = resolve_target(self, tuple(step.get("target") or ()), step_id)
        overlay_for(self).render(step, target, self._r10_guided_index, len(self._r10_guided_steps), gate_complete(self))
        self._r10_guided_step_var = self._r104_overlay.step_var
        self._r10_guided_title_var = self._r104_overlay.title_var
        self._r10_guided_gate_var = self._r104_overlay.gate_var
        self._r10_guided_back = self._r104_overlay.back
        self._r10_guided_next = self._r104_overlay.next
        self._r102_skip_button = self._r104_overlay.skip
        self._r102_gate_label = self._r104_overlay.gate_label
        try:
            if target is not None and widget_class(target) in {
                "entry", "tentry", "combobox", "tcombobox", "spinbox", "tspinbox", "text"
            }:
                target.focus_set()
        except Exception:
            pass

    def tick(self):
        if not getattr(self, "_r104_walkthrough_active", False):
            return
        step_id = self._r10_guided_steps[self._r10_guided_index]
        step = definition(self, step_id)
        target = resolve_target(self, tuple(step.get("target") or ()), step_id)
        ov = overlay_for(self)
        try:
            root = target.winfo_toplevel() if target is not None else self
        except Exception:
            root = self
        if ov.root is not root or not widget_exists(ov.bubble):
            render(self)
        else:
            ov.target = target
            ov.update_gate(gate_complete(self))
            ov.position()
        try:
            self._r104_tick_job = self.after(220, lambda: tick(self))
        except Exception:
            self._r104_tick_job = None

    def start(self, mode: str | None = None):
        if getattr(self, "_r104_walkthrough_active", False):
            render(self)
            return
        if mode not in {"clean", "update"}:
            mode = "clean"
        _destroy_previous_overlays(self)
        for attr in ("_r103_tick_job", "_r104_tick_job"):
            job = getattr(self, attr, None)
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
            setattr(self, attr, None)
        self._r10_guided_mode = mode
        self._r10_guided_steps = list(step_ids(self, mode))
        self._r10_guided_index = 0
        self._r10_tutorial_validation_ok = False
        self._r10_tutorial_export_done = False
        self._r102_last_rule_saved = False
        self._r102_rule_dialog = None
        self._r102_walkthrough_active = True
        self._r103_walkthrough_active = False
        self._r104_walkthrough_active = True
        self._r10_guided_window = None
        try:
            if getattr(self, "ui_mode", "modern") != "modern":
                self._apply_ui_mode("modern", initial=True)
            self.deiconify()
            self.lift()
            self.update_idletasks()
        except Exception:
            pass
        render(self)
        tick(self)

    def snapshot(self):
        if not getattr(self, "_r104_walkthrough_active", False) or getattr(self, "_r104_overlay", None) is None:
            return {"visible": False, "separate_window": False}
        sid = self._r10_guided_steps[self._r10_guided_index]
        return self._r104_overlay.snapshot(sid, self._r10_guided_index)

    def smoke(self, mode: str = "update"):
        start(self, mode)
        deadline = time.time() + 2.5
        snap = {}
        while time.time() < deadline:
            try:
                self.update()
            except Exception:
                break
            snap = snapshot(self)
            if snap.get("visible") and all(snap.get(k, {}).get("onscreen") for k in ("back", "next", "skip")):
                break
            time.sleep(0.02)
        return snap

    App._r104_definition = definition
    App._r104_resolve_target = lambda self, candidates, step_id="": resolve_target(self, candidates, step_id)
    App._r104_render_step = render
    App._r104_walkthrough_snapshot = snapshot
    App._r104_walkthrough_smoke = smoke
    App._r10_guided_show_step = render
    App._r10_guided_move = move
    App._r10_close_guided = close
    App._r10_skip_guided = skip
    App._r10_finish_guided = finish
    App.start_guided_tutorial = start
    # Keep compatibility with older CI/helpers that ask for the R10.3 snapshot method.
    App._r103_walkthrough_snapshot = snapshot
    App._r103_walkthrough_smoke = smoke
