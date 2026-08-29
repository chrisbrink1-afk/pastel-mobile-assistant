from __future__ import annotations

import time


def install_tutorial_render_fix(core, edition: str, licence_info=None, revision: str = "R10.1") -> None:
    """Harden R10 guided-tutorial startup/rendering for R10.1.

    R10 could auto-open the tutorial while App.__init__ was still unwinding. On a
    real updated installation this could leave a Toplevel visible before its
    instructional widgets had rendered, producing an apparently blank tutorial.

    R10.1 deliberately defers automatic launch until Tk has returned to the event
    loop, then verifies/re-renders visible title/body content. The public method
    is also wrapped so manually starting the tutorial gets the same protection.
    """

    App = core.App
    original_start = getattr(App, "start_guided_tutorial", None)
    if original_start is None:
        raise RuntimeError("R10.1 render fix requires the R10 guided tutorial")

    def _render_snapshot(self) -> dict:
        title = ""
        body = ""
        step = ""
        gate = ""
        visible = False
        width = 0
        height = 0
        try:
            title = str(self._r10_guided_title_var.get() or "").strip()
        except Exception:
            pass
        try:
            body = str(self._r10_guided_body.get("1.0", "end-1c") or "").strip()
        except Exception:
            pass
        try:
            step = str(self._r10_guided_step_var.get() or "").strip()
        except Exception:
            pass
        try:
            gate = str(self._r10_guided_gate_var.get() or "").strip()
            # Keep diagnostic snapshots printable on legacy Windows console
            # encodings. The actual tutorial UI continues to display the checkmark.
            gate = gate.replace("✓", "OK")
        except Exception:
            pass
        win = getattr(self, "_r10_guided_window", None)
        if win is not None:
            try:
                win.update_idletasks()
                width = int(win.winfo_width())
                height = int(win.winfo_height())
                visible = bool(win.winfo_exists()) and width > 100 and height > 100
            except Exception:
                pass
        return {
            "title": title,
            "body": body,
            "step": step,
            "gate": gate,
            "visible": visible,
            "width": width,
            "height": height,
        }

    def _ensure_rendered(self) -> bool:
        win = getattr(self, "_r10_guided_window", None)
        if win is None:
            return False
        try:
            if not win.winfo_exists():
                return False
        except Exception:
            return False

        try:
            win.deiconify()
            win.update_idletasks()
        except Exception:
            pass

        snap = _render_snapshot(self)
        if not snap["title"] or not snap["body"]:
            try:
                self._r10_guided_show_step()
                win.update_idletasks()
            except Exception:
                pass
            snap = _render_snapshot(self)

        try:
            win.lift()
            win.attributes("-topmost", True)
            win.update_idletasks()
        except Exception:
            pass

        snap = _render_snapshot(self)
        self._r101_last_render_snapshot = snap
        return bool(snap["visible"] and snap["title"] and snap["body"] and snap["step"])

    def fixed_start_guided_tutorial(self, mode: str | None = None):
        result = original_start(self, mode)
        _ensure_rendered(self)
        try:
            self.after_idle(lambda: _ensure_rendered(self))
            self.after(120, lambda: _ensure_rendered(self))
            self.after(350, lambda: _ensure_rendered(self))
        except Exception:
            pass
        return result

    def fixed_maybe_start_tutorial(self) -> None:
        if getattr(self, "_r101_auto_tutorial_scheduled", False):
            return
        try:
            should_start = bool(self._r10_should_auto_start_guided())
        except Exception:
            should_start = False
        if not should_start:
            return
        try:
            mode = self._r10_classify_install_mode()
        except Exception:
            mode = "clean"
        self._r101_auto_tutorial_scheduled = True

        def launch():
            self._r101_auto_tutorial_scheduled = False
            try:
                self.start_guided_tutorial(mode)
            except Exception as exc:
                self._r101_tutorial_launch_error = repr(exc)
                try:
                    self._r10_close_guided()
                except Exception:
                    pass
                try:
                    core.messagebox.showerror(
                        "AUTOLEDGER Guided Tutorial",
                        "The Guided Tutorial could not be displayed correctly.\n\n"
                        "Please close AUTOLEDGER and open it again. If the problem continues, contact AUTOLEDGER support.",
                        parent=self,
                    )
                except Exception:
                    pass

        try:
            self.after(450, launch)
        except Exception:
            launch()

    def _tutorial_render_smoke(self, mode: str = "update") -> dict:
        """Used by Windows CI and installed-EXE smoke tests."""
        self.start_guided_tutorial(mode)
        deadline = time.time() + 1.5
        while time.time() < deadline:
            try:
                self.update()
            except Exception:
                break
            snap = _render_snapshot(self)
            if snap["visible"] and snap["title"] and snap["body"] and snap["step"]:
                self._r101_last_render_snapshot = snap
                return snap
            time.sleep(0.03)
        snap = _render_snapshot(self)
        self._r101_last_render_snapshot = snap
        return snap

    App._r101_tutorial_render_snapshot = _render_snapshot
    App._r101_ensure_tutorial_rendered = _ensure_rendered
    App._r101_tutorial_render_smoke = _tutorial_render_smoke
    App.start_guided_tutorial = fixed_start_guided_tutorial
    App._maybe_start_tutorial = fixed_maybe_start_tutorial
