from __future__ import annotations
import json, os, socket, urllib.error, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

from activation_crypto import decode_and_verify_activation, activation_expired, activation_refresh_due
from device_identity import current_device_identity
from license_crypto import decode_and_verify_key

APP_NAMESPACE = "AUTOLEDGER_V225_TEST_Pro"
ACTIVATION_URL = os.environ.get("AUTOLEDGER_ACTIVATION_URL", "https://api.autoledger.co.za").rstrip("/")
HTTP_TIMEOUT = 8

def app_data_dir() -> Path:
    root = os.environ.get("APPDATA")
    path = (Path(root) / APP_NAMESPACE) if root else (Path.home() / ".autoledger_v225_test_pro")
    path.mkdir(parents=True, exist_ok=True)
    return path

# PERMANENT compatibility: never rename or discard the existing R6 entitlement file.
def licence_store_path() -> Path:
    return app_data_dir() / "pro_licence_r6.json"

def activation_store_path() -> Path:
    return app_data_dir() / "pro_device_activation_r8.json"

def deactivated_marker_path() -> Path:
    return app_data_dir() / "pro_device_deactivated_r8.json"

def load_entitlement_record() -> tuple[str, dict] | None:
    try:
        data = json.loads(licence_store_path().read_text(encoding="utf-8"))
        key = str(data.get("key", "")).strip()
        payload = decode_and_verify_key(key)
        return key, payload
    except Exception:
        return None

def save_licence(key: str, payload: dict) -> None:
    path = licence_store_path(); tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "key": key.strip(), "payload": payload}, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def _load_activation_record() -> dict | None:
    try:
        data = json.loads(activation_store_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None

def _save_activation_record(token: str, payload: dict, device: dict) -> None:
    path = activation_store_path(); tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "version": 1,
        "token": token,
        "payload": payload,
        "device_id": device["device_id"],
        "device_name": device.get("device_name", ""),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def _post(path: str, body: dict) -> dict:
    if not ACTIVATION_URL:
        raise ConnectionError("AUTOLEDGER activation service URL is not configured.")
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        ACTIVATION_URL + path,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "AUTOLEDGER-Pro/2.2.5-R8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw or "{}")
            if not isinstance(result, dict):
                raise RuntimeError("The activation service returned an invalid response.")
            return result
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            message = detail.get("detail") or detail.get("message") or str(exc)
        except Exception:
            message = str(exc)
        err = RuntimeError(message)
        setattr(err, "http_status", exc.code)
        raise err
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise ConnectionError("AUTOLEDGER could not contact the licence activation service.") from exc

def _activation_payload_matches(payload: dict, entitlement: dict, device: dict) -> bool:
    return (
        payload.get("license_id") == entitlement.get("license_id")
        and payload.get("device_id") == device.get("device_id")
        and payload.get("product") == "AUTOLEDGER"
        and payload.get("edition") == "PRO"
    )

def _server_activate(key: str, entitlement: dict, device: dict) -> tuple[str, dict]:
    result = _post("/v1/activate", {
        "licence_key": key,
        "device": device,
        "app_version": "2.2.5 R8 UPDATE",
    })
    token = str(result.get("activation_token") or "")
    payload = decode_and_verify_activation(token)
    if not _activation_payload_matches(payload, entitlement, device):
        raise RuntimeError("The activation service returned a token for a different licence or PC.")
    _save_activation_record(token, payload, device)
    try:
        deactivated_marker_path().unlink(missing_ok=True)
    except Exception:
        pass
    return token, payload

def _server_validate(key: str, entitlement: dict, device: dict, token: str) -> tuple[str, dict]:
    result = _post("/v1/validate", {
        "licence_key": key,
        "activation_token": token,
        "device": device,
        "app_version": "2.2.5 R8 UPDATE",
    })
    new_token = str(result.get("activation_token") or token)
    payload = decode_and_verify_activation(new_token)
    if not _activation_payload_matches(payload, entitlement, device):
        raise RuntimeError("The licence validation response does not match this PC.")
    _save_activation_record(new_token, payload, device)
    return new_token, payload

def _same_deactivated_device(device: dict) -> bool:
    try:
        data = json.loads(deactivated_marker_path().read_text(encoding="utf-8"))
        return data.get("device_id") == device.get("device_id")
    except Exception:
        return False

def ensure_device_activation(key: str, entitlement: dict, *, allow_legacy_migration: bool) -> dict:
    device = current_device_identity()

    if _same_deactivated_device(device):
        raise RuntimeError(
            "This PC was deliberately deactivated for a licence transfer. "
            "Reactivate this PC only if the transfer was cancelled or the licence has not been activated elsewhere."
        )

    record = _load_activation_record()
    if record and record.get("token"):
        try:
            token = str(record["token"])
            payload = decode_and_verify_activation(token)
            if not _activation_payload_matches(payload, entitlement, device):
                raise ValueError("The saved activation belongs to a different PC.")
            if activation_expired(payload):
                _, payload = _server_validate(key, entitlement, device, token)
            elif activation_refresh_due(payload):
                try:
                    _, payload = _server_validate(key, entitlement, device, token)
                except ConnectionError:
                    # Signed activation remains valid during its approximately 60-day offline grace after the 30-day refresh point.
                    pass
            return {
                **entitlement,
                "_activation_status": "active",
                "_activation_valid_until": payload.get("valid_until"),
                "_device_id": device.get("device_id"),
                "_device_name": device.get("device_name"),
            }
        except ConnectionError:
            raise
        except Exception:
            pass

    try:
        _, payload = _server_activate(key, entitlement, device)
        return {
            **entitlement,
            "_activation_status": "active",
            "_activation_valid_until": payload.get("valid_until"),
            "_device_id": device.get("device_id"),
            "_device_name": device.get("device_name"),
        }
    except ConnectionError:
        if allow_legacy_migration:
            # Transitional protection for EXISTING R6 customers only. Fresh R8
            # activations do not receive this fallback.
            return {
                **entitlement,
                "_activation_status": "legacy-migration-pending",
                "_device_id": device.get("device_id"),
                "_device_name": device.get("device_name"),
            }
        raise

def require_pro_licence() -> dict | None:
    existing = load_entitlement_record()
    existing_valid_before_prompt = existing is not None

    if existing is None:
        root = tk.Tk(); root.withdraw()
        try:
            while True:
                key = simpledialog.askstring(
                    "Unlock AUTOLEDGER Pro",
                    "Paste your AUTOLEDGER Pro licence key below.\n\n"
                    "Your existing R6 licence remains valid for this update.\n"
                    "New activations are limited to one active PC per licence.",
                    parent=root,
                )
                if key is None:
                    return None
                try:
                    payload = decode_and_verify_key(key)
                    save_licence(key, payload)
                    existing = (key.strip(), payload)
                    break
                except Exception as exc:
                    messagebox.showerror("Licence key not accepted", str(exc), parent=root)
        finally:
            root.destroy()

    key, payload = existing
    try:
        result = ensure_device_activation(
            key, payload,
            allow_legacy_migration=existing_valid_before_prompt,
        )
    except Exception as exc:
        root = tk.Tk(); root.withdraw()
        try:
            if _same_deactivated_device(current_device_identity()):
                retry = messagebox.askyesno(
                    "AUTOLEDGER Pro licence transfer",
                    "This PC was previously deactivated for a licence transfer.\n\n"
                    "Reactivate this PC now? Only do this if the transfer was cancelled or the "
                    "licence is not active on another computer.",
                    parent=root,
                )
                if retry:
                    try:
                        deactivated_marker_path().unlink(missing_ok=True)
                        result = ensure_device_activation(key, payload, allow_legacy_migration=False)
                        return result
                    except Exception as retry_exc:
                        exc = retry_exc
            messagebox.showerror(
                "AUTOLEDGER Pro activation",
                f"{exc}\n\n"
                "If this licence is already active on another PC, deactivate/transfer it there "
                "or contact AUTOLEDGER support for an activation reset.",
                parent=root,
            )
        finally:
            root.destroy()
        return None

    if result.get("_activation_status") == "legacy-migration-pending":
        notice = app_data_dir() / "pro_r8_migration_notice.json"
        show = True
        try:
            old = json.loads(notice.read_text(encoding="utf-8"))
            last = date.fromisoformat(old.get("date", ""))
            show = (date.today() - last).days >= 7
        except Exception:
            pass
        if show:
            root = tk.Tk(); root.withdraw()
            try:
                messagebox.showwarning(
                    "AUTOLEDGER Pro licence update",
                    "Your existing Pro licence remains valid and AUTOLEDGER will continue to run.\n\n"
                    "The new single-PC activation service could not be contacted. AUTOLEDGER will "
                    "automatically migrate this licence when the service becomes available.",
                    parent=root,
                )
            finally:
                root.destroy()
            try:
                notice.write_text(json.dumps({"date": date.today().isoformat()}), encoding="utf-8")
            except Exception:
                pass
    return result

def deactivate_current_device(parent=None) -> bool:
    existing = load_entitlement_record()
    if not existing:
        messagebox.showerror("AUTOLEDGER Pro", "No valid Pro entitlement is stored on this PC.", parent=parent)
        return False
    key, entitlement = existing
    device = current_device_identity()
    record = _load_activation_record()
    token = str((record or {}).get("token") or "")

    if token:
        try:
            _post("/v1/deactivate", {
                "licence_key": key,
                "activation_token": token,
                "device": device,
            })
        except Exception as exc:
            messagebox.showerror(
                "Licence transfer",
                f"AUTOLEDGER could not deactivate this PC online:\n\n{exc}\n\n"
                "The licence has not been transferred.",
                parent=parent,
            )
            return False

    try:
        activation_store_path().unlink(missing_ok=True)
    except Exception:
        pass
    deactivated_marker_path().write_text(json.dumps({
        "device_id": device.get("device_id"),
        "device_name": device.get("device_name"),
        "date": datetime.now(timezone.utc).isoformat(),
    }, indent=2), encoding="utf-8")
    messagebox.showinfo(
        "Licence deactivated",
        "This PC has been deactivated for transfer.\n\n"
        "Install AUTOLEDGER Pro on the replacement PC and enter the SAME Pro licence key.\n\n"
        "No new licence purchase is required.",
        parent=parent,
    )
    return True

def reactivate_this_pc(parent=None) -> bool:
    try:
        deactivated_marker_path().unlink(missing_ok=True)
    except Exception:
        pass
    existing = load_entitlement_record()
    if not existing:
        return False
    key, payload = existing
    try:
        ensure_device_activation(key, payload, allow_legacy_migration=False)
        messagebox.showinfo("AUTOLEDGER Pro", "This PC has been reactivated.", parent=parent)
        return True
    except Exception as exc:
        messagebox.showerror("AUTOLEDGER Pro", str(exc), parent=parent)
        return False
