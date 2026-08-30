from __future__ import annotations

from types import SimpleNamespace

from r1041_rule_gate_fix import install_r1041_rule_gate_fix


class FakeStore:
    def __init__(self, count=0):
        self.rules = [object() for _ in range(count)]

    def all_rules(self):
        return list(self.rules)


class FakeRuleDialog:
    def __init__(self, app, *, create_rule=False, result=False):
        self.app = app
        self.create_rule = create_rule
        self.result = result

    def destroy(self):
        # Reproduce the inherited R10.2 close tracking: it trusts result and can
        # incorrectly write False even after the store has already been updated.
        self.app._r102_last_rule_saved = bool(self.result)
        return "destroyed"

    def save_and_close(self):
        if self.create_rule:
            self.app.store.rules.append(object())
        return self.destroy()


class FakeCore:
    RuleDialog = FakeRuleDialog


def make_app(count=0):
    return SimpleNamespace(
        store=FakeStore(count),
        _r102_walkthrough_active=True,
        _r102_last_rule_saved=False,
        _r102_rule_count_before_dialog=count,
    )


def main() -> None:
    install_r1041_rule_gate_fix(FakeCore)

    # Exact bug: database count increases although RuleDialog.result remains False.
    app = make_app(0)
    dlg = FakeRuleDialog(app, create_rule=True, result=False)
    assert dlg.save_and_close() == "destroyed"
    assert len(app.store.all_rules()) == 1
    assert app._r102_last_rule_saved is True, "Persisted first rule did not unlock tutorial gate"

    # Cancel/no persistence + false result must remain locked.
    app = make_app(2)
    dlg = FakeRuleDialog(app, create_rule=False, result=False)
    dlg.save_and_close()
    assert app._r102_last_rule_saved is False, "Gate unlocked without a successful save"

    # Preserve the legacy success path.
    app = make_app(2)
    dlg = FakeRuleDialog(app, create_rule=False, result=True)
    dlg.save_and_close()
    assert app._r102_last_rule_saved is True, "Legacy successful result no longer unlocks gate"

    # The fix must not mutate state outside an active walkthrough.
    app = make_app(0)
    app._r102_walkthrough_active = False
    dlg = FakeRuleDialog(app, create_rule=True, result=False)
    dlg.save_and_close()
    assert len(app.store.all_rules()) == 1
    assert app._r102_last_rule_saved is False, "Fix changed tutorial state while walkthrough inactive"

    print("R10.4.1 first Saved Rule gate regression tests passed")


if __name__ == "__main__":
    main()
