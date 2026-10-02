const CACHE = 'workout-pwa-v5';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon.png',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      Promise.all(ASSETS.map((url) =>
        cache.add(new Request(url, { cache: 'reload' })).catch((e) => console.warn('SW precache failed', url, e))
      ))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  let fromV1 = false;
  const activation = (async () => {
    const keys = await caches.keys();
    // Pages loaded from the v1 cache have no controllerchange reload handler,
    // so they are reloaded once from here. Newer pages reload themselves.
    fromV1 = keys.includes('workout-pwa-v1');
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })();
  event.waitUntil(activation);
  // Must run AFTER activation finishes: awaiting a navigation inside
  // waitUntil would deadlock (the navigation's fetch waits for activation).
  activation.then(async () => {
    if (!fromV1) return;
    const wins = await self.clients.matchAll({ type: 'window' });
    wins.forEach((c) => c.navigate(c.url).catch(() => {}));
  });
});

// Cache-first, then update the cache from the network in the background.
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  const isCdn = url.hostname === 'cdn.jsdelivr.net';
  if (!sameOrigin && !isCdn) return;

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(req, { ignoreSearch: sameOrigin });
      const network = fetch(req).then((res) => {
        if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
        return res;
      }).catch(() => undefined);
      if (cached) {
        event.waitUntil(network);
        return cached;
      }
      const res = await network;
      if (res) return res;
      if (req.mode === 'navigate') {
        const fallback = await cache.match('./index.html');
        if (fallback) return fallback;
      }
      return Response.error();
    })
  );
});
