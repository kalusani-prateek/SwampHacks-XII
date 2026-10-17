// This device's notification status, shared by the navbar bell and the account
// page so turning notifications on in one place updates the other.
import { useEffect, useState } from 'react';
import { disablePush, enablePush, getPushStatus, pushUnavailableReason } from '../api/push.js';

let shared = 'checking'; // 'checking' | 'on' | 'off' | 'blocked' | 'unavailable'
const listeners = new Set();
const publish = (status) => {
  shared = status;
  listeners.forEach((listener) => listener(status));
};

export function usePushNotifications() {
  const [status, setStatus] = useState(shared);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    listeners.add(setStatus);
    getPushStatus().then(publish, () => publish('off')); // re-check: permission may have changed, or someone signed out
    return () => listeners.delete(setStatus);
  }, []);

  async function run(action) {
    setBusy(true);
    setError('');
    try {
      publish(await action());
    } catch (err) {
      setError(err.message);
      publish(await getPushStatus().catch(() => 'off'));
    } finally {
      setBusy(false);
    }
  }

  return {
    status,
    busy,
    error,
    reason: pushUnavailableReason(),
    enable: () => run(enablePush),
    disable: () => run(disablePush),
  };
}
