from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def main(path: str) -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8-sig")

    s = replace_once(s, 'APP_VERSION = "1.11.17"', 'APP_VERSION = "1.11.18"', 'version')

    old = '''        gross = t.payment_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)\n        tax_type = int(t.tax_type or default_tax or 0) if t.vat else 0\n        tax_amount = calculate_tax(gross, t.vat, vat_rate)\n        ref = (t.pastel_ref or derive_pastel_reference(t.details, t.match_key, t.row_no))[:8]\n        desc = re.sub(r"\\s+", " ", (t.description or t.details)).strip()[:36]\n        amount_s = money(gross)\n        contra = effective_contra(t, settings)\n        yield [\n            str(period_for_date(t.txn_date, fiscal_start)),\n            t.txn_date.strftime("%d/%m/%Y"),\n            "G",\n            t.account.strip(),\n            ref,\n            desc,\n            amount_s,\n            str(tax_type),\n            money(tax_amount),\n            "A",\n            project,\n            contra,\n            "1",\n            "1",\n            "1",\n            "0",\n            "0.00",\n            amount_s,\n        ]\n'''

    new = '''        gross = t.payment_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)\n        tax_type = int(t.tax_type or default_tax or 0) if t.vat else 0\n        tax_amount = calculate_tax(gross, t.vat, vat_rate)\n\n        # Sage Pastel cash-book import Amount/Home Amount are the GL-side\n        # debit/credit values (positive = DR, negative = CR). Payments debit the\n        # allocated GL and therefore stay positive. Receipts credit the allocated\n        # GL and therefore must be negative in the import file; Pastel then shows\n        # the corresponding bank movement as a POSITIVE Bank Amount on Receipts.\n        direction = (t.direction or "PAYMENT").upper()\n        signed_gross = -gross if direction == "RECEIPT" else gross\n        signed_tax = (-tax_amount if tax_amount != 0 else tax_amount) if direction == "RECEIPT" else tax_amount\n\n        ref = (t.pastel_ref or derive_pastel_reference(t.details, t.match_key, t.row_no))[:8]\n        desc = re.sub(r"\\s+", " ", (t.description or t.details)).strip()[:36]\n        amount_s = money(signed_gross)\n        tax_amount_s = money(signed_tax)\n        contra = effective_contra(t, settings)\n        yield [\n            str(period_for_date(t.txn_date, fiscal_start)),\n            t.txn_date.strftime("%d/%m/%Y"),\n            "G",\n            t.account.strip(),\n            ref,\n            desc,\n            amount_s,\n            str(tax_type),\n            tax_amount_s,\n            "A",\n            project,\n            contra,\n            "1",\n            "1",\n            "1",\n            "0",\n            "0.00",\n            amount_s,\n        ]\n'''
    s = replace_once(s, old, new, 'direction-aware Pastel cash-book export sign')

    # v1.11.0's original receipt export self-test expected a positive GL-side
    # amount. That expectation is exactly the bug fixed here: Pastel Receipts
    # need a GL credit (negative import Amount/Home Amount) so the bank movement
    # displays positive. Update the legacy test before running the full suite.
    s = replace_once(
        s,
        '    assert len(rrows) == 1 and rrows[0][6] == "2500.00" and rrows[0][11] == "1100000" and len(rrows[0]) == 18\n',
        '    assert len(rrows) == 1 and rrows[0][6] == "-2500.00" and rrows[0][17] == "-2500.00" and rrows[0][11] == "1100000" and len(rrows[0]) == 18\n',
        'legacy receipt sign self-test',
    )

    marker = '    # Receipt and payment rules with the same description must never cross-apply.\n'
    tests = '''    # v1.11.18: Pastel cash-book import signs must make bank receipts positive.\n    sign_settings = {"project_code":"", "fiscal_start_month":"3", "vat_rate":"15", "vat_tax_type":"15", "contra_account":""}\n    sign_payment = Transaction(1118, date(2026, 6, 3), Decimal("-100000.00"), "PAYMENT", "PAYMENT SIGN TEST", direction="PAYMENT")\n    sign_payment.account = "9800000"\n    sign_payment.include = True\n    sign_receipt = Transaction(1119, date(2026, 6, 3), Decimal("100000.00"), "RECEIPT", "RECEIPT SIGN TEST", direction="RECEIPT")\n    sign_receipt.account = "9800000"\n    sign_receipt.include = True\n    prow = list(pastel_rows([sign_payment], sign_settings))[0]\n    rrow = list(pastel_rows([sign_receipt], sign_settings))[0]\n    assert prow[6] == "100000.00" and prow[17] == "100000.00"\n    assert rrow[6] == "-100000.00" and rrow[17] == "-100000.00"\n\n    # VAT/tax follows the same GL-side credit sign for receipts and must not\n    # produce a spurious -0.00 when no VAT applies.\n    vat_receipt = Transaction(1120, date(2026, 6, 4), Decimal("115.00"), "RECEIPT", "VAT RECEIPT SIGN TEST", direction="RECEIPT")\n    vat_receipt.account = "4000000"\n    vat_receipt.include = True\n    vat_receipt.vat = True\n    vat_receipt.tax_type = 15\n    vat_row = list(pastel_rows([vat_receipt], sign_settings))[0]\n    assert vat_row[6] == "-115.00" and vat_row[8] == "-15.00" and vat_row[17] == "-115.00"\n    assert rrow[8] == "0.00"\n\n'''
    s = replace_once(s, marker, tests + marker, 'receipt sign regression tests')

    p.write_text(s, encoding="utf-8")
    print(f"Transformed {p} to v1.11.18 with positive Pastel bank receipts")


if __name__ == "__main__":
    main(sys.argv[1])
