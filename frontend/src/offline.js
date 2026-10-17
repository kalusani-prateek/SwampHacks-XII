// The service worker (public/sw.js) does two jobs:
//   - offline support for crews at remote sites with poor signal: it keeps the
//     app and the last data each page loaded (production builds only, so it
//     never caches stale dev code);
//   - phone and desktop notifications (Web Push), in every build.
// In development it's registered as /sw.js?dev, which tells it to skip caching.

export const API_CACHE = 'planit-api-v1';

export function registerOfflineSupport() {
  if (!('serviceWorker' in navigator)) return;
  const script = import.meta.env.PROD ? '/sw.js' : '/sw.js?dev';
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(script).catch(() => {
      /* offline support and notifications are optional; the app works without them */
    });
  });
}

/** Remove saved API data (called on sign-out so the next person on a shared device starts clean). */
export async function clearOfflineData() {
  try {
    if ('caches' in window) await caches.delete(API_CACHE);
  } catch {
    /* ignore */
  }
}
