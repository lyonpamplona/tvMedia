/**
 * AdSignage — Service Worker (PWA do protótipo de redesign).
 *
 * Estratégia:
 *  - Estáticos do app (HTML/CSS/JS/ícones): cache-first (funciona offline).
 *  - Chamadas à API (`/api/...`): network-first, com fallback ao cache.
 */

const CACHE = "adsignage-redesign-v1";
const ASSETS = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

// Pré-cache dos estáticos na instalação.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

// Limpa caches antigos ao ativar.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Intercepta requisições GET.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  // network-first para a API.
  if (request.url.includes("/api/")) {
    event.respondWith(fetch(request).catch(() => caches.match(request)));
    return;
  }

  // cache-first para o restante.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match("./index.html"));
    })
  );
});
