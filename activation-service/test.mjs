import fs from 'node:fs';
import crypto from 'node:crypto';
import { _test } from './api/index.js';

process.env.ALLOW_INMEMORY_ACTIVATION = '1';
const pair = crypto.generateKeyPairSync('rsa', {modulusLength: 3072});
process.env.ACTIVATION_PRIVATE_KEY_PEM = pair.privateKey.export({type:'pkcs8', format:'pem'}).toString();
process.env.ACTIVATION_ADMIN_API_KEY = 'test-admin-secret';

const key = fs.readFileSync('../autoledger-r8/testdata/R6_SAMPLE_ENTITLEMENT_KEY.txt', 'utf8').trim();
const devA = {
  device_id: 'a'.repeat(64),
  components: {system_uuid:'1'.repeat(64),baseboard:'2'.repeat(64),bios:'3'.repeat(64)},
  device_name:'PC-A', os:'Windows 11', architecture:'AMD64'
};
const devAMinor = {
  device_id: 'b'.repeat(64),
  components: {system_uuid:'1'.repeat(64),baseboard:'2'.repeat(64),bios:'9'.repeat(64)},
  device_name:'PC-A-REFRESHED', os:'Windows 11', architecture:'AMD64'
};
const devB = {
  device_id: 'c'.repeat(64),
  components: {system_uuid:'4'.repeat(64),baseboard:'5'.repeat(64),bios:'6'.repeat(64)},
  device_name:'PC-B', os:'Windows 11', architecture:'AMD64'
};

const first = await _test.activate({licence_key:key, device:devA, app_version:'R8 TEST'});
if (!first.activation_token.startsWith('ALA225A1.')) throw new Error('Activation token prefix failed');
const tokenPayload = _test.verifyActivationToken(first.activation_token);
if (tokenPayload.device_id !== devA.device_id) throw new Error('Token device mismatch');
const days = (new Date(tokenPayload.valid_until)-new Date(tokenPayload.issued_at))/86400000;
if (days < 89.9 || days > 90.1) throw new Error(`Expected 90-day certificate, got ${days}`);

let secondBlocked = false;
try { await _test.activate({licence_key:key, device:devB, app_version:'R8 TEST'}); }
catch (e) { secondBlocked = e.status === 409; }
if (!secondBlocked) throw new Error('Second PC was not blocked');

const tolerant = await _test.activate({licence_key:key, device:devAMinor, app_version:'R8 TEST'});
if (!_test.verifyActivationToken(tolerant.activation_token)) throw new Error('Tolerant hardware refresh failed');

await _test.deactivate({licence_key:key, activation_token:tolerant.activation_token, device:devAMinor});
const afterTransfer = await _test.activate({licence_key:key, device:devB, app_version:'R8 TEST'});
if (_test.verifyActivationToken(afterTransfer.activation_token).device_id !== devB.device_id) throw new Error('Transfer activation failed');

const req = {headers:{'x-autoledger-admin-key':'test-admin-secret'}};
const statusBefore = await _test.adminStatus(req, {licence_id: tokenPayload.license_id});
if (!statusBefore.active) throw new Error('Admin status did not report active device');
await _test.adminReset(req, {licence_id: tokenPayload.license_id, reason:'dead PC test'});
const statusAfter = await _test.adminStatus(req, {licence_id: tokenPayload.license_id});
if (statusAfter.active) throw new Error('Admin reset did not release device');
const afterAdminReset = await _test.activate({licence_key:key, device:devA, app_version:'R8 TEST'});
if (_test.verifyActivationToken(afterAdminReset.activation_token).device_id !== devA.device_id) throw new Error('Reactivation after admin reset failed');

console.log('PASS: R8 activation service tests');
console.log(`events=${_test.memoryEvents.length}`);
