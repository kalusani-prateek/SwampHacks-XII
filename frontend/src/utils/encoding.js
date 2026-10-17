// Small encoding helpers.

/** base64url text (no padding, - and _) -> bytes, e.g. the Web Push server key. */
export function base64UrlToBytes(value) {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4);
  return Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
}

/** True when two byte sequences (ArrayBuffer or typed array) hold the same bytes. */
export function sameBytes(a, b) {
  const x = new Uint8Array(a instanceof ArrayBuffer ? a : a.buffer);
  const y = new Uint8Array(b instanceof ArrayBuffer ? b : b.buffer);
  return x.length === y.length && x.every((byte, i) => byte === y[i]);
}
