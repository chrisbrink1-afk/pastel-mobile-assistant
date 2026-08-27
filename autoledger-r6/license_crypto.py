from __future__ import annotations
import base64, hashlib, hmac, json
from datetime import date

PREFIX = "ALP225R6"
PRODUCT = "AUTOLEDGER"
EDITION = "PRO"
PRODUCT_VERSION = "2.2.5"
PUBLIC_N = int("b6d409b253f9fbe8a635b14d748cb5acff50a100c106ecc8f36778c74164ec6eca0a7c3d92e7469a1b3738b1414ab66ee416d8ad685083900dc063ab4165d05e0639a879b1b3ac6da1c8f2058ec11169b8fe6cc4706ec426baf5c91572b9951a6d6d989aaf7c474ad198ee06d314467adee451e5c76f9e715379de26628412209738fab06c6e5f8e13ade2f48d3334166c514c97b0b43aacafb69b649391f822ee69d4e2a06506982b313856c4ff62210ea51d09721867344ba756001723607db4d928bdef4b40e7c7174e618170d5b7c654c9ff074a11c6e1494eb1e8975286513af39a70733a1821811275c27db1904365853bf9637ac61938b37fc0364cc1", 16)
PUBLIC_E = 65537
SHA256_DIGESTINFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")

def _b64d(s: str) -> bytes:
    s = (s or "").strip(); s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))

def _verify(message: bytes, signature: bytes) -> bool:
    k = (PUBLIC_N.bit_length() + 7) // 8
    if len(signature) != k: return False
    s = int.from_bytes(signature, "big")
    if s >= PUBLIC_N: return False
    em = pow(s, PUBLIC_E, PUBLIC_N).to_bytes(k, "big")
    t = SHA256_DIGESTINFO_PREFIX + hashlib.sha256(message).digest()
    if len(em) < len(t) + 11 or not em.startswith(b"\x00\x01"): return False
    try: sep = em.index(b"\x00", 2)
    except ValueError: return False
    ps = em[2:sep]
    return len(ps) >= 8 and all(b == 0xFF for b in ps) and hmac.compare_digest(em[sep+1:], t)

def decode_and_verify_key(key: str) -> dict:
    key = "".join((key or "").split())
    parts = key.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        raise ValueError("This is not a valid AUTOLEDGER Pro v2.2.5 R6 licence key.")
    payload_bytes = _b64d(parts[1]); signature = _b64d(parts[2])
    if not _verify(payload_bytes, signature):
        raise ValueError("The AUTOLEDGER Pro licence signature is invalid.")
    try: payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc: raise ValueError("The licence payload is invalid.") from exc
    if payload.get("product") != PRODUCT or payload.get("edition") != EDITION:
        raise ValueError("This licence was issued for a different product or edition.")
    if payload.get("version") != PRODUCT_VERSION:
        raise ValueError("This licence was issued for a different AUTOLEDGER version.")
    expires = payload.get("expires")
    if expires:
        try: expiry = date.fromisoformat(expires)
        except ValueError as exc: raise ValueError("The licence expiry date is invalid.") from exc
        if date.today() > expiry: raise ValueError(f"This AUTOLEDGER Pro licence expired on {expires}.")
    return payload
