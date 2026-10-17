// Encoding helpers used for Web Push (run: npm test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { base64UrlToBytes, sameBytes } from '../src/utils/encoding.js';

test('base64url keys decode to bytes, with or without padding', () => {
  assert.deepEqual([...base64UrlToBytes('BAEC_-8')], [4, 1, 2, 255, 239]);
  assert.deepEqual([...base64UrlToBytes('AQ')], [1]);
});

test('byte comparison works across ArrayBuffer and Uint8Array', () => {
  const bytes = new Uint8Array([4, 1, 2]);
  assert.equal(sameBytes(bytes.buffer, new Uint8Array([4, 1, 2])), true);
  assert.equal(sameBytes(bytes, new Uint8Array([4, 1, 3])), false);
});
