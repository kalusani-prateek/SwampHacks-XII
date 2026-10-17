// Offline support for crews at remote sites with poor signal.
// The service worker (public/sw.js) keeps the app and the last data each page
// loaded, so pages still open offline with the most recent saved readings.
// Only registered in production builds, so it never caches stale dev code.

export const API_CACHE = 'planit-api-v1';

export function registerOfflineSupport() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* offline support is optional; the app works without it */
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
