from __future__ import annotations
import json, os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog
from license_crypto import decode_and_verify_key

APP_NAMESPACE = "AUTOLEDGER_V225_TEST_Pro"

def app_data_dir() -> Path:
    root = os.environ.get("APPDATA")
    path = (Path(root) / APP_NAMESPACE) if root else (Path.home() / ".autoledger_v225_test_pro")
    path.mkdir(parents=True, exist_ok=True)
    return path

def licence_store_path() -> Path:
    return app_data_dir() / "pro_licence_r6.json"

def load_pro_licence() -> dict | None:
    try:
        data = json.loads(licence_store_path().read_text(encoding="utf-8"))
        return decode_and_verify_key(str(data.get("key", "")))
    except Exception:
        return None

def save_licence(key: str, payload: dict) -> None:
    path = licence_store_path(); tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "key": key.strip(), "payload": payload}, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def require_pro_licence() -> dict | None:
    payload = load_pro_licence()
    if payload is not None: return payload
    root = tk.Tk(); root.withdraw()
    try:
        while True:
            key = simpledialog.askstring(
                "Unlock AUTOLEDGER Pro v2.2.5 R6",
                "Paste your AUTOLEDGER Pro R6 licence key below.\n\n"
                "Validation is performed locally on this PC; no activation data is sent to an AUTOLEDGER server.",
                parent=root,
            )
            if key is None: return None
            try:
                payload = decode_and_verify_key(key)
                save_licence(key, payload)
                messagebox.showinfo("AUTOLEDGER Pro", f"Licence accepted.\n\nLicensed to: {payload.get('customer', 'Licensed user')}", parent=root)
                return payload
            except Exception as exc:
                messagebox.showerror("Licence key not accepted", str(exc), parent=root)
    finally:
        root.destroy()
