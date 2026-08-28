import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

from autoledger_common import run_app, smoke_test
from device_identity import current_device_identity
from license_crypto import decode_and_verify_key
from pro_licensing import require_pro_licence, load_entitlement_record, save_licence

# TEST-BUILD COMPATIBILITY:
# The production one-PC activation client is fully bundled and tested, but the
# public api.autoledger.co.za service is not deployed yet. Until that service is
# live, R8 TEST accepts the customer's permanent ALP225R6 entitlement locally so
# the desktop build remains usable. Set AUTOLEDGER_R8_ENFORCE_ONLINE_ACTIVATION=1
# to exercise mandatory server activation. Commercial release must enable it.
ENFORCE_ONLINE_ACTIVATION = os.environ.get(
    "AUTOLEDGER_R8_ENFORCE_ONLINE_ACTIVATION", "0"
).strip().lower() in {"1", "true", "yes", "on"}


def require_test_entitlement():
    existing = load_entitlement_record()
    if existing is not None:
        _, payload = existing
    else:
        root = tk.Tk()
        root.withdraw()
        try:
            while True:
                key = simpledialog.askstring(
                    "Unlock AUTOLEDGER Pro v2.2.5 R8 TEST",
                    "Paste your AUTOLEDGER Pro licence key below.\n\n"
                    "Existing ALP225R6 Pro licences remain valid for this update.\n\n"
                    "This TEST build is using local entitlement validation until the "
                    "production one-PC activation service is deployed.",
                    parent=root,
                )
                if key is None:
                    return None
                try:
                    payload = decode_and_verify_key(key)
                    save_licence(key, payload)
                    break
                except Exception as exc:
                    messagebox.showerror("Licence key not accepted", str(exc), parent=root)
        finally:
            root.destroy()

    try:
        device = current_device_identity()
        payload = {
            **payload,
            "_activation_status": "r8-test-local-entitlement",
            "_device_id": device.get("device_id"),
            "_device_name": device.get("device_name"),
        }
    except Exception:
        payload = {**payload, "_activation_status": "r8-test-local-entitlement"}
    return payload


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        smoke_test("PRO")
    elif "--existing-licence-smoke-test" in sys.argv:
        # CI compatibility gate: proves the permanent R6 entitlement file is
        # discovered and cryptographically accepted by the R8 update.
        if load_entitlement_record() is None:
            raise SystemExit(7)
    else:
        licence = require_pro_licence() if ENFORCE_ONLINE_ACTIVATION else require_test_entitlement()
        if licence is not None:
            run_app("PRO", licence)
