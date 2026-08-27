import sys
from autoledger_common import run_app, smoke_test
from pro_licensing import require_pro_licence

if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        smoke_test("PRO")
    else:
        licence = require_pro_licence()
        if licence is not None:
            run_app("PRO", licence)
