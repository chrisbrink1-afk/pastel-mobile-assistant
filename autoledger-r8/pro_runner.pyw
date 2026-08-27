import sys
from autoledger_common import run_app, smoke_test
from pro_licensing import require_pro_licence, load_entitlement_record

if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        # UI/runtime smoke test deliberately bypasses online activation.
        smoke_test("PRO")
    elif "--existing-licence-smoke-test" in sys.argv:
        # CI compatibility gate: proves the permanent R6 entitlement file is
        # discovered and cryptographically accepted by the R8 update.
        if load_entitlement_record() is None:
            raise SystemExit(7)
    else:
        licence = require_pro_licence()
        if licence is not None:
            run_app("PRO", licence)
