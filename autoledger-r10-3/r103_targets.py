from __future__ import annotations

INTERACTIVE_CLASSES = {
    "entry", "tentry", "combobox", "tcombobox", "spinbox", "tspinbox",
    "button", "tbutton", "checkbutton", "tcheckbutton", "radiobutton",
    "tradiobutton", "treeview", "listbox", "text",
}


def widget_exists(widget) -> bool:
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False


def widget_class(widget) -> str:
    try:
        return str(widget.winfo_class() or "").strip().casefold()
    except Exception:
        return ""


def widget_text(widget) -> str:
    try:
        return str(widget.cget("text") or "").strip()
    except Exception:
        return ""


def is_interactive(widget) -> bool:
    return widget_class(widget) in INTERACTIVE_CLASSES


def descendants(root):
    seen, queue, out = set(), [root], []
    while queue:
        parent = queue.pop(0)
        if parent is None or id(parent) in seen:
            continue
        seen.add(id(parent))
        try:
            children = list(parent.winfo_children())
        except Exception:
            children = []
        out.extend(children)
        queue.extend(children)
    return out


def walkthrough_roots(app):
    roots = []
    try:
        dlg = app._r102_rule_dialog_current()
    except Exception:
        dlg = None
    if widget_exists(dlg):
        roots.append(dlg)
    roots.append(app)
    return roots


def same_grid_row_interactive(label):
    try:
        info = label.grid_info()
        if not info:
            return None
        row = int(info.get("row", -999))
        parent = label.nametowidget(label.winfo_parent())
        choices = []
        for sibling in parent.winfo_children():
            if sibling is label or not is_interactive(sibling):
                continue
            sinfo = sibling.grid_info()
            if sinfo and int(sinfo.get("row", -998)) == row:
                choices.append((int(sinfo.get("column", 999)), sibling))
        if choices:
            choices.sort(key=lambda x: x[0])
            return choices[0][1]
    except Exception:
        pass
    return None


def nearby_interactive(label):
    try:
        parent = label.nametowidget(label.winfo_parent())
        label.update_idletasks()
        ly = label.winfo_rooty() + label.winfo_height() / 2.0
        lx = label.winfo_rootx()
        choices = []
        for sibling in parent.winfo_children():
            if sibling is label or not is_interactive(sibling):
                continue
            sibling.update_idletasks()
            sy = sibling.winfo_rooty() + sibling.winfo_height() / 2.0
            sx = sibling.winfo_rootx()
            choices.append((abs(sy - ly) * 5 + abs(sx - lx), sibling))
        if choices:
            choices.sort(key=lambda x: x[0])
            if choices[0][0] < 250:
                return choices[0][1]
    except Exception:
        pass
    return None


def special_target(app, step_id: str):
    if step_id == "review_transaction":
        for direction in ("PAYMENT", "RECEIPT"):
            try:
                tree = app.trees.get(direction)
                if not widget_exists(tree):
                    continue
                if direction == "PAYMENT" and getattr(app, "txns", None):
                    return tree
                if direction == "RECEIPT" and getattr(app, "receipts", None):
                    return tree
            except Exception:
                pass
    return None


def resolve_target(app, candidates, step_id: str = ""):
    direct = special_target(app, step_id)
    if direct is not None:
        return direct
    wanted = tuple(str(x).strip().casefold() for x in (candidates or ()) if str(x).strip())
    if not wanted:
        return None
    interactive, labels = [], []
    for root in walkthrough_roots(app):
        for widget in descendants(root):
            text = widget_text(widget).casefold()
            if text and any(w in text for w in wanted):
                (interactive if is_interactive(widget) else labels).append(widget)
    if interactive:
        return interactive[0]
    for label in labels:
        target = same_grid_row_interactive(label)
        if target is not None:
            return target
    for label in labels:
        target = nearby_interactive(label)
        if target is not None:
            return target
    return labels[0] if labels else None
