# AUTOLEDGER Pro activation service (R8)

This service enforces the default **one active PC per Pro licence** rule without receiving bank or accounting data.

## What is stored

- licence ID and customer label from the signed entitlement;
- SHA-256 fingerprint of the signed entitlement key (not the raw key);
- hashed device identity/components;
- device name / OS label for support diagnostics;
- activation, validation, deactivation and reset timestamps;
- transfer count and minimal activation event history.

It does **not** receive bank statements, transaction descriptions, account mappings, allocations, VAT data, exports, or company-profile accounting databases.

## Required production environment variables

- `DATABASE_URL` — PostgreSQL/Neon-compatible connection string.
- `ACTIVATION_PRIVATE_KEY_PEM` — private RSA activation-certificate signing key. Never commit it to source control.
- `ACTIVATION_ADMIN_API_KEY` — long random secret used by the internal support reset utility. Never commit it to source control.

For local automated tests only, set `ALLOW_INMEMORY_ACTIVATION=1` instead of `DATABASE_URL`.

## Endpoints

- `GET /health`
- `POST /v1/activate`
- `POST /v1/validate`
- `POST /v1/deactivate`
- `POST /v1/admin/status` (requires `X-AUTOLEDGER-ADMIN-KEY`)
- `POST /v1/admin/reset` (requires `X-AUTOLEDGER-ADMIN-KEY`)

## Certificate policy

A successful activation receives a signed device certificate valid for 90 days. The desktop application begins background refresh attempts at 30 days. This provides approximately 60 days of offline grace without making normal bookkeeping dependent on continuous internet access.

## Hardware tolerance

The server compares hashed SMBIOS system UUID, baseboard serial and BIOS serial. Exact device IDs match immediately; otherwise at least two matching stable hardware components are required. RAM, SSD, GPU, monitors and peripherals are not part of the fingerprint. A motherboard/new-PC change normally requires transfer/reset.

## Recommended production hostname

`https://api.autoledgersystems.co.za`

The DNS hostname can point to a Vercel deployment. A managed PostgreSQL/Neon database is sufficient; no dedicated physical server is required.
