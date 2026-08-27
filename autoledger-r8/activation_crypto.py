from __future__ import annotations
import base64, json
from datetime import datetime, timezone
from license_crypto import verify_rsa_sha256

ACTIVATION_PREFIX = "ALA225A1"
ACTIVATION_PUBLIC_N = int("8a0af1a58f3e607485452d88c4f143b788cff5f9329954cce790de537e4dcd3ccac408806dc984bab4439fb35933a43378991876326bc84e5b940bea152e388158ab5b653d7257dfbeafa00318325cd00fe09841726ed5f74efaacec7f9320e91aff95ca583b18e2d7e9d183a1222ac6014dc06992b9f7c70e15eb32d029d0fb39c9fe7a2ef1072e645b3c37ce30e86d2a4276f5e6705c4504190c458b6be6eb9db15efd196f2d76edd88777a830a9bf83ea81d0d96824c5e092e1c1405a573908e96e5c5bcfc468601e06a444172ae75f0851d3d4fe08aac0ebf96815bd79bb27a1084c44ffb623880517549b7048b9ba5b748c96e3320a4daaaec37ccc7d4cedbc002d5e6a05c063f079090deb7ceca6abbdcf9f54b9a4e6423071176a2e56954747929a818e0eaf62d6640f85ec3e3ecbaa31513b74a1c67b68db7e282af60035b01b78e347dd4aa1652435526d6ec9f4ea982cb7605aa5a3f16059938e23b111bd860e788d9d7f98a1766119bd12ef58eaca3a90f9566080705a5fe85993", 16)
ACTIVATION_PUBLIC_E = 65537

def _b64d(s: str) -> bytes:
    s = (s or "").strip(); s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))

def decode_and_verify_activation(token: str) -> dict:
    token = "".join((token or "").split())
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != ACTIVATION_PREFIX:
        raise ValueError("The AUTOLEDGER device activation token is invalid.")
    payload_bytes = _b64d(parts[1]); signature = _b64d(parts[2])
    if not verify_rsa_sha256(payload_bytes, signature, ACTIVATION_PUBLIC_N, ACTIVATION_PUBLIC_E):
        raise ValueError("The AUTOLEDGER device activation signature is invalid.")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("The AUTOLEDGER device activation payload is invalid.") from exc
    if payload.get("product") != "AUTOLEDGER" or payload.get("edition") != "PRO":
        raise ValueError("This activation was issued for a different product.")
    return payload

def _parse_utc(value: str):
    dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def activation_expired(payload: dict) -> bool:
    try:
        return datetime.now(timezone.utc) > _parse_utc(payload.get("valid_until"))
    except Exception:
        return True

def activation_refresh_due(payload: dict) -> bool:
    try:
        issued = _parse_utc(payload.get("issued_at"))
    except Exception:
        return True
    # Validate at 30 days; production tokens expire at 90 days, providing approximately 60 days of offline grace.
    return (datetime.now(timezone.utc) - issued).total_seconds() >= 30 * 86400
