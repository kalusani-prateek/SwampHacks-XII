// Re-run a callback on an interval. Used to refresh live data (alerts,
// lightning status) until the planned Server-Sent Events stream exists.
import { useEffect, useRef } from 'react';

/**
 * @param {() => void} callback  function to run every `intervalMs`
 * @param {number|null} intervalMs  polling period; pass null to pause
 */
export function usePolling(callback, intervalMs) {
  const saved = useRef(callback);

  // Always call the latest callback without restarting the timer.
  useEffect(() => {
    saved.current = callback;
  });

  useEffect(() => {
    if (intervalMs == null) return undefined;
    const id = setInterval(() => saved.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}
