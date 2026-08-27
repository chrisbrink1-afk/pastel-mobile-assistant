CREATE TABLE IF NOT EXISTS autoledger_licence_activations (
    licence_id TEXT PRIMARY KEY,
    customer TEXT NOT NULL DEFAULT '',
    entitlement_fingerprint TEXT NOT NULL,
    licence_status TEXT NOT NULL DEFAULT 'enabled',
    active_device_id TEXT,
    active_components JSONB NOT NULL DEFAULT '{}'::jsonb,
    active_device_name TEXT NOT NULL DEFAULT '',
    active_os TEXT NOT NULL DEFAULT '',
    activated_at TIMESTAMPTZ,
    last_validated_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ,
    transfer_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS autoledger_activation_events (
    id BIGSERIAL PRIMARY KEY,
    licence_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    device_id TEXT NOT NULL DEFAULT '',
    device_name TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS autoledger_activation_events_licence_idx
    ON autoledger_activation_events (licence_id, created_at DESC);
