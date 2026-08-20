# Pastel Mobile Assistant

Android companion app for Sage Pastel Accounting workflows.

## Included functionality

- Load bank CSV statements.
- Detect recurring payment identities such as `HOLLARD 6957`, `VODACOM 3783`, and similar stable reference patterns.
- Reuse saved GL/VAT assignments while always taking the current amount from the newly loaded CSV.
- Photograph invoices and run OCR on-device with ML Kit.
- Choose Supplier or Customer for invoice exports.
- Generate Sage Pastel-ready CSV files for bank payments and supplier/customer document imports.
- Share/email generated Pastel files using the Android share sheet.
- Keep a review-first workflow before any final Update/Process in Pastel.

## Android source

The complete Android Studio project is stored in:

`Pastel_Mobile_Assistant_Android_v0.1.zip`

## APK build

GitHub Actions builds a debug APK automatically. On the `main` branch the workflow also publishes a stable release named `mobile-latest` containing:

`Pastel-Mobile-Assistant.apk`

The APK is intended for testing and internal use. Always review generated Sage Pastel batches before processing them.
