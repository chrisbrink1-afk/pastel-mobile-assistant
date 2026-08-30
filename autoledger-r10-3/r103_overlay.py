from __future__ import annotations

from r103_targets import widget_exists, widget_class, widget_text


class InlineOverlay:
    def __init__(self, core, app, on_back, on_next, on_skip):
        self.core, self.app = core, app
        self.on_back, self.on_next, self.on_skip = on_back, on_next, on_skip
        self.root = self.target = self.bubble = None
        self.highlights = []
        self.step_var = self.title_var = self.body_var = self.gate_var = None
        self.back = self.next = self.skip = self.gate_label = None

    def destroy(self):
        for w in list(self.highlights):
            try: w.destroy()
            except Exception: pass
        self.highlights = []
        if self.bubble is not None:
            try: self.bubble.destroy()
            except Exception: pass
        self.root = self.target = self.bubble = None

    def _build(self, root):
        tk, ttk = self.core.tk, self.core.ttk
        self.root = root
        self.bubble = tk.Frame(root, bg="#fffdf5", bd=0, highlightthickness=2, highlightbackground="#f59e0b")
        head = tk.Frame(self.bubble, bg="#0f2744", padx=10, pady=7); head.pack(fill="x")
        self.step_var, self.title_var, self.body_var, self.gate_var = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
        tk.Label(head, textvariable=self.step_var, bg="#0f2744", fg="#9dd8cb", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(head, textvariable=self.title_var, bg="#0f2744", fg="#fff", font=("Segoe UI", 11, "bold"), wraplength=350, justify="left").pack(anchor="w", pady=(2,0))
        tk.Message(self.bubble, textvariable=self.body_var, bg="#fffdf5", fg="#334155", font=("Segoe UI", 9), width=350, justify="left", padx=10, pady=8).pack(fill="x")
        self.gate_label = tk.Label(self.bubble, textvariable=self.gate_var, bg="#fff7ed", fg="#9a3412", font=("Segoe UI", 8, "bold"), justify="left", anchor="w", wraplength=350, padx=9, pady=5)
        self.gate_label.pack(fill="x", padx=8, pady=(0,5))
        foot = tk.Frame(self.bubble, bg="#fffdf5", padx=8, pady=7); foot.pack(fill="x")
        self.skip = ttk.Button(foot, text="Skip Tutorial", command=self.on_skip, style="Modern.TButton"); self.skip.pack(side="left")
        self.next = ttk.Button(foot, text="Next", command=self.on_next, style="Accent.TButton"); self.next.pack(side="right")
        self.back = ttk.Button(foot, text="Back", command=self.on_back, style="Modern.TButton"); self.back.pack(side="right", padx=(0,6))

    def ensure_root(self, root):
        if root is None or not widget_exists(root):
            root = self.app
        if self.root is not root or not widget_exists(self.bubble):
            self.destroy(); self._build(root)
        return root

    def _box(self, target):
        if target is None or not widget_exists(target):
            return None
        try:
            target.update_idletasks(); self.root.update_idletasks()
            return (int(target.winfo_rootx()-self.root.winfo_rootx()), int(target.winfo_rooty()-self.root.winfo_rooty()), max(1,int(target.winfo_width())), max(1,int(target.winfo_height())))
        except Exception:
            return None

    def _highlight(self):
        for w in list(self.highlights):
            try: w.destroy()
            except Exception: pass
        self.highlights = []
        box = self._box(self.target)
        if box is None: return
        x,y,w,h = box; p,t = 4,3; tk = self.core.tk
        specs = [(x-p-t,y-p,t,h+2*p),(x+w+p,y-p,t,h+2*p),(x-p-t,y-p-t,w+2*p+2*t,t),(x-p-t,y+h+p,w+2*p+2*t,t)]
        for sx,sy,sw,sh in specs:
            f=tk.Frame(self.root,bg="#f59e0b",bd=0,highlightthickness=0); f.place(x=sx,y=sy,width=sw,height=sh); f.lift(); self.highlights.append(f)

    def position(self):
        if not widget_exists(self.bubble) or not widget_exists(self.root): return
        self._highlight()
        try:
            self.root.update_idletasks(); self.bubble.update_idletasks()
            rw,rh=max(1,self.root.winfo_width()),max(1,self.root.winfo_height())
            bw=min(390,max(320,self.bubble.winfo_reqwidth())); bh=min(max(230,self.bubble.winfo_reqheight()),max(240,rh-24)); m=12
            box=self._box(self.target)
            if box is None: x,y=max(m,rw-bw-m),(50 if rh>bh+70 else m)
            else:
                tx,ty,tw,th=box; candidates=[(tx+tw+18,ty-20),(tx-bw-18,ty-20),(tx,ty+th+18),(tx,ty-bh-18)]; x=y=m
                for ox,oy in candidates:
                    cx=max(m,min(int(ox),max(m,rw-bw-m))); cy=max(m,min(int(oy),max(m,rh-bh-m)))
                    if not (cx<tx+tw+8 and cx+bw>tx-8 and cy<ty+th+8 and cy+bh>ty-8): x,y=cx,cy; break
            self.bubble.place(x=x,y=y,width=bw); self.bubble.lift()
        except Exception:
            try: self.bubble.place(relx=1.0,x=-12,y=50,anchor="ne",width=370); self.bubble.lift()
            except Exception: pass

    def render(self, step, target, index, total, complete):
        self.target = target
        try: root = target.winfo_toplevel() if target is not None else self.app
        except Exception: root = self.app
        self.ensure_root(root)
        self.target = target
        self.step_var.set(f"Step {index+1} of {total}"); self.title_var.set(step["title"]); self.body_var.set(step["body"])
        self.back.configure(state="normal" if index>0 else "disabled"); self.next.configure(text="Finish" if index==total-1 else "Next")
        self.update_gate(complete); self.position()

    def update_gate(self, complete):
        if not widget_exists(self.bubble): return
        self.next.configure(state="normal" if complete else "disabled")
        self.gate_var.set("DONE — click Next to continue." if complete else "DO THIS NOW — complete the highlighted action before continuing.")
        self.gate_label.configure(bg="#ecfdf5" if complete else "#fff7ed", fg="#166534" if complete else "#9a3412")

    def button_info(self, btn):
        try:
            self.root.update_idletasks(); btn.update_idletasks(); rx,ry=self.root.winfo_rootx(),self.root.winfo_rooty(); rw,rh=self.root.winfo_width(),self.root.winfo_height(); bx,by=btn.winfo_rootx(),btn.winfo_rooty(); bw,bh=btn.winfo_width(),btn.winfo_height()
            return {"text":str(btn.cget("text")),"mapped":bool(btn.winfo_ismapped()),"onscreen":bx>=rx and by>=ry and bx+bw<=rx+rw and by+bh<=ry+rh,"state":str(btn.cget("state"))}
        except Exception: return {"text":"","mapped":False,"onscreen":False,"state":""}

    def snapshot(self, step_id, index):
        if not widget_exists(self.bubble): return {"visible":False,"separate_window":False}
        return {"visible":bool(self.bubble.winfo_ismapped()),"separate_window":False,"tutorial_toplevel":getattr(self.app,"_r10_guided_window",None) is not None,"step_id":step_id,"index":int(index),"title":self.title_var.get().strip(),"body":self.body_var.get().strip(),"target_class":widget_class(self.target) if self.target else "","target_text":widget_text(self.target) if self.target else "","highlight_parts":sum(1 for p in self.highlights if widget_exists(p) and p.winfo_ismapped()),"back":self.button_info(self.back),"next":self.button_info(self.next),"skip":self.button_info(self.skip)}
