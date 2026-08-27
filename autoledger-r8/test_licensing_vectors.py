from pathlib import Path
from license_crypto import decode_and_verify_key
from activation_crypto import decode_and_verify_activation

root = Path(__file__).resolve().parent / 'testdata'
key = (root / 'R6_SAMPLE_ENTITLEMENT_KEY.txt').read_text(encoding='utf-8').strip()
entitlement = decode_and_verify_key(key)
assert entitlement['license_id'] == 'R6TEST446168C5'
assert entitlement['version'] == '2.2.5'

token = (root / 'R8_ACTIVATION_TEST_VECTOR.txt').read_text(encoding='utf-8').strip()
activation = decode_and_verify_activation(token)
assert activation['license_id'] == entitlement['license_id']
assert activation['device_id'] == 'a' * 64
assert activation['certificate_version'] == 1
print('PASS: permanent R6 entitlement + R8 activation signature vectors')
