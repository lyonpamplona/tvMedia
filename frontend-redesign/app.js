/**
 * AdSignage — Protótipo de redesign do painel.
 *
 * Este é um protótipo de UI navegavel: usa dados de exemplo (mock) em memória
 * para demonstrar o novo visual, a navegação mobile-first e o comportamento
 * geral. A estrutura de telas/funções mapeia 1:1 com a API real, de modo que
 * a integração final só troca os dados mock por chamadas `fetch` à API.
 */

(() => {
  "use strict";

  // ----------------------------- Ícones ----------------------------- //
  const ICONS = {
    dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>',
    media: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="14" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 18"/></svg>',
    playlists: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h13M3 12h9M3 18h9"/><circle cx="18" cy="16" r="3"/></svg>',
    screens: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>',
  };

  const NAV = [
    { id: "dashboard", label: "Painel" },
    { id: "media", label: "Mídias" },
    { id: "playlists", label: "Playlists" },
    { id: "screens", label: "Telas" },
  ];

  // ----------------------- Dados de exemplo ------------------------ //
  const store = {
    media: [
      { id: 1, name: "Promoção de Verão", type: "image" },
      { id: 2, name: "Vídeo institucional", type: "video" },
      { id: 3, name: "Playlist Lo-fi", type: "embed" },
      { id: 4, name: "Ofertas (YouTube)", type: "youtube" },
      { id: 5, name: "Aviso de horário", type: "text" },
    ],
    playlists: [
      { id: 1, name: "Vitrine principal", items: 6 },
      { id: 2, name: "Faixa de música", items: 3 },
      { id: 3, name: "Promoções do dia", items: 4 },
    ],
    screens: [
      {
        id: 1, name: "TV Entrada", slug: "tv-entrada", online: true,
        timezone: "America/Sao_Paulo",
        zones: [
          { name: "Principal", x: 0, y: 0, width: 100, height: 80 },
          { name: "Rodapé", x: 0, y: 80, width: 100, height: 20 },
        ],
      },
      {
        id: 2, name: "TV Caixa", slug: "tv-caixa", online: false,
        timezone: "America/Sao_Paulo",
        zones: [{ name: "Principal", x: 0, y: 0, width: 100, height: 100 }],
      },
    ],
  };

  // --------------------------- Estado ------------------------------ //
  let current = "dashboard";
  const view = document.getElementById("view");
  const toastEl = document.getElementById("toast");

  /**
   * Exibe uma notificação temporária.
   * @param {string} msg Mensagem a exibir.
   */
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), 2200);
  }

  /**
   * Escapa texto para uso seguro em HTML.
   * @param {unknown} v Valor.
   * @returns {string} Texto escapado.
   */
  function esc(v) {
    const d = document.createElement("div");
    d.textContent = v == null ? "" : String(v);
    return d.innerHTML;
  }

  const TYPE_LABEL = {
    image: "Imagem", video: "Vídeo", text: "Texto",
    html: "HTML", url: "URL", youtube: "YouTube", embed: "Música",
  };

  // -------------------------- Telas (views) ------------------------ //

  /** @returns {string} HTML do painel inicial. */
  function renderDashboard() {
    const online = store.screens.filter((s) => s.online).length;
    return `
      <div class="hero">
        <h2>Bem-vindo de volta 👋</h2>
        <p>Gerencie mídias, playlists e telas — as alterações aparecem na hora.</p>
      </div>
      <div class="stats">
        <div class="stat"><div class="n">${store.screens.length}</div><div class="l">Telas</div></div>
        <div class="stat"><div class="n">${online}</div><div class="l"><b>online</b> agora</div></div>
        <div class="stat"><div class="n">${store.playlists.length}</div><div class="l">Playlists</div></div>
        <div class="stat"><div class="n">${store.media.length}</div><div class="l">Mídias</div></div>
      </div>
      <div class="section-title"><h3>Telas</h3><button class="btn small ghost" data-go="screens">Ver todas</button></div>
      <div class="cards">
        ${store.screens.map((s) => `
          <div class="card">
            <div class="row between"><h4>${esc(s.name)}</h4>
              <span class="pill ${s.online ? "online" : "offline"}">${s.online ? "online" : "offline"}</span>
            </div>
            <div class="zone-preview">
              ${s.zones.map((z) => `<div class="zone-box" style="left:${z.x}%;top:${z.y}%;width:${z.width}%;height:${z.height}%">${esc(z.name)}</div>`).join("")}
            </div>
            <div class="meta">${s.zones.length} zona(s) · ${esc(s.timezone)}</div>
          </div>`).join("")}
      </div>`;
  }

  /** @returns {string} HTML da galeria de mídias. */
  function renderMedia() {
    return `
      <div class="page-head"><h1>Mídias</h1><p>Imagens, vídeos, YouTube, música e blocos de texto.</p></div>
      <div class="cards">
        ${store.media.map((m) => `
          <div class="card">
            <div class="thumb">${esc(TYPE_LABEL[m.type] || m.type)}</div>
            <h4>${esc(m.name)}</h4>
            <div class="row between"><span class="pill">${esc(TYPE_LABEL[m.type] || m.type)}</span>
              <button class="btn small ghost" data-toast="Protótipo: abriria a mídia">Abrir</button></div>
          </div>`).join("")}
      </div>`;
  }

  /** @returns {string} HTML da lista de playlists. */
  function renderPlaylists() {
    return `
      <div class="page-head"><h1>Playlists</h1><p>Sequências de mídia reproduzidas em loop.</p></div>
      <div class="cards">
        ${store.playlists.map((p) => `
          <div class="card">
            <div class="row between"><h4>${esc(p.name)}</h4><span class="pill">${p.items} itens</span></div>
            <div class="meta">Toque para editar itens, duração, ajuste e transição.</div>
            <button class="btn small block" data-toast="Protótipo: abriria o editor">Editar playlist</button>
          </div>`).join("")}
      </div>`;
  }

  /** @returns {string} HTML da lista de telas. */
  function renderScreens() {
    return `
      <div class="page-head"><h1>Telas</h1><p>Cada TV exibe o player por um link público.</p></div>
      <div class="cards">
        ${store.screens.map((s) => `
          <div class="card">
            <div class="row between"><h4>${esc(s.name)}</h4>
              <span class="pill ${s.online ? "online" : "offline"}">${s.online ? "online" : "offline"}</span></div>
            <div class="zone-preview">
              ${s.zones.map((z) => `<div class="zone-box" style="left:${z.x}%;top:${z.y}%;width:${z.width}%;height:${z.height}%">${esc(z.name)}</div>`).join("")}
            </div>
            <div class="code">/player/?screen=${esc(s.slug)}</div>
            <div class="row">
              <button class="btn small grow" data-toast="Link copiado (protótipo)">Copiar link</button>
              <button class="btn small ghost" data-toast="Protótipo: gerenciaria zonas">Zonas</button>
            </div>
          </div>`).join("")}
      </div>`;
  }

  const VIEWS = {
    dashboard: renderDashboard,
    media: renderMedia,
    playlists: renderPlaylists,
    screens: renderScreens,
  };

  // --------------------------- Navegação -------------------------- //

  /**
   * Troca a tela ativa e re-renderiza navegação + conteúdo.
   * @param {string} id Identificador da tela (ver NAV).
   */
  function navigate(id) {
    current = id;
    view.innerHTML = (VIEWS[id] || renderDashboard)();
    renderNav();
    bindViewEvents();
    view.focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /** Renderiza a barra inferior (mobile) e a lateral (desktop). */
  function renderNav() {
    const bottom = document.getElementById("bottom-nav");
    bottom.innerHTML = NAV.map((n) => `
      <button class="nav-item ${n.id === current ? "active" : ""}" data-nav="${n.id}">
        ${ICONS[n.id]}<span>${n.label}</span>
      </button>`).join("");

    const side = document.getElementById("sidebar");
    side.innerHTML = `
      <div class="side-brand"><span class="brand-mark">A</span> AdSignage</div>
      ${NAV.map((n) => `
        <button class="side-item ${n.id === current ? "active" : ""}" data-nav="${n.id}">
          ${ICONS[n.id]}<span>${n.label}</span>
        </button>`).join("")}`;

    document.querySelectorAll("[data-nav]").forEach((b) =>
      b.addEventListener("click", () => navigate(b.dataset.nav)));
  }

  /** Liga eventos dos botões internos da tela atual. */
  function bindViewEvents() {
    view.querySelectorAll("[data-go]").forEach((b) =>
      b.addEventListener("click", () => navigate(b.dataset.go)));
    view.querySelectorAll("[data-toast]").forEach((b) =>
      b.addEventListener("click", () => toast(b.dataset.toast)));
  }

  // ----------------------- Tema (claro/escuro) --------------------- //
  const THEME_KEY = "adsignage_theme";
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem(THEME_KEY, t);
  }
  document.getElementById("theme-btn").addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
  });
  applyTheme(localStorage.getItem(THEME_KEY) || "dark");

  document.getElementById("menu-btn").addEventListener("click", () => {
    const i = NAV.findIndex((n) => n.id === current);
    navigate(NAV[(i + 1) % NAV.length].id);
  });

  // ------------------ PWA: instalação + service worker ------------- //
  let deferredPrompt = null;
  const installHint = document.getElementById("install-hint");
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installHint.hidden = false;
  });
  installHint.addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    installHint.hidden = true;
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("sw.js").catch(() => {
        /* protótipo: ignora falha de registro (ex.: aberto via file://) */
      });
    });
  }

  // ---------------------------- Bootstrap -------------------------- //
  navigate("dashboard");
})();
