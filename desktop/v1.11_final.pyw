from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Tuple

APP_NAME = "Pastel Payment Assistant"
APP_VERSION = "1.11.0"


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") if os.name == "nt" else None
    root = Path(base) if base else Path.home() / ".pastel_payment_assistant"
    p = root / "PastelPaymentAssistant" if base else root
    p.mkdir(parents=True, exist_ok=True)
    return p

DB_PATH = app_data_dir() / "pastel_payment_assistant.db"
SETTINGS_TRANSFER_KEYS = ("contra_account", "vat_tax_type", "vat_rate", "fiscal_start_month", "project_code")


def read_settings_transfer(path: str) -> Dict[str, str]:
    p = Path(path)
    if p.suffix.lower() == ".db":
        conn = sqlite3.connect(p)
        try:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        finally:
            conn.close()
        raw = {str(k): str(v) for k, v in rows}
    else:
        with open(p, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Settings backup must contain a JSON object.")
        raw = data.get("settings", data)
        if not isinstance(raw, dict):
            raise ValueError("Settings backup does not contain a settings object.")
    out = {k: str(raw[k]) for k in SETTINGS_TRANSFER_KEYS if k in raw}
    if not out:
        raise ValueError("No compatible Pastel Payment Assistant settings were found in this file.")
    return out


def D(value) -> Decimal:
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return Decimal("0")


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def amount_condition_matches(amount: Decimal, operator: str, threshold: str) -> bool:
    op = (operator or "").strip()
    if op not in {"<", "<=", ">", ">=", "="}:
        return False
    try:
        limit = Decimal(str(threshold).replace(",", "").strip())
    except (InvalidOperation, AttributeError, ValueError):
        return False
    value = abs(D(amount))
    if op == "<":
        return value < limit
    if op == "<=":
        return value <= limit
    if op == ">":
        return value > limit
    if op == ">=":
        return value >= limit
    return value == limit


def effective_rule_account(rule: "Rule", amount: Decimal) -> Tuple[str, bool]:
    if rule.amount_account.strip() and amount_condition_matches(amount, rule.amount_operator, rule.amount_threshold):
        return rule.amount_account.strip(), True
    return rule.account.strip(), False


def normalize_text(value: str) -> str:
    value = (value or "").upper().replace("_", " ")
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def looks_like_date_code(token: str) -> bool:
    if not token.isdigit():
        return False
    candidates = []
    if len(token) == 6:
        candidates = ["%y%m%d"]
    elif len(token) == 8:
        candidates = ["%Y%m%d", "%d%m%Y"]
    for fmt in candidates:
        try:
            datetime.strptime(token, fmt)
            return True
        except ValueError:
            pass
    return False


def looks_like_time_code(token: str) -> bool:
    # Standard Bank often appends times such as 13H37 / 09H30. These are not
    # contract identifiers and must never become a recurring-payment suffix.
    return bool(re.fullmatch(r"\d{1,2}H\d{2}", (token or "").upper()))


def smart_key(details: str, txn_type: str = "") -> str:
    """Return a friendly recurring-payment identity, e.g. HOLLARD 0923.

    For known statement formats we prefer the *stable* contract/account identifier,
    not simply the first number in the description. This matters for references
    such as VODACOM where an earlier number changes monthly but B0003783 remains
    constant. The amount is never part of this identity.
    """
    raw = (details or "").upper()

    # Known recurring-payment reference structures observed in the supplied
    # Standard Bank statements. Keep these deliberately specific: a false
    # automatic allocation is worse than leaving a payment unassigned.
    special_patterns = [
        (r"\bHOLLARD\b.*?\bHOL(\d{4,})\b", "HOLLARD"),
        (r"\bBRIGHTROCK[_ ]*(\d{4,})\b", "BRIGHTROCK"),
        (r"\bDISC\s+PREM\b\s*(\d{4,})", "DISC PREM"),
        (r"\bMAS\b\s+PP(\d{4,})", "MAS"),
        # VODACOM: the leading 10-digit number changed between June and July;
        # B0003783 stayed fixed and is therefore the reliable identity.
        (r"\bVODACOM\b.*?\bB(\d{4,})\b", "VODACOM"),
        (r"\bCIB\b\s+(?:CIBC|CIBV)(\d{4,})", "CIB"),
        (r"ALLAN\s+GRAYAGLP(\d{4,})", "ALLAN GRAY"),
        (r"WESTERNINS(?:GAP|COMPLIGAP)(\d{4,})", "WESTERNINS"),
        (r"NORTHCOASTARB(\d{2,})", "NORTHCOAST"),
        (r"\b(\d{4})\s+AR\s+BRINK\b", "AR BRINK"),
        # Card autopay references are best distinguished by the card suffix
        # after the asterisk.
        (r"\bSB\s+AUTOPAY\b.*?\*(\d{4})\b", "SB AUTOPAY"),
    ]
    for pattern, merchant in special_patterns:
        m = re.search(pattern, raw)
        if m:
            digits = m.group(1)
            suffix = digits[-4:] if len(digits) >= 4 else digits
            return f"{merchant} {suffix}"

    # A VODACOM entry without the stable B-number may be a manual transfer.
    # Do not accidentally turn its bank timestamp (e.g. 13H37) into an ID.
    if re.search(r"\bVODACOM\b", raw):
        return "VODACOM"

    text = normalize_text(details)
    toks = text.split()
    if not toks:
        return normalize_text(txn_type)[:40]

    # Generic fallback: find a useful leading name and the first plausible ID.
    name_parts = []
    ident_suffix = None
    for tok in toks:
        has_alpha = bool(re.search(r"[A-Z]", tok))
        if looks_like_time_code(tok):
            continue
        digits = "".join(re.findall(r"\d", tok))
        if digits and not looks_like_date_code(digits):
            if len(digits) >= 4:
                ident_suffix = digits[-4:]
                break
        if has_alpha and not digits and len(name_parts) < 3:
            if tok not in {"PTY", "LTD", "CC"}:
                name_parts.append(tok)
        elif has_alpha and digits:
            if len(digits) >= 4 and not looks_like_date_code(digits):
                ident_suffix = digits[-4:]
                break

    if not name_parts:
        for tok in toks:
            letters = re.sub(r"[^A-Z]", "", tok)
            if letters:
                name_parts = [letters]
                break

    if ident_suffix and name_parts:
        return f"{name_parts[0]} {ident_suffix}"
    if name_parts:
        return " ".join(name_parts[:3])
    return text[:40]


def smart_match(pattern: str, details: str, txn_type: str = "") -> bool:
    p = normalize_text(pattern)
    t = normalize_text(f"{details} {txn_type}")
    if not p:
        return False
    ptoks = p.split()
    ttoks = t.split()
    digit_parts = [x for x in ptoks if x.isdigit()]
    word_parts = [x for x in ptoks if not x.isdigit()]

    for word in word_parts:
        if word not in ttoks and word not in t:
            return False
    for digits in digit_parts:
        if not any("".join(re.findall(r"\d", tok)).endswith(digits) for tok in ttoks):
            return False
    return True


def repeat_description_choices(txns: List["Transaction"]) -> List[str]:
    """Return recurring Smart name + stable-reference identities.

    The amount is intentionally ignored; each statement row keeps its own
    current amount for export.
    """
    keys = {smart_key(t.details, t.txn_type) for t in txns if t.include and t.recurring_count >= 2}
    return sorted((k for k in keys if k), key=lambda x: normalize_text(x))


def recurring_parent_name(key: str) -> str:
    """Group identities such as HOLLARD 6957/0923/2091 under HOLLARD.

    Only a trailing numeric identifier is removed. The full smart key remains
    the rule identity, so each child can map to a different GL/VAT rule.
    """
    key = normalize_text(key)
    m = re.match(r"^(.*?)(?:\s+)(\d{2,8})$", key)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return key


def recurring_child_label(key: str) -> str:
    key = normalize_text(key)
    parent = recurring_parent_name(key)
    if parent != key and key.startswith(parent + " "):
        return key[len(parent) + 1:]
    return key


def rule_matches(mode: str, pattern: str, details: str, txn_type: str) -> bool:
    p = normalize_text(pattern)
    t = normalize_text(f"{details} {txn_type}")
    d = normalize_text(details)
    if not p:
        return False
    mode = (mode or "SMART").upper()
    if mode == "EXACT":
        return p == d or p == t
    if mode == "STARTS":
        return d.startswith(p) or t.startswith(p)
    if mode == "CONTAINS":
        return p in d or p in t
    return smart_match(p, details, txn_type)


def mode_rank(mode: str) -> int:
    return {"EXACT": 4, "SMART": 3, "STARTS": 2, "CONTAINS": 1}.get((mode or "").upper(), 0)


def derive_pastel_reference(details: str, key: str, row_no: int) -> str:
    # Prefer the user's friendly numeric suffix, e.g. HOLLARD 0923 -> 0923.
    key_tokens = normalize_text(key).split()
    nums = [t for t in key_tokens if t.isdigit() and not looks_like_date_code(t)]
    if nums:
        return nums[-1][-8:]

    # Then use a non-date identifier embedded in the bank details.
    for tok in normalize_text(details).split():
        digits = "".join(re.findall(r"\d", tok))
        if digits and not looks_like_date_code(digits):
            return digits[-8:]

    # Final deterministic fallback: 8 chars, useful for review even without a bank reference.
    return f"P{row_no:07d}"[-8:]


def period_for_date(d: date, fiscal_start_month: int) -> int:
    return ((d.month - fiscal_start_month) % 12) + 1


@dataclass
class Rule:
    id: Optional[int]
    name: str
    mode: str
    pattern: str
    account: str
    vat: bool
    tax_type: int
    pastel_ref: str = ""
    priority: int = 100
    enabled: bool = True
    direction: str = "PAYMENT"
    description: str = ""
    amount_operator: str = ""
    amount_threshold: str = ""
    amount_account: str = ""


@dataclass
class Transaction:
    row_no: int
    txn_date: date
    amount: Decimal
    txn_type: str
    details: str
    bank_code: str = ""
    source: str = ""
    include: bool = True
    rule_id: Optional[int] = None
    rule_name: str = ""
    account: str = ""
    vat: bool = False
    tax_type: int = 0
    match_key: str = ""
    pastel_ref: str = ""
    status: str = "Unassigned"
    manual_override: bool = False
    ambiguous: bool = False
    recurring_count: int = 1
    previously_seen: bool = False
    direction: str = "PAYMENT"
    contra: str = ""  # legacy v1.9 field; ignored in v1.10 cash-book exports
    description: str = ""
    auto_allocated: bool = False
    amount_condition_applied: bool = False

    @property
    def payment_amount(self) -> Decimal:
        return abs(self.amount)


class Store:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'SMART',
            pattern TEXT NOT NULL,
            account TEXT NOT NULL,
            vat INTEGER NOT NULL DEFAULT 0,
            tax_type INTEGER NOT NULL DEFAULT 0,
            pastel_ref TEXT NOT NULL DEFAULT '',
            priority INTEGER NOT NULL DEFAULT 100,
            enabled INTEGER NOT NULL DEFAULT 1,
            direction TEXT NOT NULL DEFAULT 'PAYMENT',
            description TEXT NOT NULL DEFAULT '',
            amount_operator TEXT NOT NULL DEFAULT '',
            amount_threshold TEXT NOT NULL DEFAULT '',
            amount_account TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transaction_history (
            signature TEXT PRIMARY KEY,
            txn_date TEXT NOT NULL,
            match_key TEXT NOT NULL,
            details TEXT NOT NULL,
            amount TEXT NOT NULL,
            source_name TEXT NOT NULL DEFAULT '',
            direction TEXT NOT NULL DEFAULT 'PAYMENT',
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_history_match_key ON transaction_history(match_key);
        """)
        # Seamless upgrade from v1.6: all existing saved rules/history were payments.
        rule_cols = {r[1] for r in self.conn.execute("PRAGMA table_info(rules)").fetchall()}
        if "direction" not in rule_cols:
            self.conn.execute("ALTER TABLE rules ADD COLUMN direction TEXT NOT NULL DEFAULT 'PAYMENT'")
        for col, ddl in {
            "description": "TEXT NOT NULL DEFAULT ''",
            "amount_operator": "TEXT NOT NULL DEFAULT ''",
            "amount_threshold": "TEXT NOT NULL DEFAULT ''",
            "amount_account": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if col not in rule_cols:
                self.conn.execute(f"ALTER TABLE rules ADD COLUMN {col} {ddl}")
        hist_cols = {r[1] for r in self.conn.execute("PRAGMA table_info(transaction_history)").fetchall()}
        if "direction" not in hist_cols:
            self.conn.execute("ALTER TABLE transaction_history ADD COLUMN direction TEXT NOT NULL DEFAULT 'PAYMENT'")
        defaults = {
            "contra_account": "",
            "vat_tax_type": "",
            "vat_rate": "15",
            "fiscal_start_month": "3",
            "project_code": "",
            "last_folder": str(Path.home()),
        }
        for k, v in defaults.items():
            self.conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        self.conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        self.conn.commit()

    @staticmethod
    def _row_to_rule(r) -> Rule:
        keys = set(r.keys())
        direction = (r["direction"] if "direction" in keys else "PAYMENT") or "PAYMENT"
        return Rule(
            r["id"], r["name"], r["mode"], r["pattern"], r["account"], bool(r["vat"]), int(r["tax_type"]),
            r["pastel_ref"], int(r["priority"]), bool(r["enabled"]), direction.upper(),
            (r["description"] if "description" in keys else "") or "",
            (r["amount_operator"] if "amount_operator" in keys else "") or "",
            (r["amount_threshold"] if "amount_threshold" in keys else "") or "",
            (r["amount_account"] if "amount_account" in keys else "") or "",
        )

    def rules(self, direction: Optional[str] = None) -> List[Rule]:
        sql = "SELECT * FROM rules WHERE enabled=1"
        args = []
        if direction:
            sql += " AND UPPER(direction)=?"
            args.append(direction.upper())
        sql += " ORDER BY priority DESC, LENGTH(pattern) DESC, id ASC"
        rows = self.conn.execute(sql, args).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def all_rules(self, direction: Optional[str] = None) -> List[Rule]:
        sql = "SELECT * FROM rules"
        args = []
        if direction:
            sql += " WHERE UPPER(direction)=?"
            args.append(direction.upper())
        sql += " ORDER BY enabled DESC, direction, priority DESC, id ASC"
        rows = self.conn.execute(sql, args).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def save_rule(self, rule: Rule) -> int:
        direction = (rule.direction or "PAYMENT").upper()
        values = (
            rule.name, rule.mode, rule.pattern, rule.account, int(rule.vat), int(rule.tax_type), rule.pastel_ref,
            int(rule.priority), int(rule.enabled), direction, rule.description or "", rule.amount_operator or "",
            rule.amount_threshold or "", rule.amount_account or "",
        )
        if rule.id:
            self.conn.execute(
                """UPDATE rules SET name=?,mode=?,pattern=?,account=?,vat=?,tax_type=?,pastel_ref=?,priority=?,enabled=?,direction=?,description=?,amount_operator=?,amount_threshold=?,amount_account=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                values + (rule.id,),
            )
            rid = rule.id
        else:
            cur = self.conn.execute(
                """INSERT INTO rules(name,mode,pattern,account,vat,tax_type,pastel_ref,priority,enabled,direction,description,amount_operator,amount_threshold,amount_account) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                values,
            )
            rid = int(cur.lastrowid)
        self.conn.commit()
        return rid

    def delete_rule(self, rid: int):
        self.conn.execute("DELETE FROM rules WHERE id=?", (rid,))
        self.conn.commit()

    def get_rule(self, rid: int) -> Optional[Rule]:
        r = self.conn.execute("SELECT * FROM rules WHERE id=?", (rid,)).fetchone()
        return self._row_to_rule(r) if r else None

    def known_accounts(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT account FROM (SELECT TRIM(account) AS account FROM rules WHERE TRIM(account) <> '' UNION SELECT TRIM(amount_account) AS account FROM rules WHERE TRIM(amount_account) <> '') ORDER BY account"
        ).fetchall()
        return [r["account"] for r in rows if r["account"]]

    @staticmethod
    def _txn_signature(t: Transaction) -> str:
        # Preserve the legacy payment signature to avoid double-counting old history.
        base = f"{t.txn_date.isoformat()}|{normalize_text(t.details)}|{money(t.payment_amount)}"
        raw = base if (t.direction or "PAYMENT").upper() == "PAYMENT" else f"RECEIPT|{base}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def remember_transactions(self, txns: List[Transaction]):
        """Remember unique transactions by direction; amount is audit-only, never a match key."""
        if not txns:
            return
        key_pairs = []
        for t in txns:
            key = smart_key(t.details, t.txn_type)
            direction = (t.direction or "PAYMENT").upper()
            key_pairs.append((direction, key))
            sig = self._txn_signature(t)
            self.conn.execute(
                "INSERT OR IGNORE INTO transaction_history(signature,txn_date,match_key,details,amount,source_name,direction) VALUES(?,?,?,?,?,?,?)",
                (sig, t.txn_date.isoformat(), key, t.details, money(t.payment_amount), Path(t.source).name if t.source else "", direction)
            )
        self.conn.commit()

        current_counts: Dict[Tuple[str, str], int] = {}
        for pair in key_pairs:
            current_counts[pair] = current_counts.get(pair, 0) + 1

        counts: Dict[Tuple[str, str], int] = {}
        for direction, key in sorted(set(key_pairs)):
            row = self.conn.execute(
                "SELECT COUNT(*) AS c FROM transaction_history WHERE UPPER(direction)=? AND match_key=?",
                (direction, key)
            ).fetchone()
            counts[(direction, key)] = int(row["c"] if row else 0)

        for t in txns:
            direction = (t.direction or "PAYMENT").upper()
            key = smart_key(t.details, t.txn_type)
            pair = (direction, key)
            t.recurring_count = max(counts.get(pair, 1), current_counts.get(pair, 1))
            t.previously_seen = counts.get(pair, 0) > current_counts.get(pair, 0)

    def recurring_summary(self, direction: Optional[str] = None) -> List[sqlite3.Row]:
        sql = "SELECT direction, match_key, COUNT(*) AS seen_count, MIN(txn_date) AS first_date, MAX(txn_date) AS last_date, MIN(CAST(amount AS REAL)) AS min_amount, MAX(CAST(amount AS REAL)) AS max_amount FROM transaction_history"
        args = []
        if direction:
            sql += " WHERE UPPER(direction)=?"
            args.append(direction.upper())
        sql += " GROUP BY direction, match_key HAVING COUNT(*) >= 2 ORDER BY last_date DESC, match_key"
        return self.conn.execute(sql, args).fetchall()


class BankCSVParser:
    DATE_NAMES = {"date", "transaction date", "trans date", "value date", "posting date"}
    AMOUNT_NAMES = {"amount", "transaction amount", "value"}
    DESC_NAMES = {"description", "details", "transaction description", "narrative", "payee", "beneficiary", "reference"}

    @staticmethod
    def load(path: str) -> Tuple[List[Transaction], List[Transaction], str]:
        with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            raw = list(csv.reader(f))
        if not raw:
            raise ValueError("The CSV file is empty.")

        payments, receipts = BankCSVParser._parse_hist(raw, path)
        if payments or receipts:
            return payments, receipts, "Standard Bank / HIST statement format"

        payments, receipts = BankCSVParser._parse_headered(raw, path)
        if payments or receipts:
            return payments, receipts, "Headered bank CSV"
        raise ValueError("I could not identify the transaction columns in this CSV. This version recognises the supplied HIST statement format and common headered CSV files.")

    @staticmethod
    def _parse_hist(raw, path):
        payments, receipts = [], []
        for i, row in enumerate(raw, 1):
            if len(row) < 7 or row[0].strip().upper() != "HIST":
                continue
            try:
                d = datetime.strptime(row[1].strip(), "%Y%m%d").date()
                amt = D(row[3])
            except Exception:
                continue
            if amt == 0:
                continue
            direction = "PAYMENT" if amt < 0 else "RECEIPT"
            txn = Transaction(i, d, amt, row[4].strip(), row[5].strip(), row[6].strip(), path, direction=direction)
            (payments if direction == "PAYMENT" else receipts).append(txn)
        return payments, receipts

    @staticmethod
    def _parse_date(s: str) -> Optional[date]:
        s = (s or "").strip()
        for fmt in ("%Y%m%d", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _parse_headered(raw, path):
        headers = [normalize_text(x).lower() for x in raw[0]]
        def idx_for(names):
            for idx, h in enumerate(headers):
                if h in names:
                    return idx
            return None
        di = idx_for(BankCSVParser.DATE_NAMES)
        ai = idx_for(BankCSVParser.AMOUNT_NAMES)
        descis = [i for i, h in enumerate(headers) if h in BankCSVParser.DESC_NAMES]
        if di is None or ai is None or not descis:
            return [], []
        payments, receipts = [], []
        for i, row in enumerate(raw[1:], 2):
            if max([di, ai] + descis) >= len(row):
                continue
            d = BankCSVParser._parse_date(row[di])
            if not d:
                continue
            amt = D(row[ai])
            if amt == 0:
                continue
            details = " ".join(row[j].strip() for j in descis if row[j].strip())
            direction = "PAYMENT" if amt < 0 else "RECEIPT"
            txn = Transaction(i, d, amt, direction, details, "", path, direction=direction)
            (payments if direction == "PAYMENT" else receipts).append(txn)
        return payments, receipts


def apply_rules(txns: List[Transaction], rules: List[Rule], default_tax_type: int = 0):
    for t in txns:
        if t.manual_override:
            continue
        candidates = []
        for r in rules:
            if (r.direction or "PAYMENT").upper() != (t.direction or "PAYMENT").upper():
                continue
            if r.enabled and rule_matches(r.mode, r.pattern, t.details, t.txn_type):
                score = (int(r.priority), mode_rank(r.mode), len(normalize_text(r.pattern)))
                candidates.append((score, r))
        t.rule_id = None
        t.rule_name = ""
        t.account = ""
        t.description = ""
        t.vat = False
        t.tax_type = 0
        t.match_key = smart_key(t.details, t.txn_type)
        t.pastel_ref = derive_pastel_reference(t.details, t.match_key, t.row_no)
        t.status = f"Recurring x{t.recurring_count} • unassigned" if t.recurring_count >= 2 else "Unassigned"
        t.ambiguous = False
        t.auto_allocated = False
        t.amount_condition_applied = False
        if not candidates:
            continue
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_score = candidates[0][0]
        top = [r for score, r in candidates if score == top_score]
        distinct = {
            (effective_rule_account(r, t.payment_amount)[0], bool(r.vat), int(r.tax_type), (r.description or "").strip())
            for r in top
        }
        if len(top) > 1 and len(distinct) > 1:
            t.status = "Ambiguous rules"
            t.ambiguous = True
            continue
        r = top[0]
        account, amount_branch = effective_rule_account(r, t.payment_amount)
        t.rule_id = r.id
        t.rule_name = r.name
        t.account = account
        t.description = (r.description or "").strip()
        t.vat = bool(r.vat)
        t.tax_type = int(r.tax_type or default_tax_type or 0) if t.vat else 0
        t.match_key = r.pattern
        t.pastel_ref = (r.pastel_ref or derive_pastel_reference(t.details, r.pattern, t.row_no))[:8]
        t.auto_allocated = True
        t.amount_condition_applied = amount_branch
        amount_note = ""
        if amount_branch:
            amount_note = f" • amount {r.amount_operator} R {money(D(r.amount_threshold))}"
        base = f"Auto-assigned{amount_note}"
        t.status = f"{base} • recurring x{t.recurring_count}" if t.recurring_count >= 2 else base


def calculate_tax(gross: Decimal, vat: bool, rate: Decimal) -> Decimal:
    if not vat:
        return Decimal("0.00")
    if rate <= 0:
        return Decimal("0.00")
    # Bank payment is treated as VAT-inclusive by default.
    return (gross * rate / (Decimal("100") + rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def effective_contra(t: Transaction, settings: Dict[str, str]) -> str:
    """Return the cash-book bank GL used in Pastel import column L.

    Sage's import layout calls this field "Contra Account", but for a cash-book
    batch it is the bank/cash-book GL and is the same for every row in that batch.
    It is not a per-payment allocation.
    """
    return settings.get("contra_account", "").strip()


def validate_export(txns: List[Transaction], settings: Dict[str, str], label: str = "transactions") -> Tuple[List[str], List[str]]:
    errors, warnings = [], []
    cashbook_account = settings.get("contra_account", "").strip()
    if cashbook_account and len(cashbook_account) > 7:
        errors.append(f"Cash-book bank GL account '{cashbook_account}' is longer than Sage's 7-character layout.")
    if not cashbook_account:
        warnings.append("Cash-book bank GL account is blank. Pastel's CSV import layout calls column L 'Contra Account'; some Pastel versions require the bank GL of the selected cash book there. The app will still export with column L blank.")

    vat_rate = D(settings.get("vat_rate", "15"))
    try:
        default_tax = int(settings.get("vat_tax_type", "") or 0)
    except ValueError:
        default_tax = 0
    try:
        fiscal_start = int(settings.get("fiscal_start_month", "3"))
    except ValueError:
        fiscal_start = 0
    if not 1 <= fiscal_start <= 12:
        errors.append("Fiscal year start month must be between 1 and 12.")
    if settings.get("project_code", "") and len(settings.get("project_code", "")) > 5:
        errors.append("Project code is longer than Sage's 5-character layout.")

    selected = [t for t in txns if t.include]
    exportable = [t for t in selected if t.account]
    ambiguous = [t for t in selected if t.ambiguous]
    unassigned = [t for t in selected if not t.account and not t.ambiguous]
    if not selected:
        errors.append(f"There are no {label} selected for export.")
    elif not exportable:
        errors.append(f"There are no assigned {label} selected for export.")
    if unassigned:
        errors.append(f"{len(unassigned)} selected {label} are unassigned. Assign them or untick them before export.")
    if ambiguous:
        errors.append(f"{len(ambiguous)} selected {label} have ambiguous rule matches. Resolve the rule conflict or untick them before export.")

    vat_count = 0
    trunc_count = 0
    for t in exportable:
        if len(t.account) > 7:
            errors.append(f"Row {t.row_no}: GL account '{t.account}' exceeds 7 characters.")
        ref = (t.pastel_ref or "").strip()
        if len(ref) > 8:
            errors.append(f"Row {t.row_no}: Pastel reference '{ref}' exceeds 8 characters.")
        if len(t.description or t.details) > 36:
            trunc_count += 1
        if t.vat:
            vat_count += 1
            tax_type = int(t.tax_type or default_tax or 0)
            if tax_type <= 0:
                errors.append(f"Row {t.row_no}: VAT is ON but no valid Pastel VAT tax type is set.")
            if vat_rate <= 0:
                errors.append(f"Row {t.row_no}: VAT is ON but VAT rate is not greater than zero.")
        p = period_for_date(t.txn_date, fiscal_start) if 1 <= fiscal_start <= 12 else 0
        if not 1 <= p <= 13:
            errors.append(f"Row {t.row_no}: calculated period {p} is invalid.")

    if trunc_count:
        warnings.append(f"{trunc_count} description(s) exceed 36 characters and will be safely truncated in the Pastel file.")
    if vat_count:
        warnings.append("VAT amounts are calculated as VAT-inclusive from the bank transaction total. Confirm this treatment is correct for each selected row before posting.")
    if fiscal_start:
        warnings.append(f"Periods are calculated using fiscal-year start month {fiscal_start}. Confirm this matches Setup → Periods in Pastel.")
    return errors, warnings


def pastel_rows(txns: List[Transaction], settings: Dict[str, str]):
    project = settings.get("project_code", "").strip()
    fiscal_start = int(settings.get("fiscal_start_month", "3"))
    vat_rate = D(settings.get("vat_rate", "15"))
    default_tax = int(settings.get("vat_tax_type", "") or 0)
    for t in txns:
        if not (t.include and t.account):
            continue
        gross = t.payment_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_type = int(t.tax_type or default_tax or 0) if t.vat else 0
        tax_amount = calculate_tax(gross, t.vat, vat_rate)
        ref = (t.pastel_ref or derive_pastel_reference(t.details, t.match_key, t.row_no))[:8]
        desc = re.sub(r"\s+", " ", (t.description or t.details)).strip()[:36]
        amount_s = money(gross)
        contra = effective_contra(t, settings)
        yield [
            str(period_for_date(t.txn_date, fiscal_start)),
            t.txn_date.strftime("%d/%m/%Y"),
            "G",
            t.account.strip(),
            ref,
            desc,
            amount_s,
            str(tax_type),
            money(tax_amount),
            "A",
            project,
            contra,
            "1",
            "1",
            "1",
            "0",
            "0.00",
            amount_s,
        ]


class RuleDialog(tk.Toplevel):
    MODES = [("Smart name + number", "SMART"), ("Contains", "CONTAINS"), ("Starts with", "STARTS"), ("Exact", "EXACT")]
    def __init__(self, parent, store: Store, txn: Optional[Transaction] = None, rule: Optional[Rule] = None, locked_identity: str = "", direction: str = ""):
        super().__init__(parent)
        self.store = store
        self.txn = txn
        self.rule = rule
        self.locked_identity = normalize_text(locked_identity)
        self.result = None
        direction = (direction or (rule.direction if rule else (txn.direction if txn else "PAYMENT")) or "PAYMENT").upper()
        noun = "receipt" if direction == "RECEIPT" else "payment"
        self.direction = direction
        self.title(f"Assign {noun} rule" if txn else ("Edit rule" if rule else f"New {noun} rule"))
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        initial_key = rule.pattern if rule else (smart_key(txn.details, txn.txn_type) if txn else "")
        initial_name = rule.name if rule else initial_key
        initial_mode = rule.mode if rule else "SMART"
        initial_account = rule.account if rule else (txn.account if txn else "")
        initial_vat = rule.vat if rule else (txn.vat if txn else False)
        initial_tax = str(rule.tax_type if rule else (txn.tax_type if txn else (store.get_setting("vat_tax_type", "") or "")))
        initial_ref = rule.pastel_ref if rule else (derive_pastel_reference(txn.details, initial_key, txn.row_no) if txn else "")
        initial_priority = str(rule.priority if rule else 100)
        initial_description = rule.description if rule else (txn.description if txn else "")
        initial_amount_enabled = bool(rule and rule.amount_operator and rule.amount_account)
        initial_amount_operator = rule.amount_operator if rule and rule.amount_operator else "<"
        initial_amount_threshold = rule.amount_threshold if rule else ""
        initial_amount_account = rule.amount_account if rule else ""

        self.vars = {
            "name": tk.StringVar(value=initial_name),
            "pattern": tk.StringVar(value=initial_key),
            "mode_label": tk.StringVar(value=next((a for a,b in self.MODES if b == initial_mode), self.MODES[0][0])),
            "account": tk.StringVar(value=initial_account),
            "vat": tk.BooleanVar(value=initial_vat),
            "tax": tk.StringVar(value=initial_tax),
            "ref": tk.StringVar(value=initial_ref[:8]),
            "priority": tk.StringVar(value=initial_priority),
            "description": tk.StringVar(value=initial_description),
            "amount_enabled": tk.BooleanVar(value=initial_amount_enabled),
            "amount_operator": tk.StringVar(value=initial_amount_operator),
            "amount_threshold": tk.StringVar(value=initial_amount_threshold),
            "amount_account": tk.StringVar(value=initial_amount_account),
        }

        root = ttk.Frame(self, padding=14)
        root.grid(sticky="nsew")
        row = 0
        if txn:
            ttk.Label(root, text=f"Selected bank {noun}", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky="w")
            row += 1
            ttk.Label(root, text=f"{txn.txn_date:%d/%m/%Y}   R {money(txn.payment_amount)}\n{txn.txn_type} — {txn.details}", wraplength=560).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0,12))
            row += 1
        fields = [
            ("Rule name", "name"),
            ("Name / number to match", "pattern"),
            ("General ledger account", "account"),
            ("Pastel description (optional)", "description"),
            ("Pastel reference (max 8)", "ref"),
            ("Priority", "priority"),
        ]
        for label, key in fields:
            ttk.Label(root, text=label).grid(row=row, column=0, sticky="w", padx=(0,10), pady=4)
            if key == "account":
                entry = ttk.Combobox(root, textvariable=self.vars[key], values=self.store.known_accounts(), width=45)
                entry.grid(row=row, column=1, sticky="ew", pady=4)
            else:
                entry = ttk.Entry(root, textvariable=self.vars[key], width=48)
                entry.grid(row=row, column=1, sticky="ew", pady=4)
                if key == "pattern" and self.locked_identity:
                    self.vars["pattern"].set(self.locked_identity)
                    entry.configure(state="readonly")
            row += 1
        ttk.Label(root, text="Matching method").grid(row=row, column=0, sticky="w", pady=4)
        combo = ttk.Combobox(root, textvariable=self.vars["mode_label"], values=[x[0] for x in self.MODES], state="readonly", width=45)
        if self.locked_identity:
            self.vars["mode_label"].set("Smart name + number")
            combo.configure(state="disabled")
        combo.grid(row=row, column=1, sticky="ew", pady=4); row += 1
        if self.locked_identity:
            ttk.Label(root,text=f"This rule is locked to {self.locked_identity}; it will not be applied to the merchant's other reference numbers.",wraplength=560,foreground="#555555").grid(row=row,column=0,columnspan=2,sticky="w",pady=(2,6)); row += 1

        vat_box = ttk.LabelFrame(root, text="VAT treatment", padding=8)
        vat_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8,4)); row += 1
        ttk.Radiobutton(vat_box, text="No VAT", variable=self.vars["vat"], value=False, command=self._vat_state).pack(side="left", padx=(0,14))
        ttk.Radiobutton(vat_box, text="VAT", variable=self.vars["vat"], value=True, command=self._vat_state).pack(side="left")
        ttk.Label(vat_box, text="Pastel tax type:").pack(side="left", padx=(24,6))
        self.tax_entry = ttk.Entry(vat_box, textvariable=self.vars["tax"], width=6)
        self.tax_entry.pack(side="left")
        self._vat_state()

        amount_box = ttk.LabelFrame(root, text="Optional amount-based allocation", padding=8)
        amount_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8,4)); row += 1
        ttk.Checkbutton(amount_box, text="Use amount-based allocation rule", variable=self.vars["amount_enabled"], command=self._amount_state).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,6))
        ttk.Label(amount_box, text="If amount").grid(row=1, column=0, sticky="w")
        self.amount_op = ttk.Combobox(amount_box, textvariable=self.vars["amount_operator"], values=["<", "<=", ">", ">=", "="], state="readonly", width=5)
        self.amount_op.grid(row=1, column=1, padx=(5,8))
        self.amount_threshold = ttk.Entry(amount_box, textvariable=self.vars["amount_threshold"], width=12)
        self.amount_threshold.grid(row=1, column=2, padx=(0,10))
        ttk.Label(amount_box, text="allocate to GL").grid(row=1, column=3, sticky="w")
        self.amount_account = ttk.Combobox(amount_box, textvariable=self.vars["amount_account"], values=self.store.known_accounts(), width=20)
        self.amount_account.grid(row=1, column=4, padx=(6,0), sticky="ew")
        ttk.Label(amount_box, text="If the condition is not met, the normal General ledger account above is used.", foreground="#555555", wraplength=520).grid(row=2, column=0, columnspan=6, sticky="w", pady=(6,0))
        self._amount_state()

        ttk.Label(root, text="Tip: Smart matching lets 'HOLLARD 0923' match a bank reference such as 'HOLLARD HOL5910923 260601'.", wraplength=560).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8,10)); row += 1
        btns = ttk.Frame(root); btns.grid(row=row, column=0, columnspan=2, sticky="e")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(8,0))
        ttk.Button(btns, text="Save rule", command=self.save).pack(side="right")
        root.columnconfigure(1, weight=1)
        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_visibility(); self.focus_force()

    def _vat_state(self):
        self.tax_entry.configure(state="normal" if self.vars["vat"].get() else "disabled")

    def _amount_state(self):
        enabled = bool(self.vars["amount_enabled"].get())
        self.amount_op.configure(state="readonly" if enabled else "disabled")
        self.amount_threshold.configure(state="normal" if enabled else "disabled")
        self.amount_account.configure(state="normal" if enabled else "disabled")

    def save(self):
        name = self.vars["name"].get().strip()
        pattern = self.vars["pattern"].get().strip()
        account = self.vars["account"].get().strip()
        ref = self.vars["ref"].get().strip()
        description = self.vars["description"].get().strip()
        if not name or not pattern or not account:
            messagebox.showerror(APP_NAME, "Rule name, match text and GL account are required.", parent=self)
            return
        if len(account) > 7:
            if not messagebox.askyesno(APP_NAME, "This GL account is longer than Sage's published 7-character cash-book layout. Save it anyway? Validation will block export until corrected.", parent=self):
                return
        if len(ref) > 8:
            messagebox.showerror(APP_NAME, "Pastel reference may not exceed 8 characters.", parent=self); return
        amount_operator = ""
        amount_threshold = ""
        amount_account = ""
        if self.vars["amount_enabled"].get():
            amount_operator = self.vars["amount_operator"].get().strip()
            amount_account = self.vars["amount_account"].get().strip()
            raw_threshold = self.vars["amount_threshold"].get().strip()
            if amount_operator not in {"<", "<=", ">", ">=", "="} or not raw_threshold or not amount_account:
                messagebox.showerror(APP_NAME, "For an amount-based rule, choose an operator, enter an amount and enter the alternate GL account.", parent=self); return
            try:
                threshold_value = Decimal(raw_threshold.replace(",", ""))
            except (InvalidOperation, ValueError):
                messagebox.showerror(APP_NAME, "The amount-rule threshold must be a valid number.", parent=self); return
            amount_threshold = money(threshold_value)
        try:
            priority = int(self.vars["priority"].get() or 100)
            tax_type = int(self.vars["tax"].get() or 0) if self.vars["vat"].get() else 0
        except ValueError:
            messagebox.showerror(APP_NAME, "Priority and tax type must be whole numbers.", parent=self); return
        mode = next((b for a,b in self.MODES if a == self.vars["mode_label"].get()), "SMART")
        r = Rule(
            self.rule.id if self.rule else None, name, mode, pattern, account, self.vars["vat"].get(), tax_type, ref, priority, True, self.direction,
            description, amount_operator, amount_threshold, amount_account,
        )
        rid = self.store.save_rule(r)
        self.result = rid
        self.destroy()


class ManualAssignDialog(tk.Toplevel):
    def __init__(self, parent, txn: Transaction, default_tax_type: str, known_accounts: Optional[List[str]] = None):
        super().__init__(parent)
        self.txn = txn
        self.result = None
        noun = "receipt" if (txn.direction or "PAYMENT").upper() == "RECEIPT" else "payment"
        self.title(f"Assign this {noun} only")
        self.transient(parent); self.grab_set(); self.resizable(False, False)
        a = tk.StringVar(value=txn.account)
        v = tk.BooleanVar(value=txn.vat)
        tax = tk.StringVar(value=str(txn.tax_type or default_tax_type or ""))
        ref = tk.StringVar(value=txn.pastel_ref or derive_pastel_reference(txn.details, smart_key(txn.details), txn.row_no))
        desc = tk.StringVar(value=txn.description or "")
        f = ttk.Frame(self, padding=14); f.grid()
        ttk.Label(f, text=f"{txn.txn_date:%d/%m/%Y}   R {money(txn.payment_amount)}", font=("Segoe UI",10,"bold")).grid(row=0,column=0,columnspan=2,sticky="w")
        ttk.Label(f, text=txn.details, wraplength=520).grid(row=1,column=0,columnspan=2,sticky="w",pady=(0,10))
        ttk.Label(f,text="GL account").grid(row=2,column=0,sticky="w",pady=4); ttk.Combobox(f,textvariable=a,values=known_accounts or [],width=37).grid(row=2,column=1,pady=4)
        ttk.Label(f,text="Pastel description").grid(row=3,column=0,sticky="w",pady=4); ttk.Entry(f,textvariable=desc,width=40).grid(row=3,column=1,pady=4)
        ttk.Label(f,text="Pastel reference").grid(row=4,column=0,sticky="w",pady=4); ttk.Entry(f,textvariable=ref,width=40).grid(row=4,column=1,pady=4)
        vatframe=ttk.Frame(f); vatframe.grid(row=5,column=0,columnspan=2,sticky="w",pady=6)
        ttk.Checkbutton(vatframe,text="VAT",variable=v).pack(side="left")
        ttk.Label(vatframe,text="Tax type").pack(side="left",padx=(18,5)); ttk.Entry(vatframe,textvariable=tax,width=6).pack(side="left")
        ttk.Label(f,text="This assignment applies only to this statement. Use 'Save rule' when you want future CSV files to remember the GL/VAT/description allocation.",wraplength=520).grid(row=6,column=0,columnspan=2,sticky="w",pady=(4,10))
        b=ttk.Frame(f); b.grid(row=7,column=0,columnspan=2,sticky="e")
        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=(8,0)); ttk.Button(b,text="Apply",command=lambda:self._save(a,v,tax,ref,desc)).pack(side="right")
        self.wait_visibility(); self.focus_force()
    def _save(self,a,v,tax,ref,desc):
        account=a.get().strip(); rr=ref.get().strip()
        if not account:
            messagebox.showerror(APP_NAME,"GL account is required.",parent=self); return
        if len(rr)>8:
            messagebox.showerror(APP_NAME,"Pastel reference may not exceed 8 characters.",parent=self); return
        try: tt=int(tax.get() or 0) if v.get() else 0
        except ValueError:
            messagebox.showerror(APP_NAME,"Tax type must be a whole number.",parent=self); return
        self.result=(account,bool(v.get()),tt,rr,desc.get().strip()); self.destroy()


class CorrectionDialog(tk.Toplevel):
    def __init__(self, parent, store: Store, txn: Transaction, rule: Optional[Rule]):
        super().__init__(parent)
        self.result = None
        self.rule = rule
        noun = "receipt" if (txn.direction or "PAYMENT").upper() == "RECEIPT" else "payment"
        self.title(f"Correct auto-allocation — {noun}")
        self.transient(parent); self.grab_set(); self.resizable(False, False)
        a = tk.StringVar(value=txn.account)
        desc = tk.StringVar(value=txn.description or "")
        v = tk.BooleanVar(value=txn.vat)
        tax = tk.StringVar(value=str(txn.tax_type or store.get_setting("vat_tax_type", "") or ""))
        ref = tk.StringVar(value=txn.pastel_ref)
        update_rule = tk.BooleanVar(value=False)
        f = ttk.Frame(self, padding=14); f.grid(sticky="nsew")
        ttk.Label(f, text="Flagged false auto-allocation", font=("Segoe UI",10,"bold")).grid(row=0,column=0,columnspan=2,sticky="w")
        ttk.Label(f, text=f"{txn.txn_date:%d/%m/%Y}   R {money(txn.payment_amount)}\n{txn.details}", wraplength=560).grid(row=1,column=0,columnspan=2,sticky="w",pady=(0,10))
        ttk.Label(f,text="Correct GL account").grid(row=2,column=0,sticky="w",pady=4); ttk.Combobox(f,textvariable=a,values=store.known_accounts(),width=40).grid(row=2,column=1,pady=4)
        ttk.Label(f,text="Correct Pastel description").grid(row=3,column=0,sticky="w",pady=4); ttk.Entry(f,textvariable=desc,width=43).grid(row=3,column=1,pady=4)
        ttk.Label(f,text="Pastel reference").grid(row=4,column=0,sticky="w",pady=4); ttk.Entry(f,textvariable=ref,width=43).grid(row=4,column=1,pady=4)
        vatframe=ttk.Frame(f); vatframe.grid(row=5,column=0,columnspan=2,sticky="w",pady=6)
        ttk.Checkbutton(vatframe,text="VAT",variable=v).pack(side="left")
        ttk.Label(vatframe,text="Tax type").pack(side="left",padx=(18,5)); ttk.Entry(vatframe,textvariable=tax,width=6).pack(side="left")
        if rule:
            text = f"Also update saved rule '{rule.name}' for future matching transactions"
            ttk.Checkbutton(f,text=text,variable=update_rule).grid(row=6,column=0,columnspan=2,sticky="w",pady=(8,2))
            if txn.amount_condition_applied and rule.amount_operator:
                ttk.Label(f,text="This transaction used the amount-based branch; updating the saved rule will correct that branch's GL account.",foreground="#555555",wraplength=560).grid(row=7,column=0,columnspan=2,sticky="w")
        else:
            ttk.Label(f,text="No saved rule is available, so this correction will apply to this statement only.",foreground="#555555",wraplength=560).grid(row=6,column=0,columnspan=2,sticky="w",pady=(8,2))
        b=ttk.Frame(f); b.grid(row=8,column=0,columnspan=2,sticky="e",pady=(12,0))
        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=(8,0))
        ttk.Button(b,text="Apply correction",command=lambda:self._save(a,desc,v,tax,ref,update_rule)).pack(side="right")
        self.wait_visibility(); self.focus_force()

    def _save(self,a,desc,v,tax,ref,update_rule):
        account=a.get().strip(); rr=ref.get().strip()
        if not account:
            messagebox.showerror(APP_NAME,"GL account is required.",parent=self); return
        if len(rr)>8:
            messagebox.showerror(APP_NAME,"Pastel reference may not exceed 8 characters.",parent=self); return
        try:
            tt=int(tax.get() or 0) if v.get() else 0
        except ValueError:
            messagebox.showerror(APP_NAME,"Tax type must be a whole number.",parent=self); return
        self.result=(account,desc.get().strip(),bool(v.get()),tt,rr,bool(update_rule.get())); self.destroy()


class App(tk.Tk):
    DIRECTIONS = ("PAYMENT", "RECEIPT")

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1380x800")
        self.minsize(1100, 680)
        self.store = Store()
        self.txns: List[Transaction] = []
        self.receipts: List[Transaction] = []
        self.current_file = ""
        self.parser_name = ""
        self.status_var = tk.StringVar(value="Load a bank CSV to begin.")
        self.search_vars = {d: tk.StringVar() for d in self.DIRECTIONS}
        self.filter_vars = {d: tk.StringVar(value="All") for d in self.DIRECTIONS}
        self.repeat_vars = {d: tk.StringVar(value="— Select repeat description —") for d in self.DIRECTIONS}
        self.sort_vars = {d: tk.StringVar(value="Oldest first") for d in self.DIRECTIONS}
        self.summary_vars = {d: tk.StringVar(value="No statement loaded") for d in self.DIRECTIONS}
        self.repeat_display_to_key: Dict[str, Dict[str, str]] = {d: {} for d in self.DIRECTIONS}
        self.trees: Dict[str, ttk.Treeview] = {}
        self.repeat_combos: Dict[str, ttk.Combobox] = {}
        self.recurring_trees: Dict[str, ttk.Treeview] = {}
        self.recurring_key_to_indices: Dict[str, Dict[str, List[int]]] = {d: {} for d in self.DIRECTIONS}
        self.recurring_item_to_index: Dict[str, Dict[str, int]] = {d: {} for d in self.DIRECTIONS}
        self._configure_style()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            pass
        s.configure("Treeview", rowheight=25, font=("Segoe UI", 9))
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        s.configure("Accent.TButton", font=("Segoe UI", 9, "bold"))

    def _list(self, direction: str) -> List[Transaction]:
        return self.receipts if direction == "RECEIPT" else self.txns

    @staticmethod
    def _noun(direction: str, plural: bool = False) -> str:
        if direction == "RECEIPT":
            return "receipts" if plural else "receipt"
        return "payments" if plural else "payment"

    def _build(self):
        top = ttk.Frame(self, padding=(12, 10)); top.pack(fill="x")
        ttk.Label(top, text=APP_NAME, font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(top, text="Load bank CSV…", command=self.load_csv, style="Accent.TButton").pack(side="left", padx=18)
        ttk.Button(top, text="Apply saved rules", command=self.reapply_rules).pack(side="left")
        ttk.Button(top, text="Check selected for errors", command=self.show_validation).pack(side="right")
        ttk.Button(top, text="Export selected to Pastel…", command=self.export_files, style="Accent.TButton").pack(side="right", padx=8)

        self.notebook = ttk.Notebook(self); self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.pay_tab = ttk.Frame(self.notebook)
        self.receipt_tab = ttk.Frame(self.notebook)
        self.recurring_pay_tab = ttk.Frame(self.notebook)
        self.recurring_receipt_tab = ttk.Frame(self.notebook)
        self.rule_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.pay_tab, text="Payments")
        self.notebook.add(self.receipt_tab, text="Receipts / Money In")
        self.notebook.add(self.recurring_pay_tab, text="Recurring Payments")
        self.notebook.add(self.recurring_receipt_tab, text="Recurring Receipts")
        self.notebook.add(self.rule_tab, text="Saved Rules")
        self.notebook.add(self.settings_tab, text="Settings")

        self._build_transaction_tab(self.pay_tab, "PAYMENT")
        self._build_transaction_tab(self.receipt_tab, "RECEIPT")
        self._build_recurring_tab(self.recurring_pay_tab, "PAYMENT")
        self._build_recurring_tab(self.recurring_receipt_tab, "RECEIPT")
        self._build_rules()
        self._build_settings()

        bar = ttk.Frame(self, padding=(12, 4, 12, 10)); bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.status_var).pack(side="left")
        ttk.Label(bar, text=f"Rules/settings saved in {DB_PATH}", foreground="#666666").pack(side="right")

    def _build_transaction_tab(self, tab, direction: str):
        noun_plural = self._noun(direction, True)
        controls = ttk.Frame(tab, padding=8); controls.pack(fill="x")

        filters = ttk.Frame(controls); filters.pack(fill="x", pady=(0, 6))
        ttk.Label(filters, text="Find:").pack(side="left")
        e = ttk.Entry(filters, textvariable=self.search_vars[direction], width=20)
        e.pack(side="left", padx=(5, 12)); e.bind("<KeyRelease>", lambda e, d=direction: self.refresh_transaction_tree(d))
        ttk.Label(filters, text="Show:").pack(side="left")
        flt = ttk.Combobox(
            filters, textvariable=self.filter_vars[direction],
            values=["All", "Recurring", "Unassigned", "Ambiguous", "Assigned", "Auto-allocated", "Corrected", "VAT", "No VAT", "Selected for export", "Not selected"],
            state="readonly", width=17
        )
        flt.pack(side="left", padx=(5, 12)); flt.bind("<<ComboboxSelected>>", lambda e, d=direction: self.refresh_transaction_tree(d))

        ttk.Label(filters, text="Repeat description:").pack(side="left")
        combo = ttk.Combobox(
            filters, textvariable=self.repeat_vars[direction],
            values=["— Select repeat description —", "All repeat descriptions"],
            state="readonly", width=28
        )
        combo.pack(side="left", padx=(5, 6)); combo.bind("<<ComboboxSelected>>", lambda e, d=direction: self._repeat_description_selected(d))
        self.repeat_combos[direction] = combo
        ttk.Button(filters, text="Clear", command=lambda d=direction: self.clear_repeat_description(d)).pack(side="left", padx=(0, 12))

        ttk.Label(filters, text="Sort date:").pack(side="left")
        sort = ttk.Combobox(filters, textvariable=self.sort_vars[direction], values=["Oldest first", "Newest first"], state="readonly", width=12)
        sort.pack(side="left", padx=(5, 0)); sort.bind("<<ComboboxSelected>>", lambda e, d=direction: self.refresh_transaction_tree(d))

        actions = ttk.Frame(controls); actions.pack(fill="x")
        ttk.Button(actions, text="Save rule from selected", command=lambda d=direction: self.assign_rule_selected(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="Assign once", command=lambda d=direction: self.manual_assign_selected(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="Correct auto-allocation", command=lambda d=direction: self.correct_auto_allocation_selected(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="VAT / No VAT (this statement)", command=lambda d=direction: self.toggle_vat_selected(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="Clear assignment", command=lambda d=direction: self.clear_assignment_selected(d)).pack(side="left", padx=(12, 3))
        ttk.Button(actions, text="Reset to saved rule", command=lambda d=direction: self.reset_selected_to_rule(d)).pack(side="left", padx=3)
        recurring_tab = self.recurring_receipt_tab if direction == "RECEIPT" else self.recurring_pay_tab
        ttk.Button(actions, text=f"Manage recurring {noun_plural}…", command=lambda t=recurring_tab: self.notebook.select(t)).pack(side="right", padx=3)

        actions2 = ttk.Frame(controls); actions2.pack(fill="x", pady=(5,0))
        ttk.Button(actions2, text="Toggle export selection", command=lambda d=direction: self.toggle_include_selected(d)).pack(side="left", padx=3)
        ttk.Button(actions2, text="Select Auto-Allocated", command=lambda d=direction: self.select_auto_allocated_export(d)).pack(side="left", padx=(12,3))
        ttk.Button(actions2, text="Select All", command=lambda d=direction: self.set_all_export(d, True)).pack(side="left", padx=3)
        ttk.Button(actions2, text="Clear All", command=lambda d=direction: self.set_all_export(d, False)).pack(side="left", padx=3)

        summary = ttk.Frame(tab, padding=(8, 0, 8, 7)); summary.pack(fill="x")
        ttk.Label(summary, textvariable=self.summary_vars[direction], font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Label(summary, text="☐ / ☑ controls export", foreground="#555555").pack(side="right")

        cols = ("inc", "date", "details", "description", "amount", "key", "repeat", "account", "vat", "rule", "status")
        tree = ttk.Treeview(tab, columns=cols, show="headings", selectmode="extended")
        self.trees[direction] = tree
        labels = {
            "inc": "Export", "date": "Date", "details": "Bank description / reference", "description": "Pastel description", "amount": "Current CSV amount",
            "key": "Matched name + number", "repeat": "Recurring", "account": "GL account", "vat": "VAT", "rule": "Rule", "status": "Status"
        }
        widths = {"inc": 58, "date": 88, "details": 280, "description": 170, "amount": 105, "key": 155, "repeat": 70, "account": 100, "vat": 55, "rule": 145, "status": 185}
        for c in cols:
            if c == "date":
                tree.heading(c, text=labels[c], command=lambda d=direction: self.toggle_date_sort(d))
            else:
                tree.heading(c, text=labels[c])
            tree.column(c, width=widths[c], anchor="center" if c == "inc" else ("e" if c == "amount" else "w"), stretch=(c in {"details", "description", "rule"}))
        y = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
        x = ttk.Scrollbar(tab, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8)); y.pack(side="right", fill="y", pady=(0, 8)); x.pack(side="bottom", fill="x", padx=8)
        tree.bind("<Button-1>", lambda e, d=direction: self._tree_click(e, d), add="+")
        tree.bind("<Double-1>", lambda e, d=direction: self._tree_double_click(e, d))
        tree.tag_configure("unassigned", background="#fff4d6")
        tree.tag_configure("assigned", background="#eaf7ea")
        tree.tag_configure("excluded", foreground="#888888")
        tree.tag_configure("ambiguous", background="#ffe5e5")
        tree.tag_configure("corrected", background="#e8f1ff")

    def _build_recurring_tab(self, tab, direction: str):
        noun = self._noun(direction)
        noun_plural = self._noun(direction, True)
        top = ttk.Frame(tab, padding=8); top.pack(fill="x")
        ttk.Label(
            top,
            text=(f"Expand a name and recurring identity to see every individual {noun} underneath it. "
                  f"Each actual transaction can be selected, included/excluded from export, and assigned independently for this statement. "
                  f"Use 'Save / edit identity rule' only when you deliberately want the same rule to apply to that recurring identity in future CSV files."),
            wraplength=1160
        ).pack(side="left", fill="x", expand=True)

        actions = ttk.Frame(tab, padding=(8, 0, 8, 7)); actions.pack(fill="x")
        ttk.Button(actions, text=f"Assign selected {noun} once", command=lambda d=direction: self.assign_recurring_transaction_once(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="Correct auto-allocation", command=lambda d=direction: self.correct_recurring_auto_allocation(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="Save / edit identity rule", command=lambda d=direction: self.assign_recurring_rule(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="Toggle export selection", command=lambda d=direction: self.toggle_recurring_include_selected(d)).pack(side="left", padx=(12, 3))
        ttk.Button(actions, text="Clear transaction assignment", command=lambda d=direction: self.clear_recurring_transaction_assignment(d)).pack(side="left", padx=3)
        ttk.Button(actions, text="Reset transaction to saved rule", command=lambda d=direction: self.reset_recurring_transaction_to_rule(d)).pack(side="left", padx=3)
        ttk.Button(actions, text=f"Show selected in {noun_plural.title()}", command=lambda d=direction: self.show_recurring_in_transactions(d)).pack(side="left", padx=(12, 3))

        actions2 = ttk.Frame(tab, padding=(8, 0, 8, 7)); actions2.pack(fill="x")
        ttk.Button(actions2, text="Select auto-allocated recurring", command=lambda d=direction: self.select_auto_allocated_export(d, True)).pack(side="left", padx=3)
        ttk.Button(actions2, text="Select all recurring for export", command=lambda d=direction: self.set_all_recurring_export(d, True)).pack(side="left", padx=3)
        ttk.Button(actions2, text="Clear all recurring from export", command=lambda d=direction: self.set_all_recurring_export(d, False)).pack(side="left", padx=3)
        ttk.Label(actions2, text="Tip: click the ☐ / ☑ box on an individual transaction to change only that transaction.", foreground="#555555").pack(side="left", padx=18)
        ttk.Button(actions2, text="Expand all", command=lambda d=direction: self.set_recurring_expanded(d, True)).pack(side="right", padx=3)
        ttk.Button(actions2, text="Collapse all", command=lambda d=direction: self.set_recurring_expanded(d, False)).pack(side="right", padx=3)

        cols = ("inc", "identity", "date", "details", "amount", "account", "vat", "rule", "status")
        tree = ttk.Treeview(tab, columns=cols, show="tree headings", selectmode="browse")
        self.recurring_trees[direction] = tree
        tree.heading("#0", text="Name / recurring identity / transaction")
        tree.column("#0", width=235, stretch=True)
        labels = {
            "inc": "Export", "identity": "Recurring identity", "date": "Date", "details": "Bank description / reference",
            "amount": "Current CSV amount", "account": "GL account", "vat": "VAT", "rule": "Rule", "status": "Status"
        }
        widths = {"inc":58, "identity":165, "date":88, "details":300, "amount":110, "account":100, "vat":55, "rule":145, "status":185}
        for c in cols:
            tree.heading(c, text=labels[c])
            anchor = "center" if c in {"inc", "date", "vat"} else ("e" if c == "amount" else "w")
            tree.column(c, width=widths[c], anchor=anchor, stretch=c in {"details", "rule", "status"})
        y = ttk.Scrollbar(tab, orient="vertical", command=tree.yview); x = ttk.Scrollbar(tab, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8)); y.pack(side="right", fill="y", pady=(0, 8)); x.pack(side="bottom", fill="x", padx=8)
        tree.bind("<Button-1>", lambda e, d=direction: self._recurring_tree_click(e, d), add="+")
        tree.bind("<Double-1>", lambda e, d=direction: self._recurring_tree_double_click(e, d))
        tree.tag_configure("unassigned", background="#fff4d6")
        tree.tag_configure("assigned", background="#eaf7ea")
        tree.tag_configure("excluded", foreground="#888888")
        tree.tag_configure("ambiguous", background="#ffe5e5")
        tree.tag_configure("corrected", background="#e8f1ff")
        tree.tag_configure("mixed", background="#eef3ff")
        tree.tag_configure("parent", font=("Segoe UI", 9, "bold"))
        tree.tag_configure("identity", font=("Segoe UI", 9, "bold"))

    def _build_rules(self):
        top = ttk.Frame(self.rule_tab, padding=8); top.pack(fill="x")
        ttk.Button(top, text="New payment rule", command=lambda: self.edit_rule(None, "PAYMENT")).pack(side="left", padx=3)
        ttk.Button(top, text="New receipt rule", command=lambda: self.edit_rule(None, "RECEIPT")).pack(side="left", padx=3)
        ttk.Button(top, text="Edit", command=self.edit_selected_rule).pack(side="left", padx=(12, 3))
        ttk.Button(top, text="Delete", command=self.delete_selected_rule).pack(side="left", padx=3)
        ttk.Button(top, text="Export rules backup…", command=self.export_rules).pack(side="right", padx=3)
        ttk.Button(top, text="Import rules backup…", command=self.import_rules).pack(side="right", padx=3)
        cols = ("id", "direction", "name", "mode", "pattern", "account", "description", "amount_rule", "vat", "tax", "ref", "priority")
        self.rule_tree = ttk.Treeview(self.rule_tab, columns=cols, show="headings", selectmode="browse")
        labels = {"id":"ID", "direction":"Type", "name":"Rule name", "mode":"Match", "pattern":"Name / number", "account":"GL account", "description":"Pastel description", "amount_rule":"Amount rule", "vat":"VAT", "tax":"Tax type", "ref":"Pastel ref", "priority":"Priority"}
        widths = {"id":45, "direction":75, "name":150, "mode":75, "pattern":180, "account":90, "description":160, "amount_rule":190, "vat":50, "tax":65, "ref":75, "priority":60}
        for c in cols:
            self.rule_tree.heading(c, text=labels[c]); self.rule_tree.column(c, width=widths[c], stretch=c in {"name", "pattern", "description", "amount_rule"})
        self.rule_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8)); self.rule_tree.bind("<Double-1>", lambda e: self.edit_selected_rule())
        self.refresh_rules()

    def _build_settings(self):
        f = ttk.Frame(self.settings_tab, padding=18); f.pack(anchor="nw", fill="x")
        self.setting_vars = {
            "contra_account": tk.StringVar(value=self.store.get_setting("contra_account")),
            "vat_tax_type": tk.StringVar(value=self.store.get_setting("vat_tax_type")),
            "vat_rate": tk.StringVar(value=self.store.get_setting("vat_rate", "15")),
            "fiscal_start_month": tk.StringVar(value=self.store.get_setting("fiscal_start_month", "3")),
            "project_code": tk.StringVar(value=self.store.get_setting("project_code")),
        }
        rows = [
            ("Cash Book bank GL account (Pastel import column L)", "contra_account", "This is the bank/general-ledger account linked to the Cash Book. Pastel's CSV layout calls column L 'Contra Account', but it is NOT a different contra per payment/receipt. Enter it once for the Cash Book (max 7 characters). You may leave it blank if your Pastel import accepts a blank column L."),
            ("VAT tax type number", "vat_tax_type", "Company-specific Pastel tax type. Leave blank until you confirm it in your Pastel company."),
            ("VAT rate (%)", "vat_rate", "Default 15%. VAT is calculated as inclusive from the bank transaction total."),
            ("Fiscal year start month (1–12)", "fiscal_start_month", "Used to calculate Pastel period 1–12 from each transaction date. Confirm against Setup → Periods."),
            ("Project code (optional)", "project_code", "Optional Pastel project/cost code, max 5 characters."),
        ]
        for i, (label, key, helptext) in enumerate(rows):
            ttk.Label(f, text=label, font=("Segoe UI", 10, "bold")).grid(row=i*2, column=0, sticky="w", pady=(6, 0))
            ttk.Entry(f, textvariable=self.setting_vars[key], width=24).grid(row=i*2, column=1, sticky="w", padx=14, pady=(6, 0))
            ttk.Label(f, text=helptext, wraplength=700, foreground="#555555").grid(row=i*2+1, column=0, columnspan=3, sticky="w", pady=(0, 6))
        buttons = ttk.Frame(f)
        buttons.grid(row=len(rows)*2, column=0, columnspan=3, sticky="w", pady=16)
        ttk.Button(buttons, text="Save settings", command=self.save_settings, style="Accent.TButton").pack(side="left", padx=(0,8))
        ttk.Button(buttons, text="Export settings backup…", command=self.export_settings_backup).pack(side="left", padx=4)
        ttk.Button(buttons, text="Import settings backup / v1.10 database…", command=self.import_settings_backup).pack(side="left", padx=4)
        transfer_note = ("Upgrading from v1.10 to v1.11 on the same Windows PC keeps these settings automatically because both versions use the same settings database. "
                         "For another PC, Import Settings can read either a v1.11 JSON settings backup or a copied v1.10 pastel_payment_assistant.db file.")
        ttk.Label(f, text=transfer_note, wraplength=820, foreground="#555555").grid(row=len(rows)*2+1, column=0, columnspan=3, sticky="w", pady=(0,8))
        note = ("The app creates review-first Pastel cash-book import files. Selected outgoing rows are exported to a Payments CSV; "
                "selected incoming rows are exported to a Receipts CSV. Review each imported batch in Pastel before Update/Process.")
        ttk.Label(f, text=note, wraplength=820).grid(row=len(rows)*2+2, column=0, columnspan=3, sticky="w")

    def settings_dict(self):
        return {k: v.get().strip() for k, v in self.setting_vars.items()}

    def save_settings(self, quiet=False):
        for k, v in self.setting_vars.items():
            self.store.set_setting(k, v.get().strip())
        if self.txns or self.receipts:
            self.reapply_rules(silent=True)
        if not quiet:
            messagebox.showinfo(APP_NAME, "Settings saved.")

    def export_settings_backup(self):
        self.save_settings(quiet=True)
        p = filedialog.asksaveasfilename(
            title="Export settings backup",
            defaultextension=".json",
            filetypes=[("Pastel settings backup", "*.json"), ("All files", "*.*")],
            initialfile="Pastel_Payment_Assistant_Settings_Backup.json",
        )
        if not p:
            return
        data = {
            "format": "PastelPaymentAssistantSettings",
            "format_version": 1,
            "app_version": APP_VERSION,
            "settings": {k: self.store.get_setting(k, "") for k in SETTINGS_TRANSFER_KEYS},
        }
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not export settings backup:\n{e}")
            return
        messagebox.showinfo(APP_NAME, f"Settings backup saved:\n{p}")

    def import_settings_backup(self):
        p = filedialog.askopenfilename(
            title="Import settings backup or v1.10 database",
            filetypes=[
                ("Pastel settings backup / database", "*.json *.db"),
                ("JSON settings backup", "*.json"),
                ("Pastel Payment Assistant database", "*.db"),
                ("All files", "*.*"),
            ],
        )
        if not p:
            return
        try:
            incoming = read_settings_transfer(p)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not import settings:\n{e}")
            return
        preview = "\n".join(f"{k}: {incoming.get(k, '')}" for k in SETTINGS_TRANSFER_KEYS if k in incoming)
        if not messagebox.askyesno(APP_NAME, "Import these settings and replace the current values?\n\n" + preview):
            return
        for k, value in incoming.items():
            if k in self.setting_vars:
                self.setting_vars[k].set(value)
        self.save_settings(quiet=True)
        source = "v1.10 database" if Path(p).suffix.lower() == ".db" else "settings backup"
        messagebox.showinfo(APP_NAME, f"Imported {len(incoming)} setting(s) from the {source}.\n\nThe imported values are now active in v1.11.")

    def load_csv(self):
        start = self.store.get_setting("last_folder", str(Path.home()))
        p = filedialog.askopenfilename(title="Select bank statement CSV", initialdir=start, filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not p:
            return
        try:
            payments, receipts, parser = BankCSVParser.load(p)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not load this CSV:\n\n{e}")
            return
        if not payments and not receipts:
            messagebox.showwarning(APP_NAME, "No bank transactions were found in this CSV.")
            return
        self.current_file = p; self.parser_name = parser; self.txns = payments; self.receipts = receipts
        self.store.set_setting("last_folder", str(Path(p).parent))
        self.store.remember_transactions(self.txns)
        self.store.remember_transactions(self.receipts)
        self.reapply_rules(silent=True)
        self.notebook.select(self.pay_tab if payments else self.receipt_tab)
        self.status_var.set(f"Loaded {len(payments)} payments and {len(receipts)} receipts from {Path(p).name} • amounts taken from this CSV")

    def reapply_rules(self, silent=False):
        if not self.txns and not self.receipts:
            if not silent:
                messagebox.showinfo(APP_NAME, "Load a bank CSV first.")
            return
        try:
            default_tax = int(self.store.get_setting("vat_tax_type", "") or 0)
        except Exception:
            default_tax = 0
        apply_rules(self.txns, self.store.rules("PAYMENT"), default_tax)
        apply_rules(self.receipts, self.store.rules("RECEIPT"), default_tax)
        for d in self.DIRECTIONS:
            self.update_repeat_dropdown(d)
            self.refresh_transaction_tree(d)
            self.refresh_recurring_tree(d)
        self.refresh_rules()
        psel = sum(1 for t in self.txns if t.include)
        rsel = sum(1 for t in self.receipts if t.include)
        passigned = sum(1 for t in self.txns if t.include and t.account and not t.ambiguous)
        rassigned = sum(1 for t in self.receipts if t.include and t.account and not t.ambiguous)
        self.status_var.set(f"Selected for export: {psel} payments ({passigned} assigned) • {rsel} receipts ({rassigned} assigned)")
        if not silent:
            messagebox.showinfo(APP_NAME, f"Saved rules applied.\n\nPayments selected: {psel}\nReceipts selected: {rsel}")

    def update_repeat_dropdown(self, direction: str):
        combo = self.repeat_combos.get(direction)
        if not combo:
            return
        txns = self._list(direction)
        keys = repeat_description_choices(txns)
        mapping = {}
        values = ["— Select repeat description —", "All repeat descriptions"]
        for key in keys:
            count = max((t.recurring_count for t in txns if smart_key(t.details, t.txn_type) == key), default=2)
            display = f"{key}  (x{count})"
            mapping[display] = key
            values.append(display)
        self.repeat_display_to_key[direction] = mapping
        combo.configure(values=values)
        if self.repeat_vars[direction].get() not in values:
            self.repeat_vars[direction].set("— Select repeat description —")

    def _repeat_description_selected(self, direction: str):
        choice = self.repeat_vars[direction].get()
        if choice == "All repeat descriptions" or choice in self.repeat_display_to_key[direction]:
            self.filter_vars[direction].set("Recurring")
        self.refresh_transaction_tree(direction)

    def clear_repeat_description(self, direction: str):
        self.repeat_vars[direction].set("— Select repeat description —")
        self.refresh_transaction_tree(direction)

    def toggle_date_sort(self, direction: str):
        self.sort_vars[direction].set("Newest first" if self.sort_vars[direction].get() == "Oldest first" else "Oldest first")
        self.refresh_transaction_tree(direction)

    def refresh_transaction_tree(self, direction: str):
        tree = self.trees.get(direction)
        if not tree:
            return
        txns = self._list(direction)
        q = normalize_text(self.search_vars[direction].get())
        flt = self.filter_vars[direction].get()
        repeat_choice = self.repeat_vars[direction].get()
        repeat_key = self.repeat_display_to_key[direction].get(repeat_choice, "")
        newest = self.sort_vars[direction].get() == "Newest first"
        tree.heading("date", text="Date ▼" if newest else "Date ▲", command=lambda d=direction: self.toggle_date_sort(d))
        tree.delete(*tree.get_children())
        shown = 0
        items = sorted(enumerate(txns), key=lambda p: (p[1].txn_date, p[1].row_no), reverse=newest)
        for idx, t in items:
            hay = normalize_text(f"{t.details} {t.description} {t.txn_type} {t.match_key} {t.account} {t.rule_name} {t.status}")
            if q and q not in hay:
                continue
            current_repeat_key = smart_key(t.details, t.txn_type)
            if repeat_choice == "All repeat descriptions" and t.recurring_count < 2:
                continue
            if repeat_key and current_repeat_key != repeat_key:
                continue
            if flt == "Recurring" and t.recurring_count < 2:
                continue
            if flt == "Unassigned" and (t.account or not t.include):
                continue
            if flt == "Ambiguous" and (not t.ambiguous or not t.include):
                continue
            if flt == "Assigned" and (not t.account or not t.include or t.ambiguous):
                continue
            if flt == "Auto-allocated" and (not t.auto_allocated or not t.include or t.ambiguous):
                continue
            if flt == "Corrected" and (not t.status.startswith("Corrected") or not t.include):
                continue
            if flt == "VAT" and (not t.vat or not t.include):
                continue
            if flt == "No VAT" and (t.vat or not t.include):
                continue
            if flt == "Selected for export" and not t.include:
                continue
            if flt == "Not selected" and t.include:
                continue
            tag = "excluded" if not t.include else ("ambiguous" if t.ambiguous else ("corrected" if t.status.startswith("Corrected") else ("assigned" if t.account else "unassigned")))
            repeat = f"x{t.recurring_count}" if t.recurring_count >= 2 else ""
            vals = ("☑" if t.include else "☐", t.txn_date.strftime("%d/%m/%Y"), t.details, t.description, f"R {money(t.payment_amount)}", t.match_key, repeat, t.account, "VAT" if t.vat else "No", t.rule_name, t.status)
            tree.insert("", "end", iid=str(idx), values=vals, tags=(tag,))
            shown += 1
        selected = [t for t in txns if t.include]
        total = sum((t.payment_amount for t in selected), Decimal("0.00"))
        assigned = sum(1 for t in selected if t.account and not t.ambiguous)
        ambiguous = sum(1 for t in selected if t.ambiguous)
        unassigned = sum(1 for t in selected if not t.account and not t.ambiguous)
        vat_count = sum(1 for t in selected if t.account and t.vat)
        auto_count = sum(1 for t in selected if t.auto_allocated and t.account and not t.ambiguous)
        corrected_count = sum(1 for t in selected if t.status.startswith("Corrected"))
        recurring = sum(1 for t in txns if t.recurring_count >= 2)
        recurring_groups = len({smart_key(t.details, t.txn_type) for t in txns if t.recurring_count >= 2})
        self.summary_vars[direction].set(
            f"{len(txns)} {self._noun(direction, True)} • {len(selected)} selected for export • {assigned} assigned • {unassigned} unassigned • "
            f"{recurring} recurring ({recurring_groups} groups) • {ambiguous} ambiguous • {auto_count} auto • {corrected_count} corrected • {vat_count} VAT • Selected total R {money(total)} • Showing {shown}"
        )

    def _tree_click(self, event, direction: str):
        tree = self.trees[direction]
        if tree.identify_region(event.x, event.y) == "cell" and tree.identify_column(event.x) == "#1":
            iid = tree.identify_row(event.y)
            if iid:
                txns = self._list(direction)
                try:
                    idx = int(iid); txns[idx].include = not txns[idx].include
                except Exception:
                    return
                self.refresh_transaction_tree(direction)
                tree.selection_set(iid)
                return "break"

    def _tree_double_click(self, event, direction: str):
        if self.trees[direction].identify_column(event.x) != "#1":
            self.assign_rule_selected(direction)

    def selected_txns(self, direction: str) -> List[Transaction]:
        out = []
        txns = self._list(direction)
        for iid in self.trees[direction].selection():
            try:
                out.append(txns[int(iid)])
            except Exception:
                pass
        return out

    def one_selected(self, direction: str) -> Optional[Transaction]:
        xs = self.selected_txns(direction)
        if not xs:
            messagebox.showinfo(APP_NAME, f"Select a {self._noun(direction)} first.")
            return None
        if len(xs) > 1:
            messagebox.showinfo(APP_NAME, f"Select one {self._noun(direction)} for this action.")
            return None
        return xs[0]

    def assign_rule_selected(self, direction: str):
        t = self.one_selected(direction)
        if not t:
            return
        existing = self.store.get_rule(t.rule_id) if t.rule_id else None
        if existing:
            choice = messagebox.askyesnocancel(
                APP_NAME,
                f"This {self._noun(direction)} is already matched by rule '{existing.name}'.\n\n"
                "Yes = edit that existing rule (affects future statements)\n"
                "No = create a new, more specific rule from this transaction\n"
                "Cancel = do nothing"
            )
            if choice is None:
                return
            if choice is False:
                existing = None
        dlg = RuleDialog(self, self.store, t, existing)
        self.wait_window(dlg)
        if dlg.result:
            t.manual_override = False
            self.reapply_rules(silent=True)

    def manual_assign_selected(self, direction: str):
        t = self.one_selected(direction)
        if not t:
            return
        dlg = ManualAssignDialog(self, t, self.store.get_setting("vat_tax_type", ""), self.store.known_accounts()); self.wait_window(dlg)
        if dlg.result:
            t.account, t.vat, t.tax_type, t.pastel_ref, t.description = dlg.result
            t.rule_id = None; t.rule_name = "Manual (this file only)"; t.status = "Manual assignment"; t.manual_override = True; t.ambiguous = False; t.auto_allocated = False; t.amount_condition_applied = False
            t.match_key = smart_key(t.details, t.txn_type)
            self.refresh_transaction_tree(direction)

    def toggle_vat_selected(self, direction: str):
        xs = self.selected_txns(direction)
        if not xs:
            messagebox.showinfo(APP_NAME, f"Select one or more {self._noun(direction, True)} first.")
            return
        try:
            default_tax = int(self.store.get_setting("vat_tax_type", "") or 0)
        except Exception:
            default_tax = 0
        target = not all(t.vat for t in xs)
        for t in xs:
            t.vat = target; t.tax_type = default_tax if target else 0; t.manual_override = True; t.auto_allocated = False
            if t.account:
                t.status = "Manual VAT override"
        self.refresh_transaction_tree(direction)

    def toggle_include_selected(self, direction: str):
        xs = self.selected_txns(direction)
        if not xs:
            messagebox.showinfo(APP_NAME, f"Select one or more {self._noun(direction, True)} first.")
            return
        target = not all(t.include for t in xs)
        for t in xs:
            t.include = target
        self.refresh_transaction_tree(direction)

    def set_all_export(self, direction: str, selected: bool):
        for t in self._list(direction):
            t.include = selected
        self.refresh_transaction_tree(direction)
        self.status_var.set(f"{'Selected all' if selected else 'Cleared all'} {self._noun(direction, True)} for export.")

    def select_auto_allocated_export(self, direction: str, recurring_only: bool = False):
        count = 0
        for t in self._list(direction):
            if recurring_only and t.recurring_count < 2:
                continue
            selected = bool(t.auto_allocated and t.account and not t.ambiguous)
            t.include = selected
            if selected:
                count += 1
        self.refresh_transaction_tree(direction)
        self.refresh_recurring_tree(direction)
        scope = "recurring " if recurring_only else ""
        self.status_var.set(f"Selected {count} automatically allocated {scope}{self._noun(direction, True)} for export; manual/corrected/unassigned rows were left unticked.")

    def correct_auto_allocation_selected(self, direction: str, txn: Optional[Transaction] = None):
        t = txn or self.one_selected(direction)
        if not t:
            return
        if not (t.auto_allocated and t.account and not t.ambiguous):
            messagebox.showinfo(APP_NAME, "Select an untouched automatically allocated transaction. Manual, corrected, ambiguous or unassigned rows are not treated as false auto-allocations.")
            return
        rule = self.store.get_rule(t.rule_id) if t.rule_id else None
        dlg = CorrectionDialog(self, self.store, t, rule)
        self.wait_window(dlg)
        if not dlg.result:
            return
        account, description, vat, tax_type, pastel_ref, update_rule = dlg.result
        if update_rule and rule:
            if t.amount_condition_applied and rule.amount_operator and rule.amount_account:
                rule.amount_account = account
            else:
                rule.account = account
            rule.description = description
            rule.vat = vat
            rule.tax_type = tax_type
            rule.pastel_ref = pastel_ref
            self.store.save_rule(rule)
            t.manual_override = False
            self.reapply_rules(silent=True)
        t.account = account
        t.description = description
        t.vat = vat
        t.tax_type = tax_type
        t.pastel_ref = pastel_ref
        t.rule_id = rule.id if rule else t.rule_id
        t.rule_name = f"Corrected • {rule.name}" if rule else "Corrected"
        t.status = "Corrected allocation • saved rule updated" if (update_rule and rule) else "Corrected allocation • this statement only"
        t.manual_override = True
        t.auto_allocated = False
        t.ambiguous = False
        self.refresh_transaction_tree(direction)
        self.refresh_recurring_tree(direction)
        self.status_var.set("Correction saved. This row is marked Corrected and is excluded by Select Auto-Allocated until you reset it to the saved rule.")

    def clear_assignment_selected(self, direction: str):
        xs = self.selected_txns(direction)
        if not xs:
            return
        for t in xs:
            t.rule_id = None; t.rule_name = ""; t.account = ""; t.description = ""; t.vat = False; t.tax_type = 0
            t.status = f"Recurring x{t.recurring_count} • unassigned" if t.recurring_count >= 2 else "Unassigned"
            t.manual_override = True; t.ambiguous = False; t.auto_allocated = False; t.amount_condition_applied = False
        self.refresh_transaction_tree(direction)

    def reset_selected_to_rule(self, direction: str):
        xs = self.selected_txns(direction)
        if not xs:
            messagebox.showinfo(APP_NAME, f"Select one or more {self._noun(direction, True)} first.")
            return
        for t in xs:
            t.manual_override = False
        self.reapply_rules(silent=True)

    def _specific_rule_for_key(self, key: str, direction: str) -> Optional[Rule]:
        nk = normalize_text(key)
        candidates = []
        for r in self.store.all_rules(direction):
            if r.enabled and (r.mode or "").upper() == "SMART" and normalize_text(r.pattern) == nk:
                candidates.append(r)
        if not candidates:
            return None
        candidates.sort(key=lambda r: (r.priority, len(normalize_text(r.pattern)), r.id or 0), reverse=True)
        return candidates[0]

    def refresh_recurring_tree(self, direction: str):
        tree = self.recurring_trees.get(direction)
        if not tree:
            return
        txns = self._list(direction)
        open_items = {iid for iid in tree.get_children("") if tree.item(iid, "open")}
        for pid in tree.get_children(""):
            for kid in tree.get_children(pid):
                if tree.item(kid, "open"):
                    open_items.add(kid)
        selected_before = tree.selection()[0] if tree.selection() else ""
        tree.delete(*tree.get_children())
        self.recurring_key_to_indices[direction] = {}
        self.recurring_item_to_index[direction] = {}

        groups: Dict[str, Dict[str, List[int]]] = {}
        for idx, t in enumerate(txns):
            if t.recurring_count < 2:
                continue
            key = smart_key(t.details, t.txn_type)
            if not key:
                continue
            parent = recurring_parent_name(key)
            groups.setdefault(parent, {}).setdefault(key, []).append(idx)
            self.recurring_key_to_indices[direction].setdefault(key, []).append(idx)

        for parent in sorted(groups, key=normalize_text):
            children = groups[parent]
            pid = "grp:" + hashlib.sha1(f"{direction}|{parent}".encode("utf-8")).hexdigest()[:12]
            total_txns = sum(len(v) for v in children.values())
            specific_rules = sum(1 for key in children if self._specific_rule_for_key(key, direction))
            tree.insert(
                "", "end", iid=pid, text=parent, open=(pid in open_items),
                values=("", "", "", f"{len(children)} recurring identities • {total_txns} individual transactions", "", "", "", "", f"{specific_rules}/{len(children)} identity rules"),
                tags=("parent",)
            )

            for key in sorted(children, key=normalize_text):
                idxs = sorted(children[key], key=lambda i: (txns[i].txn_date, txns[i].row_no))
                txs = [txns[i] for i in idxs]
                exact = self._specific_rule_for_key(key, direction)
                kid = "key:" + hashlib.sha1(f"{direction}|{key}".encode("utf-8")).hexdigest()[:12]

                if exact:
                    account = exact.account
                    vat = "VAT" if exact.vat else "No"
                    rule_name = exact.name
                    status = f"Identity rule saved • {len(txs)} transactions"
                    tag = "assigned"
                else:
                    eff_accounts = {t.account for t in txs if t.account}
                    eff_rules = {t.rule_name for t in txs if t.rule_name}
                    account = next(iter(eff_accounts)) if len(eff_accounts) == 1 else ("Multiple" if len(eff_accounts) > 1 else "")
                    vat_values = {"VAT" if t.vat else "No" for t in txs if t.account}
                    vat = next(iter(vat_values)) if len(vat_values) == 1 else ("Mixed" if len(vat_values) > 1 else "")
                    rule_name = next(iter(eff_rules)) if len(eff_rules) == 1 else ("Multiple" if len(eff_rules) > 1 else "")
                    status = f"{len(txs)} individual transactions — expand to manage separately"
                    tag = "mixed" if account else "unassigned"

                total = sum((t.payment_amount for t in txs), Decimal("0.00"))
                tree.insert(
                    pid, "end", iid=kid, text=recurring_child_label(key), open=(kid in open_items),
                    values=("", key, "", f"{len(txs)} individual transactions", f"R {money(total)} total", account, vat, rule_name, status),
                    tags=("identity", tag)
                )

                for idx in idxs:
                    t = txns[idx]
                    tiid = f"txn:{idx}"
                    self.recurring_item_to_index[direction][tiid] = idx
                    txn_tag = "excluded" if not t.include else ("ambiguous" if t.ambiguous else ("corrected" if t.status.startswith("Corrected") else ("assigned" if t.account else "unassigned")))
                    tree.insert(
                        kid, "end", iid=tiid,
                        text=f"{t.txn_date:%d/%m/%Y} • R {money(t.payment_amount)}",
                        values=("☑" if t.include else "☐", key, t.txn_date.strftime("%d/%m/%Y"), t.details,
                                f"R {money(t.payment_amount)}", t.account, "VAT" if t.vat else "No", t.rule_name, t.status),
                        tags=(txn_tag,)
                    )

        if selected_before and tree.exists(selected_before):
            tree.selection_set(selected_before)
            tree.see(selected_before)

    def _selected_recurring_key(self, direction: str, quiet: bool = False) -> Optional[str]:
        tree = self.recurring_trees[direction]
        sel = tree.selection()
        if not sel:
            if not quiet:
                messagebox.showinfo(APP_NAME, "Select a recurring identity or an individual transaction first.")
            return None
        iid = sel[0]
        if iid.startswith("grp:"):
            tree.item(iid, open=not bool(tree.item(iid, "open")))
            if not quiet:
                messagebox.showinfo(APP_NAME, "Expand the name, then select a recurring identity or one individual transaction.")
            return None
        if iid.startswith("txn:"):
            idx = self.recurring_item_to_index[direction].get(iid)
            if idx is None:
                return None
            t = self._list(direction)[idx]
            return smart_key(t.details, t.txn_type)
        key = tree.set(iid, "identity").strip()
        return key or None

    def _selected_recurring_transaction(self, direction: str, quiet: bool = False) -> Optional[Transaction]:
        tree = self.recurring_trees[direction]
        sel = tree.selection()
        if not sel:
            if not quiet:
                messagebox.showinfo(APP_NAME, f"Expand a recurring identity and select one individual {self._noun(direction)} first.")
            return None
        iid = sel[0]
        idx = self.recurring_item_to_index[direction].get(iid)
        if idx is None:
            if not quiet:
                messagebox.showinfo(APP_NAME, f"Select one individual transaction row, not the group or recurring identity.")
            return None
        txns = self._list(direction)
        if idx < 0 or idx >= len(txns):
            return None
        return txns[idx]

    def _selected_recurring_index(self, direction: str) -> Optional[int]:
        tree = self.recurring_trees[direction]
        sel = tree.selection()
        if not sel:
            return None
        return self.recurring_item_to_index[direction].get(sel[0])

    def _recurring_tree_click(self, event, direction: str):
        tree = self.recurring_trees[direction]
        if tree.identify_region(event.x, event.y) == "cell" and tree.identify_column(event.x) == "#1":
            iid = tree.identify_row(event.y)
            idx = self.recurring_item_to_index[direction].get(iid)
            if idx is None:
                return
            txns = self._list(direction)
            txns[idx].include = not txns[idx].include
            self.refresh_transaction_tree(direction)
            self.refresh_recurring_tree(direction)
            if tree.exists(iid):
                tree.selection_set(iid); tree.see(iid)
            return "break"

    def _recurring_tree_double_click(self, event, direction: str):
        tree = self.recurring_trees[direction]
        iid = tree.identify_row(event.y)
        if not iid:
            return
        tree.selection_set(iid)
        if iid.startswith("txn:"):
            self.assign_recurring_transaction_once(direction)
        elif iid.startswith("key:"):
            self.assign_recurring_rule(direction)
        elif iid.startswith("grp:"):
            tree.item(iid, open=not bool(tree.item(iid, "open")))

    def assign_recurring_transaction_once(self, direction: str):
        t = self._selected_recurring_transaction(direction)
        if not t:
            return
        dlg = ManualAssignDialog(self, t, self.store.get_setting("vat_tax_type", ""), self.store.known_accounts())
        self.wait_window(dlg)
        if dlg.result:
            t.account, t.vat, t.tax_type, t.pastel_ref, t.description = dlg.result
            t.rule_id = None
            t.rule_name = "Manual (this file only)"
            t.status = "Manual assignment — individual transaction"
            t.manual_override = True
            t.ambiguous = False
            t.auto_allocated = False
            t.amount_condition_applied = False
            t.match_key = smart_key(t.details, t.txn_type)
            self.refresh_transaction_tree(direction)
            self.refresh_recurring_tree(direction)
            self.status_var.set(f"Assigned only the selected {self._noun(direction)}. Other transactions in the recurring group were not changed.")

    def correct_recurring_auto_allocation(self, direction: str):
        t = self._selected_recurring_transaction(direction)
        if not t:
            return
        self.correct_auto_allocation_selected(direction, t)

    def toggle_recurring_include_selected(self, direction: str):
        idx = self._selected_recurring_index(direction)
        if idx is None:
            messagebox.showinfo(APP_NAME, f"Select one individual {self._noun(direction)} transaction first.")
            return
        t = self._list(direction)[idx]
        t.include = not t.include
        self.refresh_transaction_tree(direction)
        self.refresh_recurring_tree(direction)

    def clear_recurring_transaction_assignment(self, direction: str):
        t = self._selected_recurring_transaction(direction)
        if not t:
            return
        t.rule_id = None
        t.rule_name = ""
        t.account = ""
        t.description = ""
        t.vat = False
        t.tax_type = 0
        t.status = f"Recurring x{t.recurring_count} • unassigned"
        t.manual_override = True
        t.ambiguous = False
        t.auto_allocated = False
        t.amount_condition_applied = False
        self.refresh_transaction_tree(direction)
        self.refresh_recurring_tree(direction)

    def reset_recurring_transaction_to_rule(self, direction: str):
        t = self._selected_recurring_transaction(direction)
        if not t:
            return
        t.manual_override = False
        self.reapply_rules(silent=True)
        self.status_var.set(f"Reset the selected {self._noun(direction)} to its saved-rule result.")

    def set_all_recurring_export(self, direction: str, selected: bool):
        count = 0
        for t in self._list(direction):
            if t.recurring_count >= 2:
                t.include = selected
                count += 1
        self.refresh_transaction_tree(direction)
        self.refresh_recurring_tree(direction)
        self.status_var.set(f"{'Selected' if selected else 'Cleared'} {count} recurring {self._noun(direction, True)} for export.")

    def assign_recurring_rule(self, direction: str):
        key = self._selected_recurring_key(direction)
        if not key:
            return
        idxs = self.recurring_key_to_indices[direction].get(key, [])
        if not idxs:
            return
        txns = self._list(direction)
        selected_idx = self._selected_recurring_index(direction)
        txn = txns[selected_idx] if selected_idx is not None else txns[idxs[0]]
        existing = self._specific_rule_for_key(key, direction)
        dlg = RuleDialog(self, self.store, txn, existing, locked_identity=key)
        dlg.vars["name"].set(existing.name if existing else key)
        self.wait_window(dlg)
        if dlg.result:
            for i in idxs:
                txns[i].manual_override = False
            self.reapply_rules(silent=True)
            self.status_var.set(f"Saved identity rule for {key}. It applies to that identity in future CSV files; each CSV amount remains automatic.")

    def show_recurring_in_transactions(self, direction: str):
        idx = self._selected_recurring_index(direction)
        target_tab = self.receipt_tab if direction == "RECEIPT" else self.pay_tab
        if idx is not None:
            self.search_vars[direction].set("")
            self.filter_vars[direction].set("All")
            self.repeat_vars[direction].set("— Select repeat description —")
            self.notebook.select(target_tab)
            self.refresh_transaction_tree(direction)
            iid = str(idx)
            tree = self.trees[direction]
            if tree.exists(iid):
                tree.selection_set(iid)
                tree.focus(iid)
                tree.see(iid)
            return

        key = self._selected_recurring_key(direction)
        if not key:
            return
        self.update_repeat_dropdown(direction)
        display = next((d for d, k in self.repeat_display_to_key[direction].items() if k == key), None)
        if display:
            self.repeat_vars[direction].set(display)
        self.filter_vars[direction].set("Recurring")
        self.notebook.select(target_tab)
        self.refresh_transaction_tree(direction)

    def set_recurring_expanded(self, direction: str, expanded: bool):
        tree = self.recurring_trees.get(direction)
        if not tree:
            return
        for pid in tree.get_children(""):
            tree.item(pid, open=expanded)
            for kid in tree.get_children(pid):
                tree.item(kid, open=expanded)

    def refresh_rules(self):
        if not hasattr(self, "rule_tree"):
            return
        self.rule_tree.delete(*self.rule_tree.get_children())
        for r in self.store.all_rules():
            amount_rule = f"{r.amount_operator} R {r.amount_threshold} → {r.amount_account}" if (r.amount_operator and r.amount_account) else ""
            self.rule_tree.insert("", "end", iid=str(r.id), values=(r.id, "Receipt" if r.direction == "RECEIPT" else "Payment", r.name, r.mode, r.pattern, r.account, r.description, amount_rule, "Yes" if r.vat else "No", r.tax_type if r.vat else 0, r.pastel_ref, r.priority))

    def edit_rule(self, rule: Optional[Rule], direction: str = "PAYMENT"):
        if rule:
            direction = rule.direction
        if rule is None:
            dlg = RuleDialog(self, self.store, rule=None, direction=direction)
        else:
            dlg = RuleDialog(self, self.store, rule=rule)
        self.wait_window(dlg)
        if dlg.result:
            self.refresh_rules(); self.reapply_rules(silent=True) if (self.txns or self.receipts) else None

    def edit_selected_rule(self):
        sel = self.rule_tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Select a rule first."); return
        r = self.store.get_rule(int(sel[0]))
        if r:
            self.edit_rule(r)

    def delete_selected_rule(self):
        sel = self.rule_tree.selection()
        if not sel:
            return
        rid = int(sel[0]); r = self.store.get_rule(rid)
        if r and messagebox.askyesno(APP_NAME, f"Delete rule '{r.name}'?\n\nFuture statements will no longer use this mapping."):
            self.store.delete_rule(rid); self.refresh_rules()
            if self.txns or self.receipts:
                self.reapply_rules(silent=True)

    def export_rules(self):
        p = filedialog.asksaveasfilename(title="Export rule backup", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="Pastel_Payment_Receipt_Rules_Backup.csv")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["direction", "name", "mode", "pattern", "account", "description", "amount_operator", "amount_threshold", "amount_account", "vat", "tax_type", "pastel_ref", "priority", "enabled"])
            for r in self.store.all_rules():
                w.writerow([r.direction, r.name, r.mode, r.pattern, r.account, r.description, r.amount_operator, r.amount_threshold, r.amount_account, int(r.vat), r.tax_type, r.pastel_ref, r.priority, int(r.enabled)])
        messagebox.showinfo(APP_NAME, f"Rules backup saved:\n{p}")

    def import_rules(self):
        p = filedialog.askopenfilename(title="Import rule backup", filetypes=[("CSV", "*.csv")])
        if not p:
            return
        count = 0
        try:
            with open(p, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    direction = (row.get("direction") or "PAYMENT").strip().upper()
                    if direction not in self.DIRECTIONS:
                        direction = "PAYMENT"
                    r = Rule(None, row.get("name", "").strip(), row.get("mode", "SMART").strip(), row.get("pattern", "").strip(), row.get("account", "").strip(), row.get("vat", "0").strip() in {"1", "true", "True", "yes", "Yes"}, int(row.get("tax_type", "0") or 0), row.get("pastel_ref", "").strip(), int(row.get("priority", "100") or 100), row.get("enabled", "1").strip() not in {"0", "false", "False"}, direction, row.get("description", "").strip(), row.get("amount_operator", "").strip(), row.get("amount_threshold", "").strip(), row.get("amount_account", "").strip())
                    if r.name and r.pattern and r.account:
                        self.store.save_rule(r); count += 1
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not import rules:\n{e}"); return
        self.refresh_rules()
        if self.txns or self.receipts:
            self.reapply_rules(silent=True)
        messagebox.showinfo(APP_NAME, f"Imported {count} rule(s). Older v1.6 backups are treated as Payment rules.")

    def _combined_validation(self):
        settings = self.settings_dict()
        p_selected = any(t.include for t in self.txns)
        r_selected = any(t.include for t in self.receipts)
        if not p_selected and not r_selected:
            return ["Nothing is selected for export. Tick at least one payment or receipt."], [], settings
        errors, warnings = [], []
        if p_selected:
            e, w = validate_export(self.txns, settings, "payments")
            errors.extend(e); warnings.extend(w)
        if r_selected:
            e, w = validate_export(self.receipts, settings, "receipts")
            errors.extend(e); warnings.extend(w)
        # Keep the report concise when shared settings produce identical messages.
        errors = list(dict.fromkeys(errors)); warnings = list(dict.fromkeys(warnings))
        return errors, warnings, settings

    def show_validation(self):
        if not self.txns and not self.receipts:
            messagebox.showinfo(APP_NAME, "Load a bank CSV first."); return
        self.save_settings(quiet=True)
        errors, warnings, _ = self._combined_validation()
        psel = sum(1 for t in self.txns if t.include); rsel = sum(1 for t in self.receipts if t.include)
        passigned = sum(1 for t in self.txns if t.include and t.account); rassigned = sum(1 for t in self.receipts if t.include and t.account)
        text = f"Payments selected: {psel} ({passigned} assigned)\nReceipts selected: {rsel} ({rassigned} assigned)\n\n"
        if errors:
            text += "ERRORS — export is blocked\n• " + "\n• ".join(errors) + "\n\n"
        else:
            text += "No blocking format errors found for the selected rows.\n\n"
        if warnings:
            text += "WARNINGS / checks\n• " + "\n• ".join(warnings)
        messagebox.showinfo("Pastel pre-import validation", text)

    def _write_review(self, path: Path, txns: List[Transaction], settings: Dict[str, str], direction: str):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Source row", "Date", "Bank type", "Bank description/reference", "Pastel description", "Smart/matched key", "Recurring seen count", "Matched rule", "Allocation source", "GL account", "Cash Book bank GL (Pastel column L)", "VAT", "Tax type", "Gross amount", "VAT amount", "Pastel reference", "Pastel period", "Selected for export"])
            rate = D(settings.get("vat_rate", "15")); default_tax = int(settings.get("vat_tax_type", "") or 0); fiscal = int(settings.get("fiscal_start_month", "3"))
            for t in txns:
                tax = int(t.tax_type or default_tax or 0) if t.vat else 0
                allocation_source = "Corrected" if t.status.startswith("Corrected") else ("Auto" if t.auto_allocated else ("Manual" if t.manual_override and t.account else "Unassigned"))
                w.writerow([t.row_no, t.txn_date.strftime("%d/%m/%Y"), t.txn_type, t.details, t.description or t.details, t.match_key, t.recurring_count, t.rule_name, allocation_source, t.account, effective_contra(t, settings), "VAT" if t.vat else "No VAT", tax, money(t.payment_amount), money(calculate_tax(t.payment_amount, t.vat, rate)), t.pastel_ref, period_for_date(t.txn_date, fiscal), "Yes" if t.include else "No"])

    def export_files(self):
        if not self.txns and not self.receipts:
            messagebox.showinfo(APP_NAME, "Load a bank CSV first."); return
        self.save_settings(quiet=True)
        errors, warnings, settings = self._combined_validation()
        if errors:
            messagebox.showerror(APP_NAME, "Export blocked until these issues are fixed:\n\n• " + "\n• ".join(errors)); return
        folder = filedialog.askdirectory(title="Choose folder for Pastel import + review files", initialdir=self.store.get_setting("last_folder", str(Path.home())))
        if not folder:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created = []
        p_rows = list(pastel_rows(self.txns, settings)) if any(t.include for t in self.txns) else []
        r_rows = list(pastel_rows(self.receipts, settings)) if any(t.include for t in self.receipts) else []
        if p_rows:
            path = Path(folder) / f"Pastel_Payments_{stamp}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f, lineterminator="\r\n").writerows(p_rows)
            review = Path(folder) / f"Pastel_Payments_REVIEW_{stamp}.csv"
            self._write_review(review, self.txns, settings, "PAYMENT")
            created.extend([path, review])
        if r_rows:
            path = Path(folder) / f"Pastel_Receipts_{stamp}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f, lineterminator="\r\n").writerows(r_rows)
            review = Path(folder) / f"Pastel_Receipts_REVIEW_{stamp}.csv"
            self._write_review(review, self.receipts, settings, "RECEIPT")
            created.extend([path, review])
        report_path = Path(folder) / f"Pastel_Selected_Transactions_VALIDATION_{stamp}.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"{APP_NAME} {APP_VERSION}\nPre-import validation report\nGenerated: {datetime.now():%Y-%m-%d %H:%M:%S}\nSource: {self.current_file}\n\n")
            f.write(f"Selected payment rows generated: {len(p_rows)}\nSelected receipt rows generated: {len(r_rows)}\n")
            f.write(f"Cash Book bank GL (Pastel column L): {settings.get('contra_account','')}\nVAT tax type: {settings.get('vat_tax_type','')}\nVAT rate: {settings.get('vat_rate','')}%\nFiscal start month: {settings.get('fiscal_start_month','')}\n\n")
            f.write("BLOCKING ERRORS\n" + ("None\n" if not errors else "\n".join("- " + x for x in errors) + "\n"))
            f.write("\nWARNINGS / MANUAL CHECKS\n" + ("None\n" if not warnings else "\n".join("- " + x for x in warnings) + "\n"))
            f.write("\nOnly rows ticked with ☑ were included in the Pastel import files. Import Payments and Receipts into their respective cash-book sides, review, then Update/Process.\n")
        created.append(report_path)
        self.store.set_setting("last_folder", folder)
        msg = f"Created {len(p_rows)} selected Payment row(s) and {len(r_rows)} selected Receipt row(s).\n\n"
        if p_rows:
            msg += f"Payments: Pastel_Payments_{stamp}.csv\n"
        if r_rows:
            msg += f"Receipts: Pastel_Receipts_{stamp}.csv\n"
        msg += f"Validation: {report_path.name}\n\nOnly checked rows were exported. Review each imported Pastel batch before Update/Process."
        if warnings:
            msg += "\n\nWarnings to review:\n• " + "\n• ".join(warnings)
        messagebox.showinfo(APP_NAME, msg)
        try:
            if os.name == "nt": os.startfile(folder)
            elif sys.platform == "darwin": subprocess.Popen(["open", folder])
            else: subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def on_close(self):
        try:
            self.save_settings(quiet=True)
        except Exception:
            pass
        self.destroy()

def self_test(statement_path: Optional[str] = None) -> str:
    assert smart_key("HOLLARD   HOL5910923    260601") == "HOLLARD 0923"
    assert smart_key("HOLLARD HOL5986957 260530") == "HOLLARD 6957"
    assert smart_key("VODACOM 0489030492 B0003783") == "VODACOM 3783"
    assert calculate_tax(Decimal("115.00"), True, Decimal("15")) == Decimal("15.00")

    # Per-reference payment rules remain independent.
    p1 = Transaction(1, date(2026, 8, 1), Decimal("-1200"), "INSURANCE PREMIUM", "HOLLARD HOL5986957 260801")
    p2 = Transaction(2, date(2026, 8, 1), Decimal("-1300"), "INSURANCE PREMIUM", "HOLLARD HOL5910923 260801")
    prules = [
        Rule(1, "HOLLARD 6957", "SMART", "HOLLARD 6957", "7100001", False, 0, direction="PAYMENT"),
        Rule(2, "HOLLARD 0923", "SMART", "HOLLARD 0923", "7100002", True, 1, direction="PAYMENT"),
    ]
    apply_rules([p1, p2], prules, 1)
    assert [p1.account, p2.account] == ["7100001", "7100002"]

    # Receipt and payment rules with the same description must never cross-apply.
    rec = Transaction(3, date(2026, 8, 2), Decimal("2500"), "DEPOSIT", "CLIENT ABC 1234", direction="RECEIPT")
    pay_same = Transaction(4, date(2026, 8, 2), Decimal("-500"), "PAYMENT", "CLIENT ABC 1234", direction="PAYMENT")
    rr = Rule(3, "CLIENT ABC 1234", "SMART", "CLIENT ABC 1234", "4000001", False, 0, direction="RECEIPT")
    apply_rules([rec, pay_same], [rr])
    assert rec.account == "4000001" and pay_same.account == ""

    # Checkbox/export selection: unticked rows are omitted without affecting saved rules.
    p1.include = False
    settings = {"contra_account":"1100000", "project_code":"", "fiscal_start_month":"3", "vat_rate":"15", "vat_tax_type":"1"}
    rows = list(pastel_rows([p1, p2], settings))
    assert len(rows) == 1 and rows[0][6] == "1300.00" and rows[0][11] == "1100000" and len(rows[0]) == 18
    rec.account = "4000001"
    rrows = list(pastel_rows([rec], settings))
    assert len(rrows) == 1 and rrows[0][6] == "2500.00" and rrows[0][11] == "1100000" and len(rrows[0]) == 18

    # Direction-aware persistence and recurrence history.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td) / "test.db")
        oldpay = st.save_rule(Rule(None, "PAY RULE", "SMART", "CLIENT ABC 1234", "5000001", False, 0, direction="PAYMENT"))
        newrec = st.save_rule(Rule(None, "REC RULE", "SMART", "CLIENT ABC 1234", "4000001", False, 0, direction="RECEIPT"))
        assert st.get_rule(oldpay).direction == "PAYMENT"
        assert st.get_rule(newrec).direction == "RECEIPT"
        assert len(st.rules("PAYMENT")) == 1 and len(st.rules("RECEIPT")) == 1
        r1 = Transaction(1, date(2026, 6, 1), Decimal("100"), "DEPOSIT", "CLIENT ABC 1234", source="june.csv", direction="RECEIPT")
        st.remember_transactions([r1]); assert r1.recurring_count == 1
        r2 = Transaction(1, date(2026, 7, 1), Decimal("175"), "DEPOSIT", "CLIENT ABC 1234", source="july.csv", direction="RECEIPT")
        st.remember_transactions([r2]); assert r2.recurring_count == 2
        st.conn.close()

    # v1.11: amount-based allocation, descriptions and auto-allocation state.
    small = Transaction(20, date(2026, 8, 3), Decimal("-450.00"), "DEBIT", "TEST MERCHANT 5555", direction="PAYMENT")
    large = Transaction(21, date(2026, 8, 3), Decimal("-750.00"), "DEBIT", "TEST MERCHANT 5555", direction="PAYMENT")
    amount_rule = Rule(20, "TEST 5555", "SMART", "TEST 5555", "7100001", False, 0, "5555", 100, True, "PAYMENT", "Test payment", "<", "500.00", "7200001")
    apply_rules([small, large], [amount_rule], 0)
    assert small.account == "7200001" and small.amount_condition_applied and small.auto_allocated
    assert large.account == "7100001" and not large.amount_condition_applied and large.auto_allocated
    assert small.description == "Test payment"
    test_settings = {"project_code":"", "fiscal_start_month":"3", "vat_rate":"15", "vat_tax_type":"", "contra_account":""}
    assert list(pastel_rows([small], test_settings))[0][5] == "Test payment"

    out = ["Core rules, descriptions, amount-based allocation, auto-allocation state, selection-only export, VAT and recurrence tests passed."]
    if statement_path:
        payments, receipts, parser = BankCSVParser.load(statement_path)
        assert len(payments) == 294, len(payments)
        assert len(receipts) == 32, len(receipts)
        out.append(f"Parsed {len(payments)} outgoing payments and {len(receipts)} incoming receipts using {parser}.")
    return "\n".join(out)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        p = next((x for x in sys.argv[1:] if x != "--self-test"), None)
        print(self_test(p))
    else:
        App().mainloop()
