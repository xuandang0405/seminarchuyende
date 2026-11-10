/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches, createHandlerBoundToURL } from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import { NetworkFirst, CacheFirst } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: any[] };

self.addEventListener('install', event => { event.waitUntil(self.skipWaiting()); });
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();
registerRoute(new NavigationRoute(createHandlerBoundToURL('/index.html'), {
  allowlist: [/^\/client(?:\/|$)/, /^\/tourist(?:\/|$)/, /^\/$/],
}));
// Cache only public data. Orders, credentials, grants and analytics never enter runtime caches.
registerRoute(({ url }) => url.origin === self.location.origin && url.pathname === '/api/v1/pois',
  new NetworkFirst({ cacheName: 'tourvoice-public-pois', networkTimeoutSeconds: 8,
    plugins: [new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 900, purgeOnQuotaError: true })] }));
registerRoute(({ url }) => url.origin === self.location.origin && url.pathname.startsWith('/storage/images/'),
  new CacheFirst({ cacheName: 'tourvoice-public-images', plugins: [new ExpirationPlugin({ maxEntries: 100,
    maxAgeSeconds: 604800, purgeOnQuotaError: true })] }));
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
