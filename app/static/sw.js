/**
 * IPS Operations PWA service worker.
 * Network-first for the Streamlit app; only icons may be cached briefly.
 * Bump SW_CACHE_VERSION when shell/layout changes (must match app.config.APP_VERSION).
 */
const SW_CACHE_VERSION = "ips-pwa-v2.5.0";
const ICON_CACHE = `${SW_CACHE_VERSION}-icons`;

const NEVER_CACHE_PREFIXES = [
  "/_stcore/",
  "/component/",
  "/static/streamlit/",
];

function isNavigation(request) {
  return request.mode === "navigate" || request.destination === "document";
}

function shouldNeverCache(url) {
  if (url.origin !== self.location.origin) return true;
  const path = url.pathname;
  if (NEVER_CACHE_PREFIXES.some((p) => path.startsWith(p))) return true;
  if (path.endsWith(".html")) return true;
  return false;
}

function isIconAsset(url) {
  return /\/app\/static\/icon-\d+\.png$/i.test(url.pathname);
}

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(ICON_CACHE).catch(() => undefined)
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name.startsWith("ips-") || name.startsWith("ips-pwa-"))
          .filter((name) => name !== ICON_CACHE)
          .map((name) => caches.delete(name))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (shouldNeverCache(url)) return;

  if (isNavigation(request)) {
    event.respondWith(
      fetch(request).catch(() => caches.match(request))
    );
    return;
  }

  if (isIconAsset(url)) {
    event.respondWith(
      caches.open(ICON_CACHE).then((cache) =>
        cache.match(request).then(
          (cached) =>
            cached ||
            fetch(request).then((response) => {
              if (response && response.status === 200) {
                cache.put(request, response.clone());
              }
              return response;
            })
        )
      )
    );
    return;
  }

  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
