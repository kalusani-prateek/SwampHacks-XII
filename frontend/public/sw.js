// PlanIT Control service worker.
// Offline support (production builds):
//   - Page loads: network first, fall back to the saved app shell.
//   - Built assets (/assets/*): cache first (their names change on every build).
//   - API reads (GET /api/*): network first, fall back to the last saved response.
//   Writes (POST/PUT/PATCH/DELETE) always need the network.
// Notifications (every build): shows Web Push messages from the backend and opens
// the right page when one is tapped. Registered as /sw.js?dev in development,
// where it skips all caching.
const SHELL_CACHE = 'planit-shell-v1';
const API_CACHE = 'planit-api-v1';
const DEV = new URL(self.location.href).searchParams.has('dev');

// Offline caching is best-effort: where storage is unavailable (private windows, a full
// disk) the worker must still install, so notifications and normal page loads keep working.
async function openCache(name) {
  try {
    return await caches.open(name);
  } catch {
    return null;
  }
}

self.addEventListener('install', (event) => {
  if (!DEV) event.waitUntil(openCache(SHELL_CACHE).then((cache) => cache?.add('/')).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => ![SHELL_CACHE, API_CACHE].includes(k)).map((k) => caches.delete(k))))
      .catch(() => {})
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(request, cacheName, fallbackUrl) {
  const cache = await openCache(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok && cache) cache.put(fallbackUrl ?? request, response.clone()).catch(() => {});
    return response;
  } catch (err) {
    const cached = cache && (await cache.match(fallbackUrl ?? request).catch(() => null));
    if (cached) return cached;
    throw err;
  }
}

async function cacheFirst(request) {
  const cache = await openCache(SHELL_CACHE);
  const cached = cache && (await cache.match(request).catch(() => null));
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok && cache) cache.put(request, response.clone()).catch(() => {});
  return response;
}

self.addEventListener('fetch', (event) => {
  if (DEV) return; // development: always the network
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  // Live streams and photos are not cached.
  if (url.pathname === '/api/alerts/stream' || url.pathname.startsWith('/api/uploads/')) return;

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, SHELL_CACHE, '/'));
  } else if (url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirst(request));
  } else if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, API_CACHE));
  }
});

// A notification from the backend: { title, body, url, tag }.
self.addEventListener('push', (event) => {
  let message = {};
  try {
    message = event.data ? event.data.json() : {};
  } catch {
    message = { body: event.data?.text() };
  }
  event.waitUntil(
    self.registration.showNotification(message.title || 'PlanIT Control', {
      body: message.body || '',
      icon: '/icons/icon-192.png',
      badge: '/icons/badge-72.png',
      tag: message.tag || undefined,
      renotify: Boolean(message.tag), // a newer message with the same tag still alerts
      data: { url: message.url || '/' },
    }),
  );
});

// Tapping a notification opens the app on the page it's about (reusing an open window if there is one).
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || '/', self.location.origin).href;
  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      const open = windows.find((client) => new URL(client.url).origin === self.location.origin);
      if (open) {
        await open.focus();
        try {
          return await open.navigate(target);
        } catch {
          /* that window isn't controlled by this worker: open a new one */
        }
      }
      return self.clients.openWindow(target);
    })(),
  );
});
