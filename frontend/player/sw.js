// Service worker do player de sinalizacao tvMedia.
// Estrategia: cache-first para o app shell e midias (resiliencia offline),
// network-first para chamadas dinamicas /api/ (com fallback ao cache).
const CACHE = "tvmedia-player-v1";
const SHELL = ["./", "./index.html", "./player.js"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch (e) { return; }

  // Conteudo dinamico: rede primeiro; se offline, usa a ultima resposta em cache.
  if (url.pathname.indexOf("/api/") === 0) {
    event.respondWith(
      fetch(req)
        .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return res; })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Midias e estaticos: cache primeiro; busca na rede e armazena quando ausente.
  if (
    url.pathname.indexOf("/media/") === 0 ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".html") ||
    url.pathname.endsWith("/")
  ) {
    event.respondWith(
      caches.match(req).then((hit) => {
        if (hit) return hit;
        return fetch(req)
          .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return res; })
          .catch(() => hit);
      })
    );
  }
});
