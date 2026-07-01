// Service worker do player de sinalizacao tvMedia.
// Estrategia: network-first para o app shell (.js/.css/.html) e /api/ para
// sempre pegar a versao mais recente; cache-first para /media/ (offline).
const CACHE = "tvmedia-player-v18";
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

  // Midias: cache primeiro (resiliencia offline para arquivos grandes).
  if (url.pathname.indexOf("/media/") === 0) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return res; }))
    );
    return;
  }

  // App shell (.js/.css/.html e navegacao): REDE PRIMEIRO para sempre pegar a
  // versao mais recente apos um deploy; usa o cache apenas se estiver offline.
  if (
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".html") ||
    url.pathname.endsWith("/")
  ) {
    event.respondWith(
      fetch(req)
        .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return res; })
        .catch(() => caches.match(req))
    );
  }
});

// v34: pre-cache offline de midias sob demanda (mensagem do player).
self.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.type === "precache" && Array.isArray(data.urls) && data.urls.length) {
    event.waitUntil(
      caches.open(CACHE).then((c) => Promise.all(
        data.urls.map((u) => c.match(u).then((hit) => hit || fetch(u).then((res) => c.put(u, res)).catch(() => {})))
      ))
    );
  }
});
