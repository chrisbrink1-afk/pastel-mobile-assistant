from __future__ import annotations


R1041_REVISION = "R10.4.1"


def install_r1041_rule_gate_fix(core, edition: str | None = None, licence_info=None, revision: str = R1041_REVISION) -> None:
    """Make the first Saved Rule tutorial gate trust the Saved Rules store.

    R10.2/R10.3/R10.4 already record the number of rules present when the
    RuleDialog opens, but the close handler only trusts ``dlg.result``.  In the
    real save path the rule can be committed while that flag is still false,
    leaving the walkthrough's Next button disabled forever.

    R10.4.1 deliberately changes only this tracking layer.  When the real rule
    dialog closes, the persisted rule count is compared with the count captured
    when it opened.  A genuine new rule therefore unlocks the walkthrough even
    if the legacy result flag is false; cancelling without creating a rule does
    not unlock it.  Accounting, rule contents, licensing, profile storage and
    tutorial rendering are untouched.
    """
    RuleDialog = getattr(core, "RuleDialog", None)
    if RuleDialog is None or getattr(RuleDialog, "_r1041_rule_gate_fix_installed", False):
        return

    original_destroy = getattr(RuleDialog, "destroy", None)
    if original_destroy is None:
        raise RuntimeError("R10.4.1 rule gate fix: RuleDialog.destroy was not found")

    def fixed_destroy(dlg, *args, **kwargs):
        app = getattr(dlg, "app", None)
        before = getattr(app, "_r102_rule_count_before_dialog", None) if app is not None else None

        # Let the original Tk destruction run first.  This also lets the R10.2
        # <Destroy> binding run; that older binding may set the flag False from
        # dlg.result.  We then correct it from the persisted store below.
        result = original_destroy(dlg, *args, **kwargs)

        if app is not None and getattr(app, "_r102_walkthrough_active", False):
            saved = bool(getattr(app, "_r102_last_rule_saved", False))
            try:
                saved = saved or bool(getattr(dlg, "result", False))
            except Exception:
                pass

            after = None
            try:
                after = len(app.store.all_rules())
            except Exception:
                after = None

            if before is not None and after is not None and after > before:
                saved = True

            # Never overwrite an already-successful result with False.
            if saved:
                app._r102_last_rule_saved = True

        return result

    RuleDialog.destroy = fixed_destroy
    RuleDialog._r1041_rule_gate_fix_installed = True
