/* Minimal service worker: caches only PWA static assets.
   Intentionally does NOT cache Streamlit pages/API to avoid stale app updates. */

const CACHE = "ips-pwa-static-v2";
const ASSETS = [
  "/.streamlit/static/manifest.json",
  "/.streamlit/static/icon-192.png",
  "/.streamlit/static/icon-512.png",
  "/.streamlit/static/icons/icon-32.png",
  "/.streamlit/static/icons/icon-72.png",
  "/.streamlit/static/icons/icon-96.png",
  "/.streamlit/static/icons/icon-128.png",
  "/.streamlit/static/icons/icon-144.png",
  "/.streamlit/static/icons/icon-152.png",
  "/.streamlit/static/icons/icon-180.png",
  "/.streamlit/static/icons/icon-192.png",
  "/.streamlit/static/icons/icon-384.png",
  "/.streamlit/static/icons/icon-512.png",
  "/.streamlit/static/icons/icon-192-maskable.png",
  "/.streamlit/static/icons/icon-512-maskable.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).catch(() => {}));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;

  // Only handle our PWA static assets.
  if (!url.pathname.startsWith("/.streamlit/static/")) return;

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(event.request);
      const fetchPromise = fetch(event.request)
        .then((resp) => {
          if (resp && resp.ok) cache.put(event.request, resp.clone());
          return resp;
        })
        .catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
