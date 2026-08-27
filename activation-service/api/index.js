import crypto from 'node:crypto';

const ENTITLEMENT_PREFIX = 'ALP225R6';
const ACTIVATION_PREFIX = 'ALA225A1';
const PRODUCT = 'AUTOLEDGER';
const EDITION = 'PRO';
const ENTITLEMENT_VERSION = '2.2.5';
const TOKEN_REFRESH_DAYS = 30;
const TOKEN_VALID_DAYS = 90;

const ENTITLEMENT_PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAttQJslP5++imNbFNdIy1
rP9QoQDBBuzI82d4x0Fk7G7KCnw9kudGmhs3OLFBSrZu5BbYrWhQg5ANwGOrQWXQ
XgY5qHmxs6xtocjyBY7BEWm4/mzEcG7EJrr1yRVyuZUabW2Ymq98R0rRmO4G0xRG
et7kUeXHb55xU3neJmKEEiCXOPqwbG5fjhOt4vSNMzQWbFFMl7C0Oqyvtptkk5H4
Iu5p1OKgZQaYKzE4VsT/YiEOpR0JchhnNEunVgAXI2B9tNkove9LQOfHF05hgXDV
t8ZUyf8HShHG4UlOseiXUoZROvOacHM6GCGBEnXCfbGQQ2WFO/ljesYZOLN/wDZM
wQIDAQAB
-----END PUBLIC KEY-----`;

let pool;
let PoolClass;
let schemaReady = false;
const memoryRows = new Map();
const memoryEvents = [];

function json(res, status, body) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}

function b64urlDecode(value) {
  return Buffer.from(String(value || '').replace(/-/g, '+').replace(/_/g, '/'), 'base64');
}

function b64urlEncode(buffer) {
  return Buffer.from(buffer).toString('base64url');
}

function sha256Text(value) {
  return crypto.createHash('sha256').update(String(value || ''), 'utf8').digest('hex');
}

function safeText(value, max = 256) {
  return String(value || '').replace(/[\u0000-\u001f\u007f]/g, '').slice(0, max);
}

function verifyEntitlement(key) {
  const clean = String(key || '').replace(/\s+/g, '');
  const parts = clean.split('.');
  if (parts.length !== 3 || parts[0] !== ENTITLEMENT_PREFIX) {
    throw Object.assign(new Error('This is not a valid AUTOLEDGER Pro licence key.'), { status: 400 });
  }
  const payloadBytes = b64urlDecode(parts[1]);
  const signature = b64urlDecode(parts[2]);
  const ok = crypto.verify('RSA-SHA256', payloadBytes, ENTITLEMENT_PUBLIC_KEY, signature);
  if (!ok) throw Object.assign(new Error('The AUTOLEDGER Pro licence signature is invalid.'), { status: 400 });
  let payload;
  try { payload = JSON.parse(payloadBytes.toString('utf8')); }
  catch { throw Object.assign(new Error('The AUTOLEDGER Pro licence payload is invalid.'), { status: 400 }); }
  if (payload.product !== PRODUCT || payload.edition !== EDITION || payload.version !== ENTITLEMENT_VERSION) {
    throw Object.assign(new Error('This licence was issued for a different AUTOLEDGER product or edition.'), { status: 400 });
  }
  if (!payload.license_id) throw Object.assign(new Error('The AUTOLEDGER Pro licence has no licence ID.'), { status: 400 });
  if (payload.expires) {
    const expiry = new Date(`${payload.expires}T23:59:59Z`);
    if (!Number.isFinite(expiry.getTime()) || Date.now() > expiry.getTime()) {
      throw Object.assign(new Error(`This AUTOLEDGER Pro licence expired on ${payload.expires}.`), { status: 403 });
    }
  }
  return { key: clean, payload, fingerprint: sha256Text(clean) };
}

function activationPrivateKey() {
  const raw = process.env.ACTIVATION_PRIVATE_KEY_PEM || '';
  if (!raw) throw Object.assign(new Error('Activation signing key is not configured.'), { status: 503 });
  return raw.replace(/\\n/g, '\n');
}

function makeActivationToken(entitlement, device) {
  const now = new Date();
  const refresh = new Date(now.getTime() + TOKEN_REFRESH_DAYS * 86400000);
  const valid = new Date(now.getTime() + TOKEN_VALID_DAYS * 86400000);
  const payload = {
    product: PRODUCT,
    edition: EDITION,
    license_id: entitlement.license_id,
    device_id: device.device_id,
    issued_at: now.toISOString(),
    refresh_after: refresh.toISOString(),
    valid_until: valid.toISOString(),
    certificate_version: 1
  };
  const bytes = Buffer.from(JSON.stringify(payload), 'utf8');
  const signature = crypto.sign('RSA-SHA256', bytes, activationPrivateKey());
  return `${ACTIVATION_PREFIX}.${b64urlEncode(bytes)}.${b64urlEncode(signature)}`;
}

function verifyActivationToken(token) {
  const parts = String(token || '').replace(/\s+/g, '').split('.');
  if (parts.length !== 3 || parts[0] !== ACTIVATION_PREFIX) {
    throw Object.assign(new Error('The AUTOLEDGER device activation token is invalid.'), { status: 400 });
  }
  const bytes = b64urlDecode(parts[1]);
  const sig = b64urlDecode(parts[2]);
  const publicKey = crypto.createPublicKey(activationPrivateKey());
  if (!crypto.verify('RSA-SHA256', bytes, publicKey, sig)) {
    throw Object.assign(new Error('The AUTOLEDGER device activation signature is invalid.'), { status: 400 });
  }
  let payload;
  try { payload = JSON.parse(bytes.toString('utf8')); }
  catch { throw Object.assign(new Error('The AUTOLEDGER activation payload is invalid.'), { status: 400 }); }
  return payload;
}

function cleanComponents(value) {
  const src = value && typeof value === 'object' ? value : {};
  const out = {};
  for (const k of ['system_uuid', 'baseboard', 'bios']) {
    const v = String(src[k] || '').toLowerCase();
    if (/^[0-9a-f]{64}$/.test(v)) out[k] = v;
  }
  return out;
}

function cleanDevice(raw) {
  const d = raw && typeof raw === 'object' ? raw : {};
  const id = String(d.device_id || '').toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(id)) {
    throw Object.assign(new Error('The device identity is invalid.'), { status: 400 });
  }
  return {
    device_id: id,
    components: cleanComponents(d.components),
    device_name: safeText(d.device_name, 120),
    os: safeText(d.os, 180),
    architecture: safeText(d.architecture, 32)
  };
}

function hardwareMatches(saved, current) {
  if (!saved || !current) return false;
  if (saved.active_device_id && saved.active_device_id === current.device_id) return true;
  const a = saved.active_components || {};
  const b = current.components || {};
  let comparable = 0;
  let matches = 0;
  for (const k of ['system_uuid', 'baseboard', 'bios']) {
    if (a[k] && b[k]) {
      comparable += 1;
      if (a[k] === b[k]) matches += 1;
    }
  }
  return comparable >= 2 && matches >= 2;
}

async function ensureSchema(client) {
  if (schemaReady) return;
  await client.query(`
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
  `);
  schemaReady = true;
}

function memoryMode() {
  return !process.env.DATABASE_URL && process.env.ALLOW_INMEMORY_ACTIVATION === '1';
}

async function withLockedLicence(licenceId, fn) {
  if (memoryMode()) {
    return await fn({
      get: async () => memoryRows.get(licenceId) || null,
      put: async row => { memoryRows.set(licenceId, structuredClone(row)); },
      event: async (type, device, details = {}) => memoryEvents.push({ licence_id: licenceId, event_type: type, device_id: device?.device_id || '', device_name: device?.device_name || '', details, created_at: new Date().toISOString() })
    });
  }
  if (!process.env.DATABASE_URL) {
    throw Object.assign(new Error('Activation database is not configured.'), { status: 503 });
  }
  if (!PoolClass) {
    const mod = await import('pg');
    PoolClass = mod.default?.Pool || mod.Pool;
  }
  pool ||= new PoolClass({ connectionString: process.env.DATABASE_URL, ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : undefined, max: 3 });
  const client = await pool.connect();
  try {
    await ensureSchema(client);
    await client.query('BEGIN');
    await client.query('SELECT pg_advisory_xact_lock(hashtext($1))', [licenceId]);
    const api = {
      get: async () => {
        const r = await client.query('SELECT * FROM autoledger_licence_activations WHERE licence_id=$1', [licenceId]);
        return r.rows[0] || null;
      },
      put: async row => {
        await client.query(`
          INSERT INTO autoledger_licence_activations
            (licence_id, customer, entitlement_fingerprint, licence_status, active_device_id,
             active_components, active_device_name, active_os, activated_at, last_validated_at,
             deactivated_at, transfer_count, updated_at)
          VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10,$11,$12,NOW())
          ON CONFLICT (licence_id) DO UPDATE SET
            customer=EXCLUDED.customer,
            entitlement_fingerprint=EXCLUDED.entitlement_fingerprint,
            licence_status=EXCLUDED.licence_status,
            active_device_id=EXCLUDED.active_device_id,
            active_components=EXCLUDED.active_components,
            active_device_name=EXCLUDED.active_device_name,
            active_os=EXCLUDED.active_os,
            activated_at=EXCLUDED.activated_at,
            last_validated_at=EXCLUDED.last_validated_at,
            deactivated_at=EXCLUDED.deactivated_at,
            transfer_count=EXCLUDED.transfer_count,
            updated_at=NOW()
        `, [row.licence_id, row.customer || '', row.entitlement_fingerprint, row.licence_status || 'enabled', row.active_device_id || null,
             JSON.stringify(row.active_components || {}), row.active_device_name || '', row.active_os || '', row.activated_at || null,
             row.last_validated_at || null, row.deactivated_at || null, Number(row.transfer_count || 0)]);
      },
      event: async (type, device, details = {}) => {
        await client.query('INSERT INTO autoledger_activation_events (licence_id,event_type,device_id,device_name,details) VALUES ($1,$2,$3,$4,$5::jsonb)',
          [licenceId, type, device?.device_id || '', device?.device_name || '', JSON.stringify(details)]);
      }
    };
    const result = await fn(api);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    try { await client.query('ROLLBACK'); } catch {}
    throw err;
  } finally {
    client.release();
  }
}

function baseRow(ent, device, previous = null) {
  const now = new Date().toISOString();
  return {
    licence_id: ent.payload.license_id,
    customer: safeText(ent.payload.customer, 180),
    entitlement_fingerprint: ent.fingerprint,
    licence_status: previous?.licence_status || 'enabled',
    active_device_id: device?.device_id || null,
    active_components: device?.components || {},
    active_device_name: device?.device_name || '',
    active_os: device?.os || '',
    activated_at: device ? (previous?.activated_at || now) : null,
    last_validated_at: device ? now : null,
    deactivated_at: device ? null : now,
    transfer_count: Number(previous?.transfer_count || 0)
  };
}

async function activate(body) {
  const ent = verifyEntitlement(body.licence_key);
  const device = cleanDevice(body.device);
  return withLockedLicence(ent.payload.license_id, async db => {
    let row = await db.get();
    if (row && row.entitlement_fingerprint !== ent.fingerprint) {
      throw Object.assign(new Error('The licence ID is already registered to a different entitlement.'), { status: 409 });
    }
    if (row?.licence_status === 'disabled') {
      throw Object.assign(new Error('This AUTOLEDGER Pro licence is disabled. Contact AUTOLEDGER support.'), { status: 403 });
    }
    if (row?.active_device_id && !hardwareMatches(row, device)) {
      await db.event('activation_blocked_second_pc', device, { app_version: safeText(body.app_version, 80) });
      throw Object.assign(new Error('This AUTOLEDGER Pro licence is already activated on another PC. Deactivate/transfer the existing PC or contact AUTOLEDGER support for an activation reset.'), { status: 409 });
    }
    const changedIdentity = !!row?.active_device_id && row.active_device_id !== device.device_id;
    const next = baseRow(ent, device, row);
    if (changedIdentity) next.transfer_count = Number(row.transfer_count || 0);
    await db.put(next);
    await db.event(row?.active_device_id ? (changedIdentity ? 'hardware_identity_refreshed' : 'activation_refreshed') : 'activated', device,
      { app_version: safeText(body.app_version, 80) });
    return { activation_token: makeActivationToken(ent.payload, device), status: 'active' };
  });
}

async function validate(body) {
  const ent = verifyEntitlement(body.licence_key);
  const device = cleanDevice(body.device);
  const token = verifyActivationToken(body.activation_token);
  if (token.license_id !== ent.payload.license_id) throw Object.assign(new Error('Activation token and licence do not match.'), { status: 400 });
  return withLockedLicence(ent.payload.license_id, async db => {
    const row = await db.get();
    if (!row || !row.active_device_id) throw Object.assign(new Error('This licence does not currently have an active PC.'), { status: 409 });
    if (row.licence_status === 'disabled') throw Object.assign(new Error('This AUTOLEDGER Pro licence is disabled.'), { status: 403 });
    if (!hardwareMatches(row, device)) throw Object.assign(new Error('This licence is active on another PC.'), { status: 409 });
    const next = baseRow(ent, device, row);
    next.activated_at = row.activated_at;
    next.transfer_count = Number(row.transfer_count || 0);
    await db.put(next);
    await db.event('validated', device, { app_version: safeText(body.app_version, 80) });
    return { activation_token: makeActivationToken(ent.payload, device), status: 'active' };
  });
}

async function deactivate(body) {
  const ent = verifyEntitlement(body.licence_key);
  const device = cleanDevice(body.device);
  const token = verifyActivationToken(body.activation_token);
  if (token.license_id !== ent.payload.license_id) throw Object.assign(new Error('Activation token and licence do not match.'), { status: 400 });
  return withLockedLicence(ent.payload.license_id, async db => {
    const row = await db.get();
    if (!row?.active_device_id) return { status: 'already_deactivated' };
    if (!hardwareMatches(row, device)) throw Object.assign(new Error('This PC is not the active device for this licence.'), { status: 409 });
    const next = baseRow(ent, null, row);
    next.transfer_count = Number(row.transfer_count || 0) + 1;
    await db.put(next);
    await db.event('deactivated_for_transfer', device, { transfer_count: next.transfer_count });
    return { status: 'deactivated' };
  });
}

function validAdminKey(req) {
  const expected = process.env.ACTIVATION_ADMIN_API_KEY || '';
  const supplied = String(req.headers['x-autoledger-admin-key'] || '');
  if (!expected || supplied.length !== expected.length) return false;
  return crypto.timingSafeEqual(Buffer.from(supplied), Buffer.from(expected));
}

async function adminReset(req, body) {
  if (!validAdminKey(req)) throw Object.assign(new Error('Administrative authentication failed.'), { status: 401 });
  const licenceId = safeText(body.licence_id, 160);
  if (!licenceId) throw Object.assign(new Error('licence_id is required.'), { status: 400 });
  return withLockedLicence(licenceId, async db => {
    const row = await db.get();
    if (!row) throw Object.assign(new Error('Licence ID was not found in the activation registry.'), { status: 404 });
    const next = { ...row, active_device_id: null, active_components: {}, active_device_name: '', active_os: '', activated_at: null,
      last_validated_at: null, deactivated_at: new Date().toISOString(), transfer_count: Number(row.transfer_count || 0) + 1 };
    await db.put(next);
    await db.event('admin_activation_reset', null, { reason: safeText(body.reason, 300), transfer_count: next.transfer_count });
    return { status: 'reset', licence_id: licenceId, transfer_count: next.transfer_count };
  });
}

async function adminStatus(req, body) {
  if (!validAdminKey(req)) throw Object.assign(new Error('Administrative authentication failed.'), { status: 401 });
  const licenceId = safeText(body.licence_id, 160);
  if (!licenceId) throw Object.assign(new Error('licence_id is required.'), { status: 400 });
  return withLockedLicence(licenceId, async db => {
    const row = await db.get();
    if (!row) throw Object.assign(new Error('Licence ID was not found in the activation registry.'), { status: 404 });
    return {
      licence_id: row.licence_id,
      customer: row.customer,
      licence_status: row.licence_status,
      active: !!row.active_device_id,
      active_device_name: row.active_device_name || '',
      activated_at: row.activated_at || null,
      last_validated_at: row.last_validated_at || null,
      transfer_count: Number(row.transfer_count || 0)
    };
  });
}

async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') {
    try { return JSON.parse(req.body); } catch { return {}; }
  }
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  if (!chunks.length) return {};
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { return {}; }
}

export async function handle(req, res) {
  try {
    const pathname = new URL(req.url, 'https://local.invalid').pathname;
    if (req.method === 'GET' && (pathname === '/health' || pathname === '/v1/health')) {
      return json(res, 200, { status: 'ok', service: 'AUTOLEDGER activation', certificate_days: TOKEN_VALID_DAYS });
    }
    if (req.method !== 'POST') return json(res, 405, { detail: 'Method not allowed.' });
    const body = await readBody(req);
    let result;
    if (pathname === '/v1/activate') result = await activate(body);
    else if (pathname === '/v1/validate') result = await validate(body);
    else if (pathname === '/v1/deactivate') result = await deactivate(body);
    else if (pathname === '/v1/admin/reset') result = await adminReset(req, body);
    else if (pathname === '/v1/admin/status') result = await adminStatus(req, body);
    else return json(res, 404, { detail: 'Not found.' });
    return json(res, 200, result);
  } catch (err) {
    console.error('AUTOLEDGER activation error:', err?.stack || err);
    return json(res, Number(err?.status || 500), { detail: safeText(err?.message || 'Activation service error.', 500) });
  }
}

export default handle;
export const _test = { verifyEntitlement, verifyActivationToken, cleanDevice, hardwareMatches, activate, validate, deactivate, adminReset, adminStatus, memoryRows, memoryEvents };
