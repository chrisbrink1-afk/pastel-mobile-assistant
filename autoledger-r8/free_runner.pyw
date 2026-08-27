import sys
from autoledger_common import run_app, smoke_test

if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        smoke_test("FREE")
    else:
        run_app("FREE")
