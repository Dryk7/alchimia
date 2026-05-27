// Service Worker — FOULÉE (idle-tap mobile)
// v56 : identités PNJ (noms, drapeaux, dossards visibles, personnalités)
const CACHE = 'foulee-v56';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './assets/icon-192.png',
  './assets/icon-192-maskable.png',
  './assets/icon-512.png',
  './assets/icon-maskable-512.png',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // network-first pour HTML, cache-first pour assets statiques
  const req = e.request;
  const url = new URL(req.url);
  if(url.origin !== location.origin) return;
  if(req.method !== 'GET') return;
  const isHtml = req.mode === 'navigate' || (req.headers.get('accept')||'').includes('text/html');
  if(isHtml){
    e.respondWith(
      fetch(req).then(r => {
        const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp));
        return r;
      }).catch(() => caches.match(req).then(r => r || caches.match('./index.html')))
    );
  } else {
    e.respondWith(
      caches.match(req).then(cached => cached || fetch(req).then(r => {
        const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp));
        return r;
      }))
    );
  }
});
