from pathlib import Path
import importlib.machinery, importlib.util, sys

HERE = Path(__file__).resolve().parent
APP = HERE / "pastel_payment_assistant.pyw"
loader = importlib.machinery.SourceFileLoader("ppa", str(APP))
spec = importlib.util.spec_from_loader(loader.name, loader)
ppa = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ppa
loader.exec_module(ppa)

statement = HERE.parent / "statement-05-177-526-3.csv"
if not statement.exists():
    statement = Path('/mnt/data/statement-05-177-526-3.csv')

print(ppa.self_test(str(statement) if statement.exists() else None))

# Validation only considers checked rows. An unassigned but unticked row must not block export.
from decimal import Decimal
from datetime import date
assigned = ppa.Transaction(90, date(2026,8,1), Decimal('-100'), 'PAYMENT', 'A 1234')
assigned.account = '5000001'
unselected = ppa.Transaction(91, date(2026,8,1), Decimal('-200'), 'PAYMENT', 'B 5678')
unselected.include = False
settings = {"contra_account":"1100000", "project_code":"", "fiscal_start_month":"3", "vat_rate":"15", "vat_tax_type":"1"}
errors, _ = ppa.validate_export([assigned, unselected], settings, 'payments')
assert not errors, errors

# Upgrade safety: a v1.6 database without direction columns must migrate existing rules to PAYMENT.
import sqlite3
from tempfile import TemporaryDirectory
with TemporaryDirectory() as td:
    db = Path(td) / 'legacy.db'
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE rules (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,mode TEXT NOT NULL DEFAULT 'SMART',pattern TEXT NOT NULL,account TEXT NOT NULL,vat INTEGER NOT NULL DEFAULT 0,tax_type INTEGER NOT NULL DEFAULT 0,pastel_ref TEXT NOT NULL DEFAULT '',priority INTEGER NOT NULL DEFAULT 100,enabled INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE transaction_history (signature TEXT PRIMARY KEY,txn_date TEXT NOT NULL,match_key TEXT NOT NULL,details TEXT NOT NULL,amount TEXT NOT NULL,source_name TEXT NOT NULL DEFAULT '',first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    INSERT INTO rules(name,mode,pattern,account) VALUES('Old HOLLARD','SMART','HOLLARD 6957','7100001');
    """)
    con.commit(); con.close()
    migrated = ppa.Store(db)
    old = migrated.all_rules()[0]
    assert old.direction == 'PAYMENT'
# v1.9 retains v1.8 individual recurring handling and adds per-transaction contra overrides.
# A one-off manual override must survive rule reapplication on that transaction only.
rule = ppa.Rule(50, "AXXESS recurring", "SMART", "AXXESS", "6100000", False, 0, direction="PAYMENT")
a = ppa.Transaction(101, date(2026,8,1), Decimal('-899'), 'DEBIT TRANSFER', 'AXXESS', direction='PAYMENT')
b = ppa.Transaction(102, date(2026,8,12), Decimal('-1250'), 'DEBIT TRANSFER', 'AXXESS', direction='PAYMENT')
a.recurring_count = b.recurring_count = 2
a.account = '6200000'; a.vat = True; a.tax_type = 1; a.rule_name = 'Manual (this file only)'; a.manual_override = True
ppa.apply_rules([a,b], [rule], 1)
assert a.account == '6200000' and a.vat is True and a.manual_override is True
assert b.account == '6100000' and b.vat is False and b.manual_override is False
# Export selection is also individual even inside the same recurring identity.
a.include = False; b.include = True
rows = list(ppa.pastel_rows([a,b], settings))
assert len(rows) == 1 and rows[0][6] == '1250.00'

# v1.9: each selected transaction can export a different contra.
c1 = ppa.Transaction(201, date(2026,8,20), Decimal('-10'), 'PAYMENT', 'TEST ONE', direction='PAYMENT')
c2 = ppa.Transaction(202, date(2026,8,20), Decimal('-20'), 'PAYMENT', 'TEST TWO', direction='PAYMENT')
c1.account = c2.account = '5000001'
c1.contra = '2100000'
c2.contra = '3100000'
cr = list(ppa.pastel_rows([c1,c2], settings))
assert cr[0][11] == '2100000' and cr[1][11] == '3100000'
# Individual contra permits export even when no default is configured.
no_default = dict(settings); no_default['contra_account'] = ''
errors, _ = ppa.validate_export([c1,c2], no_default, 'payments')
assert not errors, errors
# Clearing an override with no default must block export for that row.
c2.contra = ''
errors, _ = ppa.validate_export([c1,c2], no_default, 'payments')
assert any('no contra account' in e.lower() for e in errors), errors

print("PASS: v1.9 individual recurring transactions, receipts, per-row contra overrides, export selection, date sorting, changing amounts and 18-column Pastel export.")
