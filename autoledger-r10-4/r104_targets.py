from __future__ import annotations

INTERACTIVE_CLASSES = {
    "entry", "tentry", "combobox", "tcombobox", "spinbox", "tspinbox",
    "button", "tbutton", "checkbutton", "tcheckbutton", "radiobutton",
    "tradiobutton", "treeview", "listbox", "text",
}
INPUT_CLASSES = {"entry", "tentry", "combobox", "tcombobox", "spinbox", "tspinbox", "text"}
BUTTON_CLASSES = {"button", "tbutton", "checkbutton", "tcheckbutton", "radiobutton", "tradiobutton"}

FIELD_STEPS = {
    "cashbook_gl", "vat_tax_type", "vat_rate", "fiscal_month", "project_code",
    "rule_name", "rule_match", "rule_method", "rule_gl", "rule_vat", "rule_priority",
}
BUTTON_STEPS = {
    "profile", "save_settings", "load_csv", "rule_open", "rule_save", "rule_result",
    "select_export", "validate", "export",
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


def is_visible(widget) -> bool:
    if not widget_exists(widget):
        return False
    try:
        widget.update_idletasks()
        return bool(widget.winfo_ismapped()) and widget.winfo_width() > 1 and widget.winfo_height() > 1
    except Exception:
        return False


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


def _centre(widget):
    try:
        widget.update_idletasks()
        return (
            widget.winfo_rootx() + widget.winfo_width() / 2.0,
            widget.winfo_rooty() + widget.winfo_height() / 2.0,
        )
    except Exception:
        return (0.0, 0.0)


def same_grid_row_interactive(label, expected_classes=None):
    try:
        info = label.grid_info()
        if not info:
            return None
        row = int(info.get("row", -999))
        col = int(info.get("column", 0))
        parent = label.nametowidget(label.winfo_parent())
        choices = []
        for sibling in parent.winfo_children():
            if sibling is label or not is_interactive(sibling) or not is_visible(sibling):
                continue
            cls = widget_class(sibling)
            if expected_classes and cls not in expected_classes:
                continue
            sinfo = sibling.grid_info()
            if not sinfo or int(sinfo.get("row", -998)) != row:
                continue
            scol = int(sinfo.get("column", 999))
            # Prefer controls to the right of the label, then the nearest column.
            right_penalty = 0 if scol > col else 1000
            choices.append((right_penalty + abs(scol - col), sibling))
        if choices:
            choices.sort(key=lambda x: x[0])
            return choices[0][1]
    except Exception:
        pass
    return None


def nearby_interactive(label, expected_classes=None):
    try:
        parent = label.nametowidget(label.winfo_parent())
        lx, ly = _centre(label)
        choices = []
        for sibling in parent.winfo_children():
            if sibling is label or not is_interactive(sibling) or not is_visible(sibling):
                continue
            cls = widget_class(sibling)
            if expected_classes and cls not in expected_classes:
                continue
            sx, sy = _centre(sibling)
            # Strongly prefer same horizontal band and a control to the right.
            score = abs(sy - ly) * 7 + abs(sx - lx)
            if sx < lx:
                score += 180
            choices.append((score, sibling))
        if choices:
            choices.sort(key=lambda x: x[0])
            if choices[0][0] < 480:
                return choices[0][1]
    except Exception:
        pass
    return None


def expected_classes(step_id: str):
    if step_id in FIELD_STEPS:
        return INPUT_CLASSES | {"checkbutton", "tcheckbutton", "radiobutton", "tradiobutton"}
    if step_id in BUTTON_STEPS:
        return BUTTON_CLASSES
    if step_id == "review_transaction":
        return {"treeview"}
    if step_id == "rule_amount_optional":
        return {"checkbutton", "tcheckbutton"}
    return None


def special_target(app, step_id: str):
    if step_id == "review_transaction":
        for direction in ("PAYMENT", "RECEIPT"):
            try:
                tree = app.trees.get(direction)
                if not is_visible(tree):
                    continue
                if direction == "PAYMENT" and getattr(app, "txns", None):
                    return tree
                if direction == "RECEIPT" and getattr(app, "receipts", None):
                    return tree
            except Exception:
                pass
    return None


def _text_match_score(text: str, wanted: tuple[str, ...]) -> int | None:
    if not text:
        return None
    text = text.strip().casefold()
    scores = []
    for index, term in enumerate(wanted):
        if text == term:
            scores.append(index)
        elif text.startswith(term):
            scores.append(20 + index)
        elif term in text:
            scores.append(40 + index)
    return min(scores) if scores else None


def resolve_target(app, candidates, step_id: str = ""):
    direct = special_target(app, step_id)
    if direct is not None:
        return direct

    wanted = tuple(str(x).strip().casefold() for x in (candidates or ()) if str(x).strip())
    if not wanted:
        return None

    expected = expected_classes(step_id)
    direct_interactive = []
    labels = []
    roots = walkthrough_roots(app)

    for root_index, root in enumerate(roots):
        for order, widget in enumerate(descendants(root)):
            if not is_visible(widget):
                continue
            score = _text_match_score(widget_text(widget), wanted)
            if score is None:
                continue
            cls = widget_class(widget)
            if is_interactive(widget):
                class_penalty = 0 if (not expected or cls in expected) else 180
                direct_interactive.append((root_index * 1000 + class_penalty + score + min(order, 99) / 100.0, widget))
            else:
                labels.append((root_index * 1000 + score + min(order, 99) / 100.0, widget))

    if direct_interactive:
        direct_interactive.sort(key=lambda x: x[0])
        best_score, best = direct_interactive[0]
        # Do not let a semantically wrong interactive widget beat a label-associated field.
        if best_score % 1000 < 180:
            return best

    labels.sort(key=lambda x: x[0])
    for _, label in labels:
        target = same_grid_row_interactive(label, expected)
        if target is not None:
            return target
    for _, label in labels:
        target = nearby_interactive(label, expected)
        if target is not None:
            return target

    if direct_interactive:
        direct_interactive.sort(key=lambda x: x[0])
        return direct_interactive[0][1]

    # An action step should never deliberately highlight only a label. Returning None
    # is safer than pointing the user at the wrong non-interactive object.
    if expected:
        return None
    return labels[0][1] if labels else None
