from __future__ import annotations
import hashlib, json, platform, socket, subprocess, winreg
from typing import Dict

_NAMESPACE = "AUTOLEDGER-DEVICE-V1"

def _run_powershell(expr: str) -> str:
    try:
        cp = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", expr],
            capture_output=True, text=True, timeout=8, creationflags=0x08000000
        )
        if cp.returncode == 0:
            text = (cp.stdout or "").strip()
            return text.splitlines()[0].strip() if text else ""
    except Exception:
        pass
    return ""

def _machine_guid() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as k:
            value, _ = winreg.QueryValueEx(k, "MachineGuid")
            return str(value or "").strip()
    except Exception:
        return ""

def _normalise(value: str) -> str:
    value = (value or "").strip().upper()
    bad = {"", "NONE", "UNKNOWN", "DEFAULT STRING", "TO BE FILLED BY O.E.M.",
           "SYSTEM SERIAL NUMBER", "00000000-0000-0000-0000-000000000000"}
    return "" if value in bad else value

def _component_hash(label: str, value: str) -> str:
    value = _normalise(value)
    if not value:
        return ""
    return hashlib.sha256(f"{_NAMESPACE}|{label}|{value}".encode("utf-8")).hexdigest()

def current_device_identity() -> Dict[str, object]:
    system_uuid = _run_powershell("(Get-CimInstance Win32_ComputerSystemProduct -ErrorAction SilentlyContinue).UUID")
    baseboard = _run_powershell("(Get-CimInstance Win32_BaseBoard -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty SerialNumber)")
    bios = _run_powershell("(Get-CimInstance Win32_BIOS -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty SerialNumber)")
    machine_guid = _machine_guid()

    components = {
        "system_uuid": _component_hash("system_uuid", system_uuid),
        "baseboard": _component_hash("baseboard", baseboard),
        "bios": _component_hash("bios", bios),
    }
    fallback = _component_hash("machine_guid", machine_guid)

    stable = [v for v in components.values() if v]
    if stable:
        material = "|".join(sorted(stable))
    elif fallback:
        material = fallback
    else:
        material = hashlib.sha256(f"{socket.gethostname()}|{platform.machine()}".encode()).hexdigest()

    device_id = hashlib.sha256(f"{_NAMESPACE}|device|{material}".encode()).hexdigest()
    return {
        "device_id": device_id,
        "components": components,
        "fallback_hash": fallback,
        "device_name": socket.gethostname(),
        "os": platform.platform(),
        "architecture": platform.machine(),
    }

if __name__ == "__main__":
    print(json.dumps(current_device_identity(), indent=2))
