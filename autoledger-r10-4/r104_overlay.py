from __future__ import annotations

from r104_targets import widget_exists, widget_class, widget_text


class NonObscuringOverlay:
    def __init__(self, core, app, on_back, on_next, on_skip):
        self.core, self.app = core, app
        self.on_back, self.on_next, self.on_skip = on_back, on_next, on_skip
        self.root = self.target = self.bubble = self.body = None
        self.highlights = []
        self.arrow = None
        self.arrow_job = None
        self.arrow_phase = 0
        self.arrow_side = "left"
        self.step_var = self.title_var = self.body_var = self.gate_var = None
        self.back = self.next = self.skip = self.gate_label = None
        self.last_bubble_rect = None

    def _cancel_arrow(self):
        if self.arrow_job:
            try:
                self.root.after_cancel(self.arrow_job)
            except Exception:
                pass
        self.arrow_job = None
        if self.arrow is not None:
            try:
                self.arrow.destroy()
            except Exception:
                pass
        self.arrow = None

    def destroy(self):
        self._cancel_arrow()
        for w in list(self.highlights):
            try:
                w.destroy()
            except Exception:
                pass
        self.highlights = []
        if self.bubble is not None:
            try:
                self.bubble.destroy()
            except Exception:
                pass
        self.root = self.target = self.bubble = self.body = None
        self.last_bubble_rect = None

    def _build(self, root):
        tk, ttk = self.core.tk, self.core.ttk
        self.root = root
        self.bubble = tk.Frame(root, bg="#fffdf5", bd=0, highlightthickness=2, highlightbackground="#f59e0b")
        head = tk.Frame(self.bubble, bg="#0f2744", padx=10, pady=7)
        head.pack(fill="x")
        self.step_var, self.title_var, self.body_var, self.gate_var = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
        tk.Label(head, textvariable=self.step_var, bg="#0f2744", fg="#9dd8cb", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(head, textvariable=self.title_var, bg="#0f2744", fg="#fff", font=("Segoe UI", 11, "bold"), wraplength=350, justify="left").pack(anchor="w", pady=(2, 0))
        self.body = tk.Message(self.bubble, textvariable=self.body_var, bg="#fffdf5", fg="#334155", font=("Segoe UI", 9), width=350, justify="left", padx=10, pady=8)
        self.body.pack(fill="x")
        self.gate_label = tk.Label(self.bubble, textvariable=self.gate_var, bg="#fff7ed", fg="#9a3412", font=("Segoe UI", 8, "bold"), justify="left", anchor="w", wraplength=350, padx=9, pady=5)
        self.gate_label.pack(fill="x", padx=8, pady=(0, 5))
        foot = tk.Frame(self.bubble, bg="#fffdf5", padx=8, pady=7)
        foot.pack(fill="x")
        self.skip = ttk.Button(foot, text="Skip Tutorial", command=self.on_skip, style="Modern.TButton")
        self.skip.pack(side="left")
        self.next = ttk.Button(foot, text="Next", command=self.on_next, style="Accent.TButton")
        self.next.pack(side="right")
        self.back = ttk.Button(foot, text="Back", command=self.on_back, style="Modern.TButton")
        self.back.pack(side="right", padx=(0, 6))

    def ensure_root(self, root):
        if root is None or not widget_exists(root):
            root = self.app
        if self.root is not root or not widget_exists(self.bubble):
            self.destroy()
            self._build(root)
        return root

    def _box(self, target):
        if target is None or not widget_exists(target):
            return None
        try:
            target.update_idletasks()
            self.root.update_idletasks()
            return (
                int(target.winfo_rootx() - self.root.winfo_rootx()),
                int(target.winfo_rooty() - self.root.winfo_rooty()),
                max(1, int(target.winfo_width())),
                max(1, int(target.winfo_height())),
            )
        except Exception:
            return None

    @staticmethod
    def _rects_overlap(a, b, pad=0):
        if a is None or b is None:
            return False
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return ax < bx + bw + pad and ax + aw > bx - pad and ay < by + bh + pad and ay + ah > by - pad

    def _highlight(self):
        for w in list(self.highlights):
            try:
                w.destroy()
            except Exception:
                pass
        self.highlights = []
        box = self._box(self.target)
        if box is None:
            return
        x, y, w, h = box
        p, t = 5, 3
        tk = self.core.tk
        specs = [
            (x - p - t, y - p, t, h + 2 * p),
            (x + w + p, y - p, t, h + 2 * p),
            (x - p - t, y - p - t, w + 2 * p + 2 * t, t),
            (x - p - t, y + h + p, w + 2 * p + 2 * t, t),
        ]
        for sx, sy, sw, sh in specs:
            f = tk.Frame(self.root, bg="#f59e0b", bd=0, highlightthickness=0)
            f.place(x=sx, y=sy, width=sw, height=sh)
            f.lift()
            self.highlights.append(f)

    def _choose_bubble_position(self, box, rw, rh, bw, bh):
        margin, gap = 12, 42
        if box is None:
            return max(margin, rw - bw - margin), margin, "none"

        tx, ty, tw, th = box
        target_guard = (tx - 14, ty - 14, tw + 28, th + 28)
        candidates = [
            (tx + tw + gap, ty + th // 2 - bh // 2, "right"),
            (tx - bw - gap, ty + th // 2 - bh // 2, "left"),
            (tx + tw // 2 - bw // 2, ty + th + gap, "below"),
            (tx + tw // 2 - bw // 2, ty - bh - gap, "above"),
        ]

        # First choice: fully on-screen and definitely clear of the target.
        for x, y, side in candidates:
            rect = (int(x), int(y), bw, bh)
            if x >= margin and y >= margin and x + bw <= rw - margin and y + bh <= rh - margin and not self._rects_overlap(rect, target_guard):
                return int(x), int(y), side

        # Second choice: clamp each candidate to the window and choose the one with no target overlap and the greatest centre distance.
        usable = []
        tcx, tcy = tx + tw / 2.0, ty + th / 2.0
        for x, y, side in candidates:
            cx = max(margin, min(int(x), max(margin, rw - bw - margin)))
            cy = max(margin, min(int(y), max(margin, rh - bh - margin)))
            rect = (cx, cy, bw, bh)
            if self._rects_overlap(rect, target_guard):
                continue
            bcx, bcy = cx + bw / 2.0, cy + bh / 2.0
            dist = (bcx - tcx) ** 2 + (bcy - tcy) ** 2
            usable.append((dist, cx, cy, side))
        if usable:
            usable.sort(reverse=True)
            _, x, y, side = usable[0]
            return x, y, side

        # Final safety: try the four corners. If none is clear, hide the bubble rather than cover the required control.
        corners = [
            (margin, margin, "corner"),
            (max(margin, rw - bw - margin), margin, "corner"),
            (margin, max(margin, rh - bh - margin), "corner"),
            (max(margin, rw - bw - margin), max(margin, rh - bh - margin), "corner"),
        ]
        for x, y, side in corners:
            if not self._rects_overlap((x, y, bw, bh), target_guard):
                return x, y, side
        return None

    def _arrow_base(self):
        box = self._box(self.target)
        if box is None or not widget_exists(self.root):
            return None
        try:
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
        except Exception:
            return None
        tx, ty, tw, th = box
        choices = []
        # side, arrow glyph, x, y, motion vector. Coordinates remain outside the target.
        choices.append((tx - 34, "left", "➜", tx - 32, ty + th // 2 - 14, 1, 0))
        choices.append((rw - (tx + tw) - 34, "right", "⬅", tx + tw + 8, ty + th // 2 - 14, -1, 0))
        choices.append((ty - 34, "above", "⬇", tx + tw // 2 - 12, ty - 32, 0, 1))
        choices.append((rh - (ty + th) - 34, "below", "⬆", tx + tw // 2 - 12, ty + th + 8, 0, -1))
        choices = [c for c in choices if c[0] >= 0]
        if not choices:
            return None
        choices.sort(reverse=True, key=lambda c: c[0])
        _, side, glyph, x, y, dx, dy = choices[0]
        x = max(2, min(int(x), max(2, rw - 30)))
        y = max(2, min(int(y), max(2, rh - 30)))
        return side, glyph, x, y, dx, dy

    def _animate_arrow(self):
        self.arrow_job = None
        if not widget_exists(self.root) or not widget_exists(self.target):
            return
        base = self._arrow_base()
        if base is None:
            if self.arrow is not None:
                try:
                    self.arrow.place_forget()
                except Exception:
                    pass
            return
        side, glyph, x, y, dx, dy = base
        self.arrow_side = side
        if self.arrow is None or not widget_exists(self.arrow):
            self.arrow = self.core.tk.Label(self.root, text=glyph, bg="#fff3cd", fg="#c2410c", bd=1, relief="solid", font=("Segoe UI Symbol", 17, "bold"), padx=2, pady=0)
        else:
            try:
                self.arrow.configure(text=glyph)
            except Exception:
                pass
        phases = (0, 2, 4, 7, 4, 2)
        offset = phases[self.arrow_phase % len(phases)]
        self.arrow_phase += 1
        self.arrow.place(x=x + dx * offset, y=y + dy * offset, width=28, height=28)
        self.arrow.lift()
        try:
            self.arrow_job = self.root.after(150, self._animate_arrow)
        except Exception:
            self.arrow_job = None

    def _ensure_arrow(self):
        if self.target is None or not widget_exists(self.target):
            self._cancel_arrow()
            return
        if self.arrow_job is None:
            self._animate_arrow()

    def position(self):
        if not widget_exists(self.bubble) or not widget_exists(self.root):
            return
        self._highlight()
        try:
            self.root.update_idletasks()
            self.bubble.update_idletasks()
            rw, rh = max(1, self.root.winfo_width()), max(1, self.root.winfo_height())
            bw = min(390, max(285, min(self.bubble.winfo_reqwidth(), rw - 24)))
            if self.body is not None:
                self.body.configure(width=max(235, bw - 30))
                self.gate_label.configure(wraplength=max(235, bw - 30))
            self.bubble.update_idletasks()
            bh = min(max(210, self.bubble.winfo_reqheight()), max(210, rh - 24))
            box = self._box(self.target)
            chosen = self._choose_bubble_position(box, rw, rh, bw, bh)
            if chosen is None:
                self.bubble.place_forget()
                self.last_bubble_rect = None
            else:
                x, y, _ = chosen
                self.bubble.place(x=x, y=y, width=bw)
                self.bubble.lift()
                self.last_bubble_rect = (x, y, bw, bh)
            self._ensure_arrow()
        except Exception:
            # Safety fallback: never deliberately place over a known target.
            try:
                box = self._box(self.target)
                if box is None:
                    self.bubble.place(relx=1.0, x=-12, y=12, anchor="ne", width=350)
                    self.bubble.lift()
                else:
                    self.bubble.place_forget()
            except Exception:
                pass

    def render(self, step, target, index, total, complete):
        self.target = target
        try:
            root = target.winfo_toplevel() if target is not None else self.app
        except Exception:
            root = self.app
        self.ensure_root(root)
        self.target = target
        self.step_var.set(f"Step {index + 1} of {total}")
        self.title_var.set(step["title"])
        self.body_var.set(step["body"])
        self.back.configure(state="normal" if index > 0 else "disabled")
        self.next.configure(text="Finish" if index == total - 1 else "Next")
        self.update_gate(complete)
        self.position()

    def update_gate(self, complete):
        if not widget_exists(self.bubble):
            return
        self.next.configure(state="normal" if complete else "disabled")
        self.gate_var.set("DONE — click Next to continue." if complete else "DO THIS NOW — complete the highlighted action before continuing.")
        self.gate_label.configure(bg="#ecfdf5" if complete else "#fff7ed", fg="#166534" if complete else "#9a3412")

    def button_info(self, btn):
        try:
            self.root.update_idletasks()
            btn.update_idletasks()
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            bx, by = btn.winfo_rootx(), btn.winfo_rooty()
            bw, bh = btn.winfo_width(), btn.winfo_height()
            return {
                "text": str(btn.cget("text")),
                "mapped": bool(btn.winfo_ismapped()),
                "onscreen": bx >= rx and by >= ry and bx + bw <= rx + rw and by + bh <= ry + rh,
                "state": str(btn.cget("state")),
            }
        except Exception:
            return {"text": "", "mapped": False, "onscreen": False, "state": ""}

    def snapshot(self, step_id, index):
        if not widget_exists(self.bubble):
            return {"visible": False, "separate_window": False}
        target_box = self._box(self.target)
        bubble_overlap = self._rects_overlap(self.last_bubble_rect, target_box, pad=8) if self.last_bubble_rect and target_box else False
        arrow_mapped = False
        try:
            arrow_mapped = bool(self.arrow is not None and self.arrow.winfo_ismapped())
        except Exception:
            pass
        return {
            "visible": bool(self.bubble.winfo_ismapped()),
            "separate_window": False,
            "tutorial_toplevel": getattr(self.app, "_r10_guided_window", None) is not None,
            "step_id": step_id,
            "index": int(index),
            "title": self.title_var.get().strip(),
            "body": self.body_var.get().strip(),
            "target_class": widget_class(self.target) if self.target else "",
            "target_text": widget_text(self.target) if self.target else "",
            "highlight_parts": sum(1 for p in self.highlights if widget_exists(p) and p.winfo_ismapped()),
            "bubble_overlaps_target": bool(bubble_overlap),
            "arrow_mapped": arrow_mapped,
            "arrow_side": self.arrow_side,
            "back": self.button_info(self.back),
            "next": self.button_info(self.next),
            "skip": self.button_info(self.skip),
        }
