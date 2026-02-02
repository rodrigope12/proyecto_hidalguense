// Service Worker for Última Milla PWA
const CACHE_NAME = 'ultima-milla-v4';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/static/css/styles.css',
    '/static/js/app.js',
    '/static/js/html2canvas.min.js',
    '/static/img/receipt_bg.jpg',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png'
];

// Install - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('Caching static assets');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Always go to network for API calls (server optimization)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(JSON.stringify({
                    error: 'Sin conexión al servidor',
                    offline: true
                }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // For static assets, try cache first
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request).then((fetchResponse) => {
                // Cache new static resources
                if (fetchResponse.ok && event.request.method === 'GET') {
                    const responseClone = fetchResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return fetchResponse;
            });
        }).catch(() => {
            // Offline fallback for HTML
            if (event.request.headers.get('accept').includes('text/html')) {
                return caches.match('/');
            }
        })
    );
});
