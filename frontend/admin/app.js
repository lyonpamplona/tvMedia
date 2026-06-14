/**
 * tvMedia Studio - painel de edicao profissional (estilo IDE) para
 * sinalizacao digital, conectado a API real do backend.
 *
 * Layout: barra de titulo + menu, barra de atividades, explorer em arvore,
 * editor com documentos por secao (canvas de telas/zonas arrastaveis,
 * biblioteca de midias, editor de playlists, tabela de agendamentos),
 * inspetor de propriedades contextual, painel inferior (linha do tempo,
 * saida e problemas), barra de status, paleta de comandos (Ctrl+K) e toasts.
 *
 * Todos os icones sao SVG (sem emojis). As alteracoes sao aplicadas ao vivo:
 * o player consome /api/display/{slug} e reage via WebSocket no backend.
 */
(() => {
  "use strict";

  // ----------------------------- Icones SVG ------------------------ //
  const S = (p, vb) => "<svg viewBox=\"" + (vb || "0 0 24 24") + "\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">" + p + "</svg>";
  const ICONS = {
    logo: S('<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M7 20h10M9 16v4M15 16v4M7 9h4"/>'),
    layout: S('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>'),
    media: S('<rect x="3" y="4" width="18" height="14" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 18"/>'),
    playlist: S('<path d="M3 6h13M3 12h9M3 18h9"/><circle cx="18" cy="16" r="3"/>'),
    screen: S('<rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>'),
    clock: S('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    search: S('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
    settings: S('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
    chevron: S('<path d="m6 9 6 6 6-6"/>'),
    plus: S('<path d="M12 5v14M5 12h14"/>'),
    refresh: S('<path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6"/>'),
    close: S('<path d="M18 6 6 18M6 6l12 12"/>'),
    image: S('<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>'),
    video: S('<rect x="2" y="5" width="14" height="14" rx="2"/><path d="m16 9 6-3v12l-6-3"/>'),
    text: S('<path d="M4 6h16M4 12h16M4 18h10"/>'),
    code: S('<path d="m8 6-6 6 6 6M16 6l6 6-6 6"/>'),
    link: S('<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>'),
    youtube: S('<rect x="2" y="5" width="20" height="14" rx="4"/><path d="m10 9 5 3-5 3z" fill="currentColor" stroke="none"/>'),
    music: S('<circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/><path d="M9 18V5l12-2v13"/>'),
    timeline: S('<path d="M3 12h18M6 8v8M12 6v12M18 9v6"/>'),
    terminal: S('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/>'),
    alert: S('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>'),
    check: S('<path d="M20 6 9 17l-5-5"/>'),
    info: S('<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>'),
    eye: S('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>'),
    copy: S('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
    trash: S('<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>'),
    sun: S('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M5 5l1.5 1.5M17.5 17.5 19 19M2 12h2M20 12h2M5 19l1.5-1.5M17.5 6.5 19 5"/>'),
    branch: S('<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 8.5v7M18 10.5c0 3-4 2.5-4 6.5"/>'),
    wifi: S('<path d="M5 12a10 10 0 0 1 14 0M8.5 15.5a5 5 0 0 1 7 0M12 19h.01"/>'),
    up: S('<path d="m18 15-6-6-6 6"/>'),
    down: S('<path d="m6 9 6 6 6-6"/>'),
    power: S('<path d="M12 2v10M18.4 6.6a9 9 0 1 1-12.8 0"/>'),
    upload: S('<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>'),
    folder: S('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    user: S('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
    shield: S('<path d="M12 3 4 6v6c0 5 3.5 7.5 8 9 4.5-1.5 8-4 8-9V6z"/>'),
    lock: S('<rect x="4" y="11" width="16" height="9" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
    tag: S('<path d="M3 3h8l10 10-8 8L3 11z"/><circle cx="7.5" cy="7.5" r="1.5" fill="currentColor" stroke="none"/>'),
  };

  const TYPE_ICON = { image: "image", video: "video", text: "text", html: "code", url: "link", youtube: "youtube", embed: "music", audio: "music", clock: "clock", weather: "sun", news: "text", promo: "tag", countdown: "clock", qrcode: "layout", rates: "tag", live: "video" };
  const TYPE_LABEL = { image: "Imagem", video: "Video", text: "Texto", html: "HTML", url: "URL", youtube: "YouTube", embed: "Embed", audio: "Audio", clock: "Relogio", weather: "Clima", news: "Noticias", promo: "Promocoes", countdown: "Contagem", qrcode: "QR Code", rates: "Cotacoes", live: "Ao vivo (HLS)" };
  const WIDGET_TYPES = ["clock", "weather", "news", "promo", "countdown", "qrcode", "rates"];
  // Modelos prontos de conteudo para acelerar a criacao de textos/cartazes.
  const MEDIA_TEMPLATES = {
    promo: { label: "Promocao", text: "OFERTA ESPECIAL\n50% OFF\nSomente hoje. Aproveite!", html: '<div style="text-align:center;color:#fff;font-family:system-ui"><div style="font-size:3vmin;letter-spacing:.3em;color:#7aa2f7">OFERTA ESPECIAL</div><div style="font-size:12vmin;font-weight:800;line-height:1">50% OFF</div><div style="font-size:3.5vmin;margin-top:2vmin">Somente hoje. Aproveite!</div></div>' },
    cardapio: { label: "Cardapio", text: "CARDAPIO DO DIA\nPrato executivo - R$ 25\nMassa da casa - R$ 30\nSobremesa - R$ 12", html: '<div style="color:#fff;font-family:system-ui;text-align:center"><div style="font-size:6vmin;font-weight:800;margin-bottom:3vmin">Cardapio do dia</div><div style="font-size:4vmin;line-height:1.8"><div>Prato executivo &mdash; R$ 25</div><div>Massa da casa &mdash; R$ 30</div><div>Sobremesa &mdash; R$ 12</div></div></div>' },
    aviso: { label: "Aviso", text: "AVISO IMPORTANTE\nEscreva aqui a sua mensagem.", html: '<div style="text-align:center;color:#fff;font-family:system-ui"><div style="font-size:9vmin">&#9888;</div><div style="font-size:6vmin;font-weight:800;margin:2vmin 0">Aviso importante</div><div style="font-size:3.6vmin">Escreva aqui a sua mensagem.</div></div>' },
  };
  // Layouts iniciais oferecidos no assistente de nova tela (zonas em % da tela).
  const SCREEN_LAYOUTS = {
    full: { label: "1 zona (tela cheia)", zones: [{ name: "Principal", x: 0, y: 0, width: 100, height: 100 }] },
    split: { label: "2 zonas (lado a lado)", zones: [{ name: "Esquerda", x: 0, y: 0, width: 50, height: 100 }, { name: "Direita", x: 50, y: 0, width: 50, height: 100 }] },
    triptico: { label: "3 zonas (banner + 2 colunas)", zones: [{ name: "Banner", x: 0, y: 0, width: 100, height: 60 }, { name: "Inferior esq.", x: 0, y: 60, width: 50, height: 40 }, { name: "Inferior dir.", x: 50, y: 60, width: 50, height: 40 }] },
  };
  const FITS = ["cover", "contain", "fill"];
  const FIT_LABELS = { cover: "Preencher tela", contain: "Ajustar (sem cortes)", fill: "Esticar" };
  const FOCALS = ["center", "top", "bottom", "left", "right"];
  const FOCAL_LABELS = { center: "Foco: centro", top: "Foco: topo", bottom: "Foco: base", left: "Foco: esq.", right: "Foco: dir." };
  const TRANSITIONS = ["none", "fade", "slide"];
  const DAYS = ["S", "T", "Q", "Q", "S", "S", "D"];
  const DAYS_FULL = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"];

  // ------------------------------ Estado --------------------------- //
  const TOKEN_KEY = "adsignage_token";
  let token = localStorage.getItem(TOKEN_KEY);
  let isDragging = false;

  const state = {
    media: [],
    playlists: [],
    screens: [],
    folders: [],
    users: [],
    user: null,
    mediaQuery: "",
    mediaFolder: "all",
    activeSection: "screens",
    activeScreenId: null,
    selectedZoneId: null,
    selectedMediaId: null,
    openPlaylistId: null,
    bottomTab: "timeline",
    activeCompanyId: null,
    companies: [],
    branding: null,
  };

  const $ = (id) => document.getElementById(id);
  const screen = () => state.screens.find((s) => s.id === state.activeScreenId) || null;
  const zone = () => { const s = screen(); return s ? s.zones.find((z) => z.id === state.selectedZoneId) || null : null; };
  const playlistById = (id) => state.playlists.find((p) => p.id === id) || null;
  const mediaById = (id) => state.media.find((m) => m.id === id) || null;
  const esc = (v) => { const d = document.createElement("div"); d.textContent = v == null ? "" : String(v); return d.innerHTML; };
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const isOnline = (s) => !!(s.last_seen && (Date.now() - new Date(s.last_seen).getTime() < 60000));
  const minToHHMM = (m) => String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
  const hhmmToMin = (v) => { const parts = (v || "0:0").split(":").map(Number); return (parts[0] || 0) * 60 + (parts[1] || 0); };
  const playerUrl = (slug) => location.origin + "/player/?screen=" + slug;

  // ------------------------------- API ----------------------------- //
  /**
   * Wrapper de fetch que injeta o token e trata 401 (sessao expirada).
   * @param {string} path Caminho relativo da API.
   * @param {RequestInit} [options] Opcoes do fetch.
   * @returns {Promise<any>} Corpo JSON (ou null em 204).
   */
  async function api(path, options) {
    options = options || {};
    const headers = options.headers ? Object.assign({}, options.headers) : {};
    if (token) headers["Authorization"] = "Bearer " + token;
    if (state.activeCompanyId != null) headers["X-Company-Id"] = String(state.activeCompanyId);
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    const resp = await fetch(path, Object.assign({}, options, { headers }));
    if (resp.status === 401) { logout(); throw new Error("Sessao expirada. Entre novamente."); }
    if (!resp.ok) {
      let detail = "Erro " + resp.status;
      try { const j = await resp.json(); detail = j.detail || detail; } catch (e) { /* ignore */ }
      throw new Error(detail);
    }
    return resp.status === 204 ? null : resp.json();
  }

  async function loadMedia() { state.media = await api("/api/media"); }
  async function loadPlaylists() { state.playlists = await api("/api/playlists"); }
  async function loadScreens() { state.screens = await api("/api/screens"); }

  // Endpoints novos (analytics, folders, users, auditoria, importacao em massa).
  async function loadHealth() { return api("/api/analytics/screens/health"); }
  async function loadProofOfPlay(days, screenSlug) {
    const qs = new URLSearchParams();
    if (days) qs.set("days", String(days));
    if (screenSlug) qs.set("screen", screenSlug);
    return api("/api/analytics/proof-of-play?" + qs.toString());
  }
  async function previewScreen(id) { return api("/api/screens/" + id + "/preview"); }
  async function bulkImportMedia(items) { return api("/api/media/bulk", { method: "POST", body: JSON.stringify({ items }) }); }
  async function loadFolders() { return api("/api/folders"); }
  async function loadUsers() { return api("/api/users"); }
  async function createUser(data) { return api("/api/users", { method: "POST", body: JSON.stringify(data) }); }
  async function loadAudit(limit) { return api("/api/audit?limit=" + (limit || 100)); }
  async function changePassword(currentPassword, newPassword) {
    const j = await api("/api/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
    if (j && j.token) { token = j.token; localStorage.setItem(TOKEN_KEY, token); }
    return j;
  }

  // ----- Multi-empresa (multi-tenant): branding, empresas e templates ----- //
  async function loadBranding() { return api("/api/branding"); }
  async function loadMe() { return api("/api/auth/me"); }
  async function loadTemplates() { try { return await api("/api/templates"); } catch (e) { return []; } }
  async function loadCompanies() { return api("/api/companies"); }
  async function createCompany(data) { return api("/api/companies", { method: "POST", body: JSON.stringify(data) }); }
  async function updateCompany(id, data) { return api("/api/companies/" + id, { method: "PATCH", body: JSON.stringify(data) }); }
  async function deleteCompany(id) { return api("/api/companies/" + id, { method: "DELETE" }); }
  async function uploadCompanyLogo(id, file) { const fd = new FormData(); fd.append("file", file); return api("/api/companies/" + id + "/logo", { method: "POST", body: fd }); }

  // Le as dimensoes (px) de imagem/video no navegador antes do upload.
  function readMediaDims(file, kind) {
    return new Promise((resolve) => {
      try {
        if (kind === "image") { const img = new Image(); const u = URL.createObjectURL(file); img.onload = () => { resolve({ width: img.naturalWidth, height: img.naturalHeight }); URL.revokeObjectURL(u); }; img.onerror = () => { resolve(null); URL.revokeObjectURL(u); }; img.src = u; }
        else if (kind === "video") { const v = document.createElement("video"); const u = URL.createObjectURL(file); v.onloadedmetadata = () => { resolve({ width: v.videoWidth, height: v.videoHeight }); URL.revokeObjectURL(u); }; v.onerror = () => { resolve(null); URL.revokeObjectURL(u); }; v.src = u; }
        else resolve(null);
      } catch (e) { resolve(null); }
    });
  }

  // Alerta quando a midia tem resolucao menor que a tela ativa.
  function warnIfLowRes(media) {
    try {
      const sc = (typeof screen === "function") ? screen() : null;
      if (!sc || !sc.resolution || !media || !media.width || !media.height) return;
      if (media.type !== "image" && media.type !== "video") return;
      const parts = String(sc.resolution).toLowerCase().split("x"); const sw = Number(parts[0]) || 0; const sh = Number(parts[1]) || 0;
      if (sw && sh && (media.width < sw * 0.85 || media.height < sh * 0.85)) {
        toast({ kind: "warn", msg: "Atencao: " + media.name + " (" + media.width + "x" + media.height + ") tem resolucao menor que a tela (" + sc.resolution + "). Pode aparecer borrada." });
      }
    } catch (e) {}
  }

  // Define/limpa a mensagem de emergencia (override em tela cheia) de uma empresa.
  async function emergencyDialog(c) {
    if (!c) return;
    const cur = c.emergency_active ? (c.emergency_message || "") : "";
    const msg = await promptDialog({ title: "Mensagem de emergencia", message: "Exibida em tela cheia em todas as TVs da empresa. Deixe em branco para desativar.", icon: "shield", defaultValue: cur, confirmText: "Aplicar" });
    if (msg === null) return;
    const text = (msg || "").trim();
    try { await updateCompany(c.id, text ? { emergency_message: text, emergency_active: true } : { emergency_active: false }); toast({ kind: "ok", msg: text ? "Mensagem de emergencia ativada." : "Emergencia desativada." }); } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  /** Aplica a marca (nome/logo/cor) da empresa no cabecalho do painel. */
  function applyBranding(b) {
    state.branding = b || null;
    const txt = document.querySelector(".brand-text");
    if (txt) txt.innerHTML = b && b.company_name ? esc(b.company_name) : 'tvMedia <b>Studio</b>';
    const mark = $("brand-mark");
    if (mark) { if (b && b.logo_url) { mark.innerHTML = '<img src="' + esc(b.logo_url) + '" alt="" style="width:100%;height:100%;object-fit:contain;border-radius:5px"/>'; } else { mark.innerHTML = ICONS.logo; } }
    if (b && b.primary_color) { try { document.documentElement.style.setProperty("--accent", b.primary_color); } catch (e) { /* ignore */ } }
  }
  async function refreshBranding() { try { applyBranding(await loadBranding()); } catch (e) { /* ignore */ } }

  /** Mostra um resumo da saude das telas (online/offline + players). */
  async function reportHealth() {
    try {
      const rows = await loadHealth();
      if (!rows || !rows.length) { toast({ kind: "info", msg: "Nenhuma tela cadastrada." }); return; }
      const online = rows.filter((r) => r.online).length;
      const summary = rows.map((r) => (r.online ? "on" : "off") + " " + r.name + " (" + r.connected_players + ")").join(" \u00b7 ");
      toast({ kind: "info", title: "Telas: " + online + "/" + rows.length + " online", msg: summary, timeout: 8000 });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  /** Mostra o proof-of-play agregado dos ultimos 7 dias. */
  async function reportProofOfPlay() {
    try {
      const rows = await loadProofOfPlay(7);
      if (!rows || !rows.length) { toast({ kind: "info", msg: "Sem dados de exibicao nos ultimos 7 dias." }); return; }
      const summary = rows.slice(0, 10).map((r) => r.media_name + ": " + r.plays + "x (" + Math.round(r.total_seconds / 60) + " min)").join(" \u00b7 ");
      toast({ kind: "info", title: "Proof-of-play (7 dias)", msg: summary, timeout: 9000 });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  /** Carrega todos os dados e renderiza o painel. */
  async function loadAll() {
    try {
      await Promise.all([loadMedia(), loadPlaylists(), loadScreens()]);
      try { state.folders = await loadFolders(); } catch (e) { state.folders = []; }
      await refreshBranding();
      if (state.user && state.user.is_super_admin) { try { state.companies = await loadCompanies(); } catch (e) { state.companies = []; } }
      fixSelection();
      renderAll();
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  /** Garante que as selecoes apontem para entidades existentes. */
  function fixSelection() {
    if (!screen()) state.activeScreenId = state.screens[0] ? state.screens[0].id : null;
    const s = screen();
    if (s && !zone()) state.selectedZoneId = s.zones[0] ? s.zones[0].id : null;
    if (!playlistById(state.openPlaylistId)) state.openPlaylistId = state.playlists[0] ? state.playlists[0].id : null;
  }

  // ------------------------------ Toasts --------------------------- //
  /**
   * Exibe um toast empilhado.
   * @param {string|{kind?:string,title?:string,msg?:string,timeout?:number}} opts
   */
  function toast(opts) {
    const o = typeof opts === "string" ? { msg: opts } : opts;
    const kind = o.kind || "info";
    const ico = ({ ok: "check", info: "info", warn: "alert", err: "alert" })[kind] || "info";
    const title = o.title || ({ ok: "Sucesso", info: "Informacao", warn: "Atencao", err: "Erro" })[kind];
    const el = document.createElement("div");
    el.className = "toast " + kind;
    el.innerHTML = '<span class="tico">' + ICONS[ico] + '</span><div class="tbody"><div class="ttitle">' + esc(title) + '</div><div class="tmsg">' + esc(o.msg || "") + '</div></div><button class="tclose">' + ICONS.close + '</button>';
    $("toast-stack").appendChild(el);
    requestAnimationFrame(() => el.classList.add("show"));
    const kill = () => { el.classList.remove("show"); setTimeout(() => el.remove(), 300); };
    el.querySelector(".tclose").addEventListener("click", kill);
    setTimeout(kill, o.timeout || 3200);
  }

  // --------------------- Dialogos personalizados ------------------- //
  // Substituem window.confirm()/window.prompt() nativos por uma janela modal
  // propria, coerente com o tema. Retornam Promise: confirmDialog -> boolean;
  // promptDialog -> string digitada (ou null/'' se cancelado).
  function modalDialog(opts) {
    const o = opts || {};
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");

      const head = document.createElement("div");
      head.className = "modal-head";
      const ico = document.createElement("span");
      ico.className = "modal-ico" + (o.danger ? " danger" : "");
      ico.innerHTML = ICONS[o.icon] || ICONS.info;
      const ttl = document.createElement("span");
      ttl.className = "modal-title";
      ttl.textContent = o.title || "Confirmar";
      head.appendChild(ico); head.appendChild(ttl);

      const body = document.createElement("div");
      body.className = "modal-body";
      body.textContent = o.message || "";

      let input = null;
      if (o.prompt) {
        input = document.createElement("input");
        input.className = "modal-input";
        input.type = "text";
        input.value = o.defaultValue || "";
        if (o.placeholder) input.placeholder = o.placeholder;
      }

      const acts = document.createElement("div");
      acts.className = "modal-actions";
      const cancel = document.createElement("button");
      cancel.className = "btn ghost";
      cancel.textContent = o.cancelText || "Cancelar";
      const ok = document.createElement("button");
      ok.className = "btn " + (o.danger ? "danger" : "primary");
      ok.textContent = o.confirmText || "Confirmar";
      acts.appendChild(cancel); acts.appendChild(ok);

      modal.appendChild(head); modal.appendChild(body);
      if (input) modal.appendChild(input);
      modal.appendChild(acts);
      overlay.appendChild(modal);
      document.body.appendChild(overlay);
      requestAnimationFrame(() => overlay.classList.add("show"));

      let closed = false;
      const close = (result) => {
        if (closed) return; closed = true;
        overlay.classList.remove("show");
        document.removeEventListener("keydown", onKey, true);
        setTimeout(() => overlay.remove(), 200);
        resolve(result);
      };
      const cancelVal = () => (o.prompt ? null : false);
      const okVal = () => (o.prompt ? (input ? input.value.trim() : "") : true);
      const onKey = (e) => {
        if (e.key === "Escape") { e.preventDefault(); close(cancelVal()); }
        else if (e.key === "Enter") { e.preventDefault(); close(okVal()); }
      };
      cancel.addEventListener("click", () => close(cancelVal()));
      ok.addEventListener("click", () => close(okVal()));
      overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(cancelVal()); });
      document.addEventListener("keydown", onKey, true);
      setTimeout(() => { (input || ok).focus(); if (input) input.select(); }, 30);
    });
  }
  function confirmDialog(opts) { return modalDialog(Object.assign({ prompt: false }, opts)); }
  function promptDialog(opts) { return modalDialog(Object.assign({ prompt: true }, opts)); }

  // ---------------------------- Atividades ------------------------- //
  const SECTIONS = [
    { id: "screens", label: "Telas", icon: "screen" },
    { id: "media", label: "Midias", icon: "media" },
    { id: "playlists", label: "Playlists", icon: "playlist" },
    { id: "schedules", label: "Agendamentos", icon: "clock" },
  ];

  function renderActivity() {
    const bar = $("activitybar");
    bar.innerHTML = SECTIONS.map((s) => '<button class="act ' + (s.id === state.activeSection ? "active" : "") + '" data-sec="' + s.id + '" title="' + s.label + '">' + ICONS[s.icon] + '</button>').join("") +
      '<div class="spacer"></div>' +
      '<button class="act" data-act="health" title="Painel de saude das telas">' + ICONS.wifi + '</button>' +
      (state.user && state.user.is_super_admin ? '<button class="act" data-act="companies" title="Console do super admin">' + ICONS.shield + '</button>' : '') +
      '<button class="act" data-act="theme" title="Alternar tema">' + ICONS.sun + '</button>' +
      '<button class="act" data-act="settings" title="Configuracoes">' + ICONS.settings + '</button>';
    bar.querySelectorAll("[data-sec]").forEach((b) => b.addEventListener("click", () => { state.activeSection = b.dataset.sec; renderActivity(); renderSidebar(); renderTabs(); renderDoc(); renderInspector(); renderBottom(); }));
    bar.querySelector('[data-act="theme"]').addEventListener("click", toggleTheme);
    bar.querySelector('[data-act="settings"]').addEventListener("click", openSettings);
    const hb = bar.querySelector('[data-act="health"]'); if (hb) hb.addEventListener("click", openHealthPanel);
    const cb = bar.querySelector('[data-act="companies"]'); if (cb) cb.addEventListener("click", openSuperAdmin);
  }

  // Menus suspensos estilo VS Code (Projeto / Editar / Visualizar / Ajuda).
  // Cada guia abre um menu ancorado abaixo do botao, em vez da paleta.
  let openMenuIndex = null;
  let menuData = [];

  function closeMenu() {
    openMenuIndex = null;
    const host = $("menu");
    if (!host) return;
    host.querySelectorAll(".menu-dropdown").forEach((d) => { d.hidden = true; });
    host.querySelectorAll(".menu-top").forEach((b) => b.classList.remove("active"));
  }

  function toggleMenu(mi) {
    const host = $("menu");
    if (!host) return;
    if (openMenuIndex === mi) { closeMenu(); return; }
    closeMenu();
    openMenuIndex = mi;
    const drop = host.querySelector('[data-drop="' + mi + '"]');
    const top = host.querySelector('[data-mtop="' + mi + '"]');
    if (drop) drop.hidden = false;
    if (top) top.classList.add("active");
  }

  function previewCurrent() {
    const s = screen();
    if (!s) { toast({ kind: "warn", msg: "Selecione uma tela primeiro." }); return; }
    window.open(playerUrl(s.slug), "_blank", "noopener");
  }

  function renderMenu() {
    menuData = [
      { name: "Projeto", items: [
        { label: "Nova tela", run: () => handleSideAct("add-screen") },
        { label: "Nova playlist", run: () => handleSideAct("add-playlist") },
        { sep: true },
        { label: "Recarregar dados", run: () => handleSideAct("reload") },
        { sep: true },
        { label: "Sair", run: () => logout() },
      ] },
      { name: "Editar", items: [
        { label: "Pre-visualizar player", run: () => previewCurrent() },
        { sep: true },
        { label: "Alternar tema claro/escuro", run: () => toggleTheme() },
      ] },
      { name: "Visualizar", items: [
        { label: "Telas", run: () => goSection("screens") },
        { label: "Midias", run: () => goSection("media") },
        { label: "Playlists", run: () => goSection("playlists") },
        { label: "Agendamentos", run: () => goSection("schedules") },
        { sep: true },
        { label: "Paleta de comandos", kbd: "Ctrl K", run: () => openPalette() },
      ] },
      { name: "Ajuda", items: [
        { label: "Guia de uso", run: () => openOnboard() },
        { sep: true },
        { label: "Saude das telas", run: () => reportHealth() },
        { label: "Relatorio de exibicao", run: () => reportProofOfPlay() },
      ] },
    ];
    const host = $("menu");
    host.innerHTML = menuData.map((m, mi) =>
      '<div class="menu-group" data-mi="' + mi + '">' +
        '<button class="menu-top" data-mtop="' + mi + '">' + m.name + '</button>' +
        '<div class="menu-dropdown" data-drop="' + mi + '" role="menu" hidden>' +
          m.items.map((it, ii) => it.sep
            ? '<div class="menu-sep"></div>'
            : '<button class="menu-opt" role="menuitem" data-mi="' + mi + '" data-ii="' + ii + '"><span>' + it.label + '</span>' + (it.kbd ? '<kbd>' + it.kbd + '</kbd>' : '') + '</button>'
          ).join("") +
        '</div>' +
      '</div>'
    ).join("");
    host.querySelectorAll("[data-mtop]").forEach((b) => {
      const mi = Number(b.dataset.mtop);
      b.addEventListener("click", (e) => { e.stopPropagation(); toggleMenu(mi); });
      b.addEventListener("mouseenter", () => { if (openMenuIndex !== null && openMenuIndex !== mi) toggleMenu(mi); });
    });
    host.querySelectorAll(".menu-opt").forEach((b) => b.addEventListener("click", (e) => {
      e.stopPropagation();
      const it = menuData[Number(b.dataset.mi)].items[Number(b.dataset.ii)];
      closeMenu();
      if (it && it.run) it.run();
    }));
  }

  // ----------------------------- Sidebar --------------------------- //
  function sideHead(title, actions) {
    return '<div class="side-head"><span>' + title + '</span><span class="acts">' + (actions || []).map((a) => '<button data-side-act="' + a.act + '" title="' + a.title + '">' + ICONS[a.icon] + '</button>').join("") + '</span></div>';
  }

  function renderSidebar() {
    const sb = $("sidebar");
    if (state.activeSection === "screens") {
      sb.innerHTML = sideHead("Telas", [{ act: "add-screen", icon: "plus", title: "Nova tela" }, { act: "preview", icon: "eye", title: "Pre-visualizar tela" }, { act: "reload", icon: "refresh", title: "Recarregar" }]) +
        '<div class="tree"><div class="tree-group"><div class="tree-label" data-toggle><span class="chev">' + ICONS.chevron + '</span><span>Dispositivos</span></div><div class="tree-children">' +
        (state.screens.length ? state.screens.map((s) => '<div class="tree-item ' + (s.id === state.activeScreenId ? "active" : "") + '" data-screen="' + s.id + '"><span class="dot ' + (isOnline(s) ? "on" : "off") + '"></span><span class="name">' + esc(s.name) + '</span><span class="tag">' + s.zones.length + 'z</span></div>').join("") : '<div class="empty">Nenhuma tela.</div>') +
        '</div></div></div>';
    } else if (state.activeSection === "media") {
      const list = filteredMedia();
      sb.innerHTML = sideHead("Midias", [{ act: "add-media", icon: "plus", title: "Nova midia" }, { act: "bulk-import", icon: "link", title: "Importar URLs em massa" }, { act: "new-folder", icon: "folder", title: "Nova pasta" }, { act: "reload", icon: "refresh", title: "Recarregar" }]) +
        '<div class="tree">' + (list.length ? list.map((m) => '<div class="tree-item ' + (m.id === state.selectedMediaId ? "active" : "") + '" data-media="' + m.id + '">' + ICONS[TYPE_ICON[m.type]] + '<span class="name">' + esc(m.name) + '</span><span class="tag">' + TYPE_LABEL[m.type] + '</span></div>').join("") : '<div class="empty">' + (state.media.length ? "Nada encontrado para os filtros." : "Nenhuma midia. Use + para adicionar.") + '</div>') + '</div>';
    } else if (state.activeSection === "playlists") {
      sb.innerHTML = sideHead("Playlists", [{ act: "add-playlist", icon: "plus", title: "Nova playlist" }, { act: "reload", icon: "refresh", title: "Recarregar" }]) +
        '<div class="tree">' + (state.playlists.length ? state.playlists.map((p) => '<div class="tree-item ' + (p.id === state.openPlaylistId ? "active" : "") + '" data-playlist="' + p.id + '">' + ICONS.playlist + '<span class="name">' + esc(p.name) + '</span><span class="tag">' + p.items.length + '</span></div>').join("") : '<div class="empty">Nenhuma playlist.</div>') + '</div>';
    } else {
      const rows = [];
      state.screens.forEach((s) => s.zones.forEach((z) => z.schedules.forEach((sc) => {
        const pl = playlistById(sc.playlist_id);
        rows.push('<div class="tree-item" data-sched-screen="' + s.id + '"><span class="name">' + esc((pl ? pl.name : "?")) + '</span><span class="tag">' + minToHHMM(sc.start_minute) + '</span></div>');
      })));
      sb.innerHTML = sideHead("Agendamentos") + '<div class="tree">' + (rows.join("") || '<div class="empty">Nenhum agendamento. Crie no inspetor de uma zona.</div>') + '</div>';
    }
    bindSidebar();
  }

  function bindSidebar() {
    const sb = $("sidebar");
    sb.querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", () => b.closest(".tree-group").classList.toggle("collapsed")));
    sb.querySelectorAll("[data-screen]").forEach((b) => b.addEventListener("click", () => { state.activeScreenId = Number(b.dataset.screen); const s = screen(); state.selectedZoneId = s && s.zones[0] ? s.zones[0].id : null; renderAll(); }));
    sb.querySelectorAll("[data-media]").forEach((b) => b.addEventListener("click", () => { state.selectedMediaId = Number(b.dataset.media); renderSidebar(); renderInspector(); }));
    sb.querySelectorAll("[data-playlist]").forEach((b) => b.addEventListener("click", () => { state.openPlaylistId = Number(b.dataset.playlist); renderSidebar(); renderTabs(); renderDoc(); renderInspector(); renderBottom(); }));
    sb.querySelectorAll("[data-sched-screen]").forEach((b) => b.addEventListener("click", () => { state.activeSection = "screens"; state.activeScreenId = Number(b.dataset.schedScreen); renderAll(); }));
    sb.querySelectorAll("[data-side-act]").forEach((b) => b.addEventListener("click", () => handleSideAct(b.dataset.sideAct)));
  }

  async function handleSideAct(act) {
    try {
      if (act === "reload") { await loadAll(); toast({ kind: "info", msg: "Projeto recarregado." }); }
      else if (act === "add-screen") { openScreenWizard(); }
      else if (act === "add-playlist") {
        const created = await api("/api/playlists", { method: "POST", body: JSON.stringify({ name: "Nova playlist" }) });
        await loadPlaylists(); state.openPlaylistId = created.id; renderSidebar(); renderTabs(); renderDoc(); toast({ kind: "ok", msg: "Playlist criada." });
      } else if (act === "add-media") { openMediaModal(); }
      else if (act === "bulk-import") { openBulkModal(); }
      else if (act === "new-folder") { await createFolder(); }
      else if (act === "preview") { const s = screen(); if (s) window.open(playerUrl(s.slug), "_blank"); else toast({ kind: "warn", msg: "Selecione uma tela primeiro." }); }
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  // ------------------------------- Tabs ---------------------------- //
  function renderTabs() {
    const tb = $("tabsbar");
    if (state.activeSection === "screens") {
      tb.innerHTML = state.screens.map((s) => '<div class="tab ' + (s.id === state.activeScreenId ? "active" : "") + '" data-tab="' + s.id + '">' + ICONS.screen + '<span>' + esc(s.name) + '</span></div>').join("") || '<div class="tab active">' + ICONS.screen + '<span>Sem telas</span></div>';
      tb.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { state.activeScreenId = Number(b.dataset.tab); const s = screen(); state.selectedZoneId = s && s.zones[0] ? s.zones[0].id : null; renderAll(); }));
    } else {
      const map = { media: { i: "media", t: "Biblioteca de midias" }, playlists: { i: "playlist", t: "Editor de playlists" }, schedules: { i: "clock", t: "Agendamentos" } };
      const m = map[state.activeSection];
      tb.innerHTML = '<div class="tab active">' + ICONS[m.i] + '<span>' + m.t + '</span></div>';
    }
    $("title-center").textContent = screen() ? screen().slug : "";
  }

  // ----------------------------- Documento ------------------------- //
  function renderDoc() {
    const doc = $("doc");
    if (state.activeSection === "screens") doc.innerHTML = '<div class="stage-wrap"><div class="stage" id="stage"></div><div class="stage-hint" id="stage-hint"></div></div>';
    else if (state.activeSection === "media") doc.innerHTML = renderMediaDoc();
    else if (state.activeSection === "playlists") doc.innerHTML = renderPlaylistDoc();
    else doc.innerHTML = renderSchedulesDoc();
    if (state.activeSection === "screens") renderStage();
    else if (state.activeSection === "media") bindMediaDoc();
    else if (state.activeSection === "playlists") bindPlaylistDoc();
    else bindSchedulesDoc();
  }

  // ------------------------------ Canvas --------------------------- //
  function renderStage() {
    const sc = screen();
    const stage = $("stage");
    if (!stage) return;
    if (!sc) { stage.innerHTML = ""; return; }
    const ar = screenAspect(sc);
    stage.style.aspectRatio = ar.w + " / " + ar.h;
    if (ar.w >= ar.h) { stage.style.width = "100%"; stage.style.height = "auto"; stage.style.maxWidth = "1024px"; stage.style.maxHeight = "100%"; }
    else { stage.style.width = "auto"; stage.style.height = "min(100%, 68vh)"; stage.style.maxWidth = "100%"; stage.style.maxHeight = "100%"; }
    stage.innerHTML = sc.zones.slice().sort((a, b) => a.z_index - b.z_index).map((z) => {
      const pl = playlistById(z.default_playlist_id);
      const isEmpty = !pl || !pl.items || pl.items.length === 0;
      const body = isEmpty ? '<span class="zone-empty-tag">⚠ Sem conteúdo</span>' : esc(pl.name) + " - " + pl.items.length + " item(s)";
      return '<div class="zone ' + (z.id === state.selectedZoneId ? "selected" : "") + (isEmpty ? " empty" : "") + '" data-zone="' + z.id + '" style="left:' + z.x + '%;top:' + z.y + '%;width:' + z.width + '%;height:' + z.height + '%"><div class="zone-label">' + ICONS.layout + '<span>' + esc(z.name) + '</span></div><div class="zone-body">' + body + '</div><div class="resize" data-resize="' + z.id + '"></div></div>';
    }).join("");
    const resTxt = (sc.resolution || "1920x1080") + (sc.orientation === "portrait" ? " vertical" : " horizontal");
    $("stage-hint").innerHTML = esc(sc.name) + " &middot; " + esc(resTxt) + " &middot; " + sc.zones.length + " zona(s) &middot; <a href=\"#\" id=\"screen-size-edit\" style=\"color:#7aa2f7\">ajustar tamanho</a>";
    const sizeEdit = $("screen-size-edit"); if (sizeEdit) sizeEdit.addEventListener("click", (e) => { e.preventDefault(); openScreenSizeModal(sc); });
    bindZoneInteractions();
  }

  function bindZoneInteractions() {
    const stage = $("stage");
    if (!stage.dataset.ctxBound) {
      stage.dataset.ctxBound = "1";
      stage.addEventListener("contextmenu", (e) => {
        if (e.target.closest("[data-zone]")) return;
        e.preventDefault();
        const rect = stage.getBoundingClientRect();
        const px = clamp(Math.round(((e.clientX - rect.left) / rect.width) * 100), 0, 95);
        const py = clamp(Math.round(((e.clientY - rect.top) / rect.height) * 100), 0, 95);
        openStageMenu(e.clientX, e.clientY, px, py);
      });
    }
    stage.querySelectorAll("[data-zone]").forEach((el) => {
      el.addEventListener("pointerdown", (e) => {
        if (e.target.closest("[data-resize]")) return;
        const z = zoneOf(Number(el.dataset.zone));
        state.selectedZoneId = z.id; renderInspector(); markSelected();
        startDrag(e, z, "move");
      });
      el.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const z = zoneOf(Number(el.dataset.zone));
        state.selectedZoneId = z.id; markSelected(); renderInspector();
        openZoneQuickMenu(e.clientX, e.clientY, z.id);
      });
    });
    stage.querySelectorAll("[data-resize]").forEach((el) => {
      el.addEventListener("pointerdown", (e) => { e.stopPropagation(); const z = zoneOf(Number(el.dataset.resize)); state.selectedZoneId = z.id; renderInspector(); markSelected(); startDrag(e, z, "resize"); });
    });
  }
  function zoneOf(id) { return screen().zones.find((z) => z.id === id); }
  function markSelected() { const stage = $("stage"); if (!stage) return; stage.querySelectorAll("[data-zone]").forEach((el) => el.classList.toggle("selected", Number(el.dataset.zone) === state.selectedZoneId)); }

  function nearestSnap(v, targets, thr) { let best = null, bd = thr; for (const t of targets) { const d = Math.abs(v - t); if (d <= bd) { bd = d; best = t; } } return best; }
  function clearGuides() { const st = $("stage"); if (!st) return; st.querySelectorAll(".snap-guide").forEach((g) => g.remove()); }
  function drawGuides(vs, hs) {
    const st = $("stage"); if (!st) return; clearGuides();
    vs.forEach((v) => { const g = document.createElement("div"); g.className = "snap-guide snap-v"; g.style.left = v + "%"; st.appendChild(g); });
    hs.forEach((v) => { const g = document.createElement("div"); g.className = "snap-guide snap-h"; g.style.top = v + "%"; st.appendChild(g); });
  }
  function startDrag(e, z, mode) {
    e.preventDefault();
    isDragging = true;
    const rect = $("stage").getBoundingClientRect();
    const sx = e.clientX, sy = e.clientY;
    const o = { x: z.x, y: z.y, w: z.width, h: z.height };
    const SNAP = 1.6;
    const sc = screen();
    const others = sc ? sc.zones.filter((zz) => zz.id !== z.id) : [];
    const xT = [0, 50, 100]; const yT = [0, 50, 100];
    others.forEach((zz) => { xT.push(zz.x, zz.x + zz.width, zz.x + zz.width / 2); yT.push(zz.y, zz.y + zz.height, zz.y + zz.height / 2); });
    const move = (ev) => {
      const dx = ((ev.clientX - sx) / rect.width) * 100;
      const dy = ((ev.clientY - sy) / rect.height) * 100;
      const gv = []; const gh = [];
      if (mode === "move") {
        let nx = clamp(Math.round(o.x + dx), 0, 100 - z.width);
        let ny = clamp(Math.round(o.y + dy), 0, 100 - z.height);
        const sl = nearestSnap(nx, xT, SNAP); const sr = nearestSnap(nx + z.width, xT, SNAP);
        if (sl != null) { nx = sl; gv.push(sl); } else if (sr != null) { nx = sr - z.width; gv.push(sr); }
        const stp = nearestSnap(ny, yT, SNAP); const sb = nearestSnap(ny + z.height, yT, SNAP);
        if (stp != null) { ny = stp; gh.push(stp); } else if (sb != null) { ny = sb - z.height; gh.push(sb); }
        z.x = clamp(nx, 0, 100 - z.width); z.y = clamp(ny, 0, 100 - z.height);
      } else {
        let nw = clamp(Math.round(o.w + dx), 5, 100 - z.x);
        let nh = clamp(Math.round(o.h + dy), 5, 100 - z.y);
        const sr = nearestSnap(z.x + nw, xT, SNAP); if (sr != null) { nw = sr - z.x; gv.push(sr); }
        const sb = nearestSnap(z.y + nh, yT, SNAP); if (sb != null) { nh = sb - z.y; gh.push(sb); }
        z.width = clamp(nw, 5, 100 - z.x); z.height = clamp(nh, 5, 100 - z.y);
      }
      drawGuides(gv, gh);
      applyZoneGeometry(z); syncInspectorGeometry(z);
    };
    const up = async () => {
      document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); isDragging = false;
      clearGuides();
      try { await api("/api/screens/" + state.activeScreenId + "/zones/" + z.id, { method: "PATCH", body: JSON.stringify({ x: z.x, y: z.y, width: z.width, height: z.height }) }); renderBottom(); renderStatus(); }
      catch (err) { toast({ kind: "err", msg: err.message }); }
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  function applyZoneGeometry(z) { const el = $("stage").querySelector('[data-zone="' + z.id + '"]'); if (el) { el.style.left = z.x + "%"; el.style.top = z.y + "%"; el.style.width = z.width + "%"; el.style.height = z.height + "%"; } }
  function syncInspectorGeometry(z) { [["x", "x"], ["y", "y"], ["w", "width"], ["h", "height"]].forEach((pair) => { const i = $("f-" + pair[0]); if (i) i.value = z[pair[1]]; const v = $("v-" + pair[0]); if (v) v.textContent = z[pair[1]] + "%"; }); }

  // ---------------------------- Inspector -------------------------- //
  function renderInspector() {
    const insp = $("inspector");
    if (state.activeSection === "media") { insp.innerHTML = renderMediaInspector(); bindMediaInspector(); return; }
    if (state.activeSection === "playlists") { insp.innerHTML = '<div class="insp-head">' + ICONS.playlist + '<span>Playlist</span></div><div class="insp-section"><p class="empty" style="padding:0">Selecione um item na linha do tempo do editor para ajustar duracao, ajuste, transicao e som.</p></div>'; return; }
    if (state.activeSection === "schedules") { insp.innerHTML = '<div class="insp-head">' + ICONS.clock + '<span>Agendamentos</span></div><div class="insp-section"><p class="empty" style="padding:0">Os agendamentos sao criados no inspetor de cada zona (secao Telas).</p></div>'; return; }
    const z = zone();
    const sc = screen();
    if (!z) { insp.innerHTML = '<div class="insp-head">' + ICONS.screen + '<span>Tela</span></div>' + (sc ? screenProps(sc) : '<div class="empty">Selecione uma tela.</div>'); bindInspector(); return; }
    insp.innerHTML = '<div class="insp-head">' + ICONS.layout + '<span>Zona: ' + esc(z.name) + '</span></div>' +
      '<div class="insp-section"><h5>Identificacao</h5>' + field("Nome", '<input id="f-name" value="' + esc(z.name) + '"/>') + field("Camada (z-index)", '<input id="f-z" type="number" value="' + z.z_index + '"/>') + '</div>' +
      '<div class="insp-section"><h5>Geometria (% da tela)</h5><div class="grid2">' + rangeField("x", "X", z.x) + rangeField("y", "Y", z.y) + rangeField("w", "Largura", z.width) + rangeField("h", "Altura", z.height) + '</div></div>' +
      '<div class="insp-section"><h5>Conteudo</h5>' +
      '<button class="btn primary block" data-quick-add>' + ICONS.plus + ' Adicionar conteudo</button>' +
      '<span class="hint" style="display:block;margin:6px 0 10px">Dica: clique com o botao direito na zona (no canvas) para abrir o menu rapido.</span>' +
      field("Playlist padrao", '<select id="f-playlist"><option value="">- sem playlist -</option>' + state.playlists.map((p) => '<option value="' + p.id + '"' + (p.id === z.default_playlist_id ? " selected" : "") + '>' + esc(p.name) + '</option>').join("") + '</select>') +
      '<button class="btn ghost block small" data-open-playlist>' + ICONS.playlist + ' Abrir no editor de playlists</button></div>' +
      '<div class="insp-section"><h5>Agendamentos</h5>' + (z.schedules.length ? z.schedules.map(schedCard).join("") : '<div class="empty" style="padding:0 0 8px">Sem agendamentos. A playlist padrao toca sempre.</div>') + schedForm(z) + '</div>' +
      '<div class="insp-section"><button class="btn block" data-dup-zone>' + ICONS.copy + ' Duplicar zona</button><button class="btn danger block small" style="margin-top:8px" data-del-zone>' + ICONS.trash + ' Excluir zona</button></div>';
    bindInspector();
  }

  function screenProps(sc) {
    return '<div class="insp-section"><h5>Tela</h5>' + field("Nome", '<input id="f-sname" value="' + esc(sc.name) + '"/>') + field("Fuso horario", '<input id="f-tz" value="' + esc(sc.timezone) + '"/>') +
      '<div class="switch"><span>Status</span><span class="tag" style="color:' + (isOnline(sc) ? "var(--green)" : "var(--faint)") + '">' + (isOnline(sc) ? "online" : "offline") + '</span></div>' +
      field("Slug (somente leitura)", '<input value="' + esc(sc.slug) + '" readonly/>') +
      '<div class="field"><label>Link do player (TV)</label><div class="code">' + esc(playerUrl(sc.slug)) + '</div></div>' +
      '<button class="btn ghost block small" data-copy-link>' + ICONS.copy + ' Copiar link</button>' +
      '<button class="btn ghost block small" style="margin-top:8px" data-preview-screen>' + ICONS.eye + ' Pre-visualizar player</button>' +
      '<button class="btn ghost block small" style="margin-top:8px" data-live-preview>' + ICONS.eye + ' Pre-visualizar ao vivo (no painel)</button>' +
      '<button class="btn ghost block small" style="margin-top:8px" data-kiosk>' + ICONS.screen + ' Modo quiosque (QR code)</button></div>' +
      '<div class="insp-section"><h5>Sincronia e emparelhamento</h5>' + field("Grupo de sincronia", '<input id="f-syncgroup" value="' + esc(sc.sync_group || "") + '" placeholder="ex.: vitrine-loja1"/>') + '<span class="hint" style="display:block;margin:-4px 0 10px">Telas no mesmo grupo recarregam juntas quando uma e atualizada.</span>' + (sc.pair_code ? '<div class="field"><label>Codigo de emparelhamento (TV)</label><div class="code">' + esc(sc.pair_code) + '</div></div><button class="btn ghost block small" data-copy-pair>' + ICONS.copy + ' Copiar codigo</button>' : '') + '</div>' +
      '<div class="insp-section"><h5>Atalhos de layout</h5><button class="btn block" data-add-ticker>' + ICONS.tag + ' Adicionar rodape de ticker (1 clique)</button><span class="hint" style="display:block;margin-top:6px">Cria uma zona fixa de rodape (15% da altura) ja com um ticker de promocoes.</span></div>' +
      '<div class="insp-section"><h5>Musica de fundo (tela)</h5>' + screenMusicField(sc) + '</div>' +
      '<div class="insp-section"><h5>Tema de cores</h5>' + themeFields(sc) + '</div>' +
      '<div class="insp-section"><h5>Overlays (HUD)</h5>' + overlayListHtml(sc) + '<button class="btn block small" style="margin-top:8px" data-add-overlay>' + ICONS.plus + ' Adicionar overlay</button></div>' +
      '<div class="insp-section"><button class="btn block" data-add-zone>' + ICONS.plus + ' Adicionar zona</button><button class="btn block small" style="margin-top:8px" data-dup-screen>' + ICONS.copy + ' Duplicar tela</button><button class="btn danger block small" style="margin-top:8px" data-del-screen>' + ICONS.trash + ' Excluir tela</button></div>';
  }

  function field(label, inner) { return '<div class="field"><label>' + label + '</label>' + inner + '</div>'; }
  function rangeField(key, label, val) { return '<div class="field"><label>' + label + '</label><div class="range-row"><input id="f-' + key + '" type="range" min="0" max="100" value="' + val + '" data-geo="' + key + '"/><span class="val" id="v-' + key + '">' + val + '%</span></div></div>'; }
  function schedCard(sc) {
    const pl = playlistById(sc.playlist_id);
    const days = (sc.days_of_week || "").split(",").filter((x) => x !== "").map(Number);
    return '<div class="sched"><div class="row"><strong>' + esc(pl ? pl.name : "?") + '</strong><span class="tag">' + minToHHMM(sc.start_minute) + " - " + minToHHMM(sc.end_minute) + ' P' + sc.priority + '</span></div><div class="days">' + DAYS.map((d, i) => '<span class="day ' + (days.includes(i) ? "on" : "") + '" title="' + DAYS_FULL[i] + '">' + d + '</span>').join("") + '</div><button class="btn danger block small" style="margin-top:7px" data-del-sched="' + sc.id + '">' + ICONS.trash + ' Remover</button></div>';
  }
  function schedForm(z) {
    return '<div class="sched" style="margin-top:6px"><div class="field"><label>Nova regra - playlist</label><select id="sf-pl">' + state.playlists.map((p) => '<option value="' + p.id + '">' + esc(p.name) + '</option>').join("") + '</select></div><div class="grid2"><div class="field"><label>Inicio</label><input id="sf-start" type="time" value="08:00"/></div><div class="field"><label>Fim</label><input id="sf-end" type="time" value="18:00"/></div></div><div class="field"><label>Prioridade</label><input id="sf-prio" type="number" value="1"/></div><div class="days" id="sf-days">' + DAYS.map((d, i) => '<span class="day ' + (i < 5 ? "on" : "") + '" data-day="' + i + '" title="' + DAYS_FULL[i] + '">' + d + '</span>').join("") + '</div><button class="btn primary block small" style="margin-top:8px" data-add-sched>' + ICONS.plus + ' Agendar</button></div>';
  }

  function bindInspector() {
    const insp = $("inspector");
    const z = zone();
    if (z) {
      const screenId = state.activeScreenId;
      const nm = $("f-name"); if (nm) { nm.addEventListener("input", () => { z.name = nm.value; renderStage(); renderTabs(); }); nm.addEventListener("change", () => patchZone(z.id, { name: nm.value })); }
      const zi = $("f-z"); if (zi) zi.addEventListener("change", () => { z.z_index = Number(zi.value) || 0; patchZone(z.id, { z_index: z.z_index }); renderStage(); });
      insp.querySelectorAll("[data-geo]").forEach((r) => {
        r.addEventListener("input", () => { const k = r.dataset.geo; const f = { x: "x", y: "y", w: "width", h: "height" }[k]; z[f] = clamp(Number(r.value), 0, 100); const v = $("v-" + k); if (v) v.textContent = z[f] + "%"; applyZoneGeometry(z); });
        r.addEventListener("change", () => patchZone(z.id, { x: z.x, y: z.y, width: z.width, height: z.height }));
      });
      const pl = $("f-playlist"); if (pl) pl.addEventListener("change", () => { z.default_playlist_id = pl.value ? Number(pl.value) : null; patchZone(z.id, { default_playlist_id: z.default_playlist_id }); renderStage(); renderBottom(); });
      const op = insp.querySelector("[data-open-playlist]"); if (op) op.addEventListener("click", () => { if (z.default_playlist_id) state.openPlaylistId = z.default_playlist_id; state.activeSection = "playlists"; renderActivity(); renderSidebar(); renderTabs(); renderDoc(); renderInspector(); renderBottom(); });
      const qa = insp.querySelector("[data-quick-add]"); if (qa) qa.addEventListener("click", () => { const r = qa.getBoundingClientRect(); openZoneQuickMenu(r.left, r.bottom + 4, z.id); });
      const dz = insp.querySelector("[data-dup-zone]"); if (dz) dz.addEventListener("click", async () => { try { await api("/api/screens/" + screenId + "/zones", { method: "POST", body: JSON.stringify({ name: z.name + " (copia)", x: clamp(z.x + 5, 0, 90), y: clamp(z.y + 5, 0, 90), width: z.width, height: z.height, z_index: z.z_index + 1, default_playlist_id: z.default_playlist_id }) }); await loadScreens(); const s = screen(); state.selectedZoneId = s.zones[s.zones.length - 1].id; renderAll(); toast({ kind: "ok", msg: "Zona duplicada." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
      const del = insp.querySelector("[data-del-zone]"); if (del) del.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir zona", message: "Tem certeza que deseja excluir esta zona? Esta acao nao pode ser desfeita.", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/screens/" + screenId + "/zones/" + z.id, { method: "DELETE" }); await loadScreens(); const s = screen(); state.selectedZoneId = s && s.zones[0] ? s.zones[0].id : null; renderAll(); toast({ kind: "warn", msg: "Zona excluida." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
      insp.querySelectorAll("#sf-days .day").forEach((d) => d.addEventListener("click", () => d.classList.toggle("on")));
      const as = insp.querySelector("[data-add-sched]"); if (as) as.addEventListener("click", () => addSchedule(z.id));
      insp.querySelectorAll("[data-del-sched]").forEach((b) => b.addEventListener("click", () => deleteSchedule(z.id, Number(b.dataset.delSched))));
    } else {
      const sc = screen();
      const sn = $("f-sname"); if (sn) { sn.addEventListener("input", () => { sc.name = sn.value; renderTabs(); renderSidebar(); }); sn.addEventListener("change", () => patchScreen(sc.id, { name: sn.value })); }
      const tz = $("f-tz"); if (tz) tz.addEventListener("change", () => patchScreen(sc.id, { timezone: tz.value }));
      const sg = $("f-syncgroup"); if (sg) sg.addEventListener("change", async () => { try { await api("/api/screens/" + sc.id, { method: "PATCH", body: JSON.stringify({ sync_group: sg.value.trim() || null }) }); await loadScreens(); renderInspector(); toast({ kind: "ok", msg: "Grupo de sincronia atualizado." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
      const cpr = insp.querySelector("[data-copy-pair]"); if (cpr) cpr.addEventListener("click", () => copyText(sc.pair_code || ""));
      const at = insp.querySelector("[data-add-ticker]"); if (at) at.addEventListener("click", () => addTickerFooter(sc));
      const cl = insp.querySelector("[data-copy-link]"); if (cl) cl.addEventListener("click", () => copyText(playerUrl(sc.slug)));
      const pv = insp.querySelector("[data-preview-screen]"); if (pv) pv.addEventListener("click", () => window.open(playerUrl(sc.slug), "_blank"));
      const lp = insp.querySelector("[data-live-preview]"); if (lp) lp.addEventListener("click", () => openLivePreview(sc));
      const kq = insp.querySelector("[data-kiosk]"); if (kq) kq.addEventListener("click", () => openKioskMode(sc));
      const dsc = insp.querySelector("[data-dup-screen]"); if (dsc) dsc.addEventListener("click", () => duplicateScreen(sc));
      const bg = $("f-bgaudio"); if (bg) bg.addEventListener("change", () => setScreenMusic(bg.value ? Number(bg.value) : null));
      const um = insp.querySelector("[data-upload-music]"); if (um) um.addEventListener("click", uploadScreenMusic);
      const az = insp.querySelector("[data-add-zone]"); if (az) az.addEventListener("click", () => { createZoneFlow(10, 10, 40, 40); });
      const themeMap = { bg: "theme_bg", text: "theme_text", accent: "theme_accent", tbg: "theme_ticker_bg", ttext: "theme_ticker_text" };
      ["bg", "text", "accent", "tbg", "ttext"].forEach((id) => {
        const c = $("th-" + id); const t = $("th-" + id + "-tx");
        if (c && t) {
          c.addEventListener("input", () => { t.value = c.value; });
          t.addEventListener("input", () => { if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(t.value.trim())) c.value = t.value.trim(); });
        }
      });
      const stv = insp.querySelector("[data-save-theme]");
      if (stv) stv.addEventListener("click", async () => {
        const patch = {};
        Object.keys(themeMap).forEach((id) => { const t = $("th-" + id + "-tx"); const v = (t && t.value.trim()) || ""; patch[themeMap[id]] = v || null; });
        try { await api("/api/screens/" + sc.id, { method: "PATCH", body: JSON.stringify(patch) }); await loadScreens(); renderInspector(); toast({ kind: "ok", msg: "Tema atualizado." }); } catch (err) { toast({ kind: "err", msg: err.message }); }
      });
      const rtv = insp.querySelector("[data-reset-theme]");
      if (rtv) rtv.addEventListener("click", async () => {
        try { await api("/api/screens/" + sc.id, { method: "PATCH", body: JSON.stringify({ theme_bg: null, theme_text: null, theme_accent: null, theme_ticker_bg: null, theme_ticker_text: null }) }); await loadScreens(); renderInspector(); toast({ kind: "ok", msg: "Tema redefinido." }); } catch (err) { toast({ kind: "err", msg: err.message }); }
      });
      const aov = insp.querySelector("[data-add-overlay]");
      if (aov) aov.addEventListener("click", () => openOverlayModal(sc, null));
      insp.querySelectorAll("[data-edit-overlay]").forEach((b) => b.addEventListener("click", () => { const ov = (sc.overlays || []).find((o) => String(o.id) === b.dataset.editOverlay); if (ov) openOverlayModal(sc, ov); }));
      insp.querySelectorAll("[data-del-overlay]").forEach((b) => b.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir overlay", message: "Remover este overlay da tela?", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/screens/" + sc.id + "/overlays/" + b.dataset.delOverlay, { method: "DELETE" }); await loadScreens(); renderInspector(); toast({ kind: "warn", msg: "Overlay removido." }); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
      const ds = insp.querySelector("[data-del-screen]"); if (ds) ds.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir tela", message: "Tem certeza que deseja excluir esta tela e todas as suas zonas? Esta acao nao pode ser desfeita.", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/screens/" + sc.id, { method: "DELETE" }); await loadScreens(); fixSelection(); renderAll(); toast({ kind: "warn", msg: "Tela excluida." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
    }
  }

  async function patchZone(zoneId, patch) { try { await api("/api/screens/" + state.activeScreenId + "/zones/" + zoneId, { method: "PATCH", body: JSON.stringify(patch) }); renderBottom(); renderStatus(); } catch (err) { toast({ kind: "err", msg: err.message }); } }
  async function patchScreen(screenId, patch) { try { await api("/api/screens/" + screenId, { method: "PATCH", body: JSON.stringify(patch) }); } catch (err) { toast({ kind: "err", msg: err.message }); } }

  async function addSchedule(zoneId) {
    const insp = $("inspector");
    const playlist_id = Number(insp.querySelector("#sf-pl").value);
    const start_minute = hhmmToMin(insp.querySelector("#sf-start").value);
    const end_minute = hhmmToMin(insp.querySelector("#sf-end").value);
    const priority = Number(insp.querySelector("#sf-prio").value) || 0;
    const days = Array.from(insp.querySelectorAll("#sf-days .day.on")).map((d) => d.dataset.day);
    if (!playlist_id) { toast({ kind: "warn", msg: "Selecione uma playlist." }); return; }
    if (!days.length) { toast({ kind: "warn", msg: "Selecione ao menos um dia." }); return; }
    try { await api("/api/zones/" + zoneId + "/schedules", { method: "POST", body: JSON.stringify({ playlist_id, days_of_week: days.join(","), start_minute, end_minute, priority }) }); await loadScreens(); renderInspector(); renderBottom(); toast({ kind: "ok", msg: "Agendamento criado." }); } catch (err) { toast({ kind: "err", msg: err.message }); }
  }
  async function deleteSchedule(zoneId, schedId) { try { await api("/api/zones/" + zoneId + "/schedules/" + schedId, { method: "DELETE" }); await loadScreens(); renderInspector(); renderBottom(); toast({ kind: "warn", msg: "Agendamento removido." }); } catch (err) { toast({ kind: "err", msg: err.message }); } }

  // ============================ Midias ============================== //
  function folderName(id) { const f = state.folders.find((x) => x.id === id); return f ? f.name : null; }
  function mediaFolderOptions(sel) {
    return '<option value="all"' + (sel === "all" ? " selected" : "") + '>Todas as pastas</option>' +
      '<option value="none"' + (sel === "none" ? " selected" : "") + '>Sem pasta</option>' +
      state.folders.map((f) => '<option value="' + f.id + '"' + (String(sel) === String(f.id) ? " selected" : "") + '>' + esc(f.name) + '</option>').join("");
  }
  function filteredMedia() {
    const q = (state.mediaQuery || "").trim().toLowerCase();
    return state.media.filter((m) => {
      if (state.mediaFolder === "none" && m.folder_id != null) return false;
      if (state.mediaFolder !== "all" && state.mediaFolder !== "none" && String(m.folder_id) !== String(state.mediaFolder)) return false;
      if (!q) return true;
      return (m.name + " " + (m.tags || []).join(" ") + " " + (TYPE_LABEL[m.type] || "")).toLowerCase().indexOf(q) !== -1;
    });
  }
  function renderMediaDoc() {
    return '<div class="doc-toolbar">' +
      '<span class="side-search grow">' + ICONS.search + '<input id="media-search" placeholder="Buscar por nome ou tag..." value="' + esc(state.mediaQuery) + '"/></span>' +
      '<select id="media-folder">' + mediaFolderOptions(state.mediaFolder) + '</select>' +
      '<button class="btn ghost small" id="md-folder">' + ICONS.folder + ' Nova pasta</button>' +
      '<button class="btn ghost small" id="md-bulk">' + ICONS.link + ' Importar URLs</button>' +
      '<button class="btn primary small" id="md-add">' + ICONS.plus + ' Nova midia</button>' +
      '</div><div id="media-grid-wrap">' + renderMediaGrid() + '</div>';
  }
  function renderMediaGrid() {
    if (!state.media.length) {
      return '<div class="empty-cta">' + ICONS.media +
        '<h4>Sua biblioteca esta vazia</h4>' +
        '<p>Adicione imagens, videos, textos ou links. Depois monte uma <b>playlist</b> e ligue-a a uma <b>zona</b> em <b>Telas</b> para exibir.</p>' +
        '<button class="btn primary" id="cta-add">' + ICONS.plus + ' Adicionar primeira midia</button></div>';
    }
    const list = filteredMedia();
    const hint = '<div class="next-hint">' + ICONS.info + '<span><b>Proximo passo:</b> adicione a midia a uma <b>Playlist</b> e ligue a playlist a uma <b>zona</b> da tela (secao Telas).</span></div>';
    if (!list.length) return hint + '<div class="empty">Nada encontrado para os filtros atuais.</div>';
    return hint + '<div class="media-grid">' + list.map(mediaCard).join("") + '</div>';
  }
  function procBadge(m) {
    if (m.type !== "image" && m.type !== "video") return "";
    const map = {
      pending: ["na fila", "warn"],
      processing: ["otimizando\u2026", "warn"],
      done: m.optimized_path ? ["otimizada", "ok"] : ["", ""],
      failed: ["falha", "err"],
    };
    const entry = map[m.processing_status || "skipped"];
    if (!entry || !entry[0]) return "";
    const title = m.processing_note ? ' title="' + esc(m.processing_note) + '"' : "";
    return '<span class="tag proc-' + entry[1] + '"' + title + '>' + entry[0] + '</span>';
  }
  function mediaCard(m) {
    let thumb;
    if (m.type === "image" && m.path) thumb = '<div class="thumb"><img src="/media/' + esc(m.path) + '" alt=""/></div>';
    else if (m.type === "video" && m.path) thumb = '<div class="thumb"><video src="/media/' + esc(m.path) + '" muted></video></div>';
    else thumb = '<div class="thumb placeholder">' + ICONS[TYPE_ICON[m.type]] + '</div>';
    const fol = m.folder_id != null ? '<span class="chip">' + ICONS.folder + esc(folderName(m.folder_id) || "?") + '</span>' : "";
    const tags = (m.tags || []).slice(0, 3).map((t) => '<span class="chip">' + esc(t) + '</span>').join("");
    const meta = (fol || tags) ? '<div class="mc-meta">' + fol + tags + '</div>' : "";
    return '<div class="media-card' + (m.id === state.selectedMediaId ? " sel" : "") + '" data-mcard="' + m.id + '">' + thumb + '<div class="mc-body"><div class="mc-name">' + esc(m.name) + '</div>' + meta + '<div class="mc-foot"><span class="tag">' + TYPE_LABEL[m.type] + '</span>' + (m.width && m.height ? '<span class="tag" title="Resolucao">' + m.width + '\u00d7' + m.height + '</span>' : '') + procBadge(m) + ((m.type === "image" || m.type === "video") ? '<button class="btn ghost small" data-reproc="' + m.id + '" title="Reprocessar midia">' + ICONS.refresh + '</button>' : '') + '<button class="btn danger small" data-del-media="' + m.id + '">' + ICONS.trash + '</button></div></div></div>';
  }
  function bindMediaDoc() {
    const search = $("media-search");
    const refreshGrid = () => { const w = $("media-grid-wrap"); if (w) { w.innerHTML = renderMediaGrid(); bindMediaGrid(); } };
    if (search) search.addEventListener("input", () => { state.mediaQuery = search.value; refreshGrid(); });
    const fol = $("media-folder"); if (fol) fol.addEventListener("change", () => { state.mediaFolder = fol.value; refreshGrid(); });
    const add = $("md-add"); if (add) add.addEventListener("click", openMediaModal);
    const bulk = $("md-bulk"); if (bulk) bulk.addEventListener("click", openBulkModal);
    const nf = $("md-folder"); if (nf) nf.addEventListener("click", createFolder);
    bindMediaGrid();
  }
  function bindMediaGrid() {
    const doc = $("doc");
    const cta = $("cta-add"); if (cta) cta.addEventListener("click", openMediaModal);
    doc.querySelectorAll("[data-mcard]").forEach((c) => c.addEventListener("click", (e) => { if (e.target.closest("[data-del-media]") || e.target.closest("[data-reproc]")) return; state.selectedMediaId = Number(c.dataset.mcard); doc.querySelectorAll("[data-mcard]").forEach((x) => x.classList.toggle("sel", x === c)); renderSidebar(); renderInspector(); }));
    doc.querySelectorAll("[data-del-media]").forEach((b) => b.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir midia", message: "Tem certeza que deseja excluir esta midia?", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/media/" + b.dataset.delMedia, { method: "DELETE" }); await loadMedia(); renderSidebar(); renderDoc(); toast({ kind: "warn", msg: "Midia excluida." }); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
    doc.querySelectorAll("[data-reproc]").forEach((b) => b.addEventListener("click", async (e) => { e.stopPropagation(); try { await api("/api/media/" + b.dataset.reproc + "/process", { method: "POST" }); await loadMedia(); renderDoc(); toast({ kind: "ok", msg: "Reprocessamento enfileirado." }); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
  }

  // Overlay generico reutilizando as classes .modal-overlay / .modal.
  // ============== P0: Tema de cores e Overlays (HUD) ============== //
  function overlayKindLabel(kind) {
    return { clock: "Relogio", weather: "Clima", news: "Noticias", promo: "Promocoes", text: "Texto", countdown: "Contagem", qrcode: "QR Code", rates: "Cotacoes" }[kind] || kind;
  }
  function themeColorRow(id, label, val) {
    const v = val || "";
    const safe = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(v) ? v : "#000000";
    return '<div class="field"><label>' + label + '</label><div class="row" style="gap:8px;align-items:center"><input type="color" id="th-' + id + '" value="' + safe + '" style="width:42px;height:32px;padding:0;border:0;background:none;cursor:pointer"/><input id="th-' + id + '-tx" value="' + esc(v) + '" placeholder="#RRGGBB ou vazio" style="flex:1"/></div></div>';
  }
  function themeFields(sc) {
    return themeColorRow("bg", "Fundo", sc.theme_bg) +
      themeColorRow("text", "Texto", sc.theme_text) +
      themeColorRow("accent", "Destaque", sc.theme_accent) +
      themeColorRow("tbg", "Fundo do ticker", sc.theme_ticker_bg) +
      themeColorRow("ttext", "Texto do ticker", sc.theme_ticker_text) +
      '<div class="row" style="gap:8px;margin-top:6px"><button class="btn primary block small" data-save-theme>' + ICONS.check + ' Salvar tema</button><button class="btn ghost block small" data-reset-theme>Redefinir</button></div>' +
      '<span class="hint" style="display:block;margin-top:6px">Deixe vazio para usar a cor padrao. As cores valem para textos, widgets e tickers desta tela.</span>';
  }
  function overlayListHtml(sc) {
    const list = (sc.overlays || []).slice().sort((a, b) => a.z_index - b.z_index);
    if (!list.length) return '<span class="hint" style="display:block;margin-bottom:4px">Nenhum overlay. Crie widgets fixos ou temporizados (estilo HUD de TV).</span>';
    return list.map((ov) =>
      '<div class="sched"><div class="row"><strong>' + esc(ov.name || overlayKindLabel(ov.kind)) + '</strong><span class="tag">' + overlayKindLabel(ov.kind) + (ov.enabled === false ? " (off)" : "") + '</span></div>' +
      '<div class="row" style="gap:6px;margin-top:4px"><span class="tag">' + esc(ov.position) + '</span><span class="tag">' + (ov.mode === "timed" ? ("a cada " + ov.interval_seconds + "s / " + ov.visible_seconds + "s") : "fixo") + '</span></div>' +
      '<div class="row" style="gap:8px;margin-top:7px"><button class="btn ghost block small" data-edit-overlay="' + ov.id + '">' + ICONS.settings + ' Editar</button><button class="btn danger block small" data-del-overlay="' + ov.id + '">' + ICONS.trash + ' Remover</button></div></div>'
    ).join("");
  }
  function parseOverlayText(ov) {
    return (ov && ov.content) ? ov.content : "";
  }
  function prefillWidget(kind, ov, modal) {
    if (!ov || !ov.content) return;
    let cfg = {};
    try { cfg = JSON.parse(ov.content) || {}; } catch (e) { cfg = {}; }
    const set = (id, v) => { const e = modal.querySelector(id); if (e != null && v != null) e.value = v; };
    if (cfg.title != null) set("#wf-title", cfg.title);
    if (kind === "clock") { set("#wf-format", cfg.format || "24h"); set("#wf-showdate", cfg.showDate === false ? "0" : "1"); }
    else if (kind === "weather") { set("#wf-city", cfg.city || ""); if (cfg.lat != null) set("#wf-lat", cfg.lat); if (cfg.lon != null) set("#wf-lon", cfg.lon); }
    else if (kind === "news") { set("#wf-feeds", (cfg.feeds || []).join("\n")); set("#wf-messages", (cfg.messages || []).join("\n")); set("#wf-speed", cfg.speed || 60); }
    else if (kind === "countdown") { set("#wf-target", cfg.target || ""); set("#wf-done", cfg.doneText || ""); }
    else if (kind === "qrcode") { set("#wf-data", cfg.data || cfg.url || ""); if (cfg.size != null) set("#wf-size", cfg.size); }
    else if (kind === "rates") { set("#wf-pairs", (cfg.pairs || []).join("\n")); }
    else if (kind === "promo") { set("#wf-products", (cfg.products || []).map((p) => [p.name, p.price, p.note].filter(Boolean).join(" | ")).join("\n")); set("#wf-speed", cfg.speed || 50); }
  }
  function openOverlayModal(sc, ov) {
    const editing = !!ov;
    const o = ov || {};
    const kinds = ["clock", "weather", "news", "promo", "countdown", "qrcode", "rates", "text"];
    const positions = [["top-left", "Sup. esquerda"], ["top", "Topo"], ["top-right", "Sup. direita"], ["left", "Esquerda"], ["center", "Centro"], ["right", "Direita"], ["bottom-left", "Inf. esquerda"], ["bottom", "Rodape"], ["bottom-right", "Inf. direita"]];
    let current = o.kind || "clock";
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    modal.setAttribute("role", "dialog"); modal.setAttribute("aria-modal", "true");
    const kindBtns = kinds.map((t) => '<button class="type-pick" data-okind="' + t + '">' + (ICONS[TYPE_ICON[t]] || ICONS.layout) + '<span>' + overlayKindLabel(t) + '</span></button>').join("");
    const posOpts = positions.map((p) => '<option value="' + p[0] + '">' + p[1] + '</option>').join("");
    modal.innerHTML =
      '<div class="modal-head"><span class="modal-ico">' + ICONS.layout + '</span><span class="modal-title">' + (editing ? "Editar overlay" : "Novo overlay (HUD)") + '</span></div>' +
      '<div class="modal-body">' +
        '<label class="mm-label">1. Tipo de widget</label><div class="type-grid">' + kindBtns + '</div>' +
        '<div class="field"><label>2. Nome</label><input id="ov-name" value="' + esc(o.name || "") + '" placeholder="Ex.: Relogio do topo"/></div>' +
        '<div id="ov-dynamic"></div>' +
        '<div class="row" style="gap:10px"><div class="field grow"><label>Posicao</label><select id="ov-pos">' + posOpts + '</select></div><div class="field grow"><label>Exibicao</label><select id="ov-mode"><option value="fixed">Fixo (sempre visivel)</option><option value="timed">Temporizado (aparece/some)</option></select></div></div>' +
        '<div class="row" style="gap:10px" id="ov-timing"><div class="field grow"><label>Intervalo (s)</label><input id="ov-interval" type="number" value="' + (o.interval_seconds || 300) + '"/></div><div class="field grow"><label>Duracao visivel (s)</label><input id="ov-visible" type="number" value="' + (o.visible_seconds || 15) + '"/></div></div>' +
        '<div class="row" style="gap:10px"><div class="field grow"><label>Largura (% tela, 0=auto)</label><input id="ov-width" type="number" value="' + (o.width || 0) + '"/></div><div class="field grow"><label>Altura (% tela, 0=auto)</label><input id="ov-height" type="number" value="' + (o.height || 0) + '"/></div></div>' +
        '<div class="row" style="gap:10px"><div class="field grow"><label>Opacidade (0.1-1)</label><input id="ov-opacity" type="number" step="0.1" min="0.1" max="1" value="' + (o.opacity != null ? o.opacity : 1) + '"/></div><div class="field grow"><label>Camada (z-index)</label><input id="ov-z" type="number" value="' + (o.z_index != null ? o.z_index : 50) + '"/></div></div>' +
        '<div class="switch"><span>Ativo</span><input id="ov-enabled" type="checkbox" ' + (o.enabled === false ? "" : "checked") + '/></div>' +
      '</div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Cancelar</button><button class="btn primary" data-save>' + ICONS.check + ' ' + (editing ? "Salvar" : "Criar") + '</button></div>';
    const ui = buildOverlay(modal);
    const dyn = modal.querySelector("#ov-dynamic");
    const renderDynamic = () => {
      if (current === "text") {
        dyn.innerHTML = '<div class="field"><label>3. Texto</label><textarea id="ov-text" rows="3" placeholder="Texto exibido no overlay">' + esc(parseOverlayText(o)) + '</textarea></div>';
      } else {
        dyn.innerHTML = widgetFormHtml(current);
        prefillWidget(current, o, modal);
      }
    };
    const syncKindBtns = () => modal.querySelectorAll("[data-okind]").forEach((b) => b.classList.toggle("active", b.dataset.okind === current));
    modal.querySelectorAll("[data-okind]").forEach((b) => b.addEventListener("click", () => { current = b.dataset.okind; syncKindBtns(); renderDynamic(); }));
    modal.querySelector("#ov-pos").value = o.position || "bottom";
    modal.querySelector("#ov-mode").value = o.mode || "fixed";
    const timing = modal.querySelector("#ov-timing");
    const syncTiming = () => { timing.style.display = modal.querySelector("#ov-mode").value === "timed" ? "" : "none"; };
    modal.querySelector("#ov-mode").addEventListener("change", syncTiming);
    syncKindBtns(); renderDynamic(); syncTiming();
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("[data-save]").addEventListener("click", async () => {
      let content = "";
      if (current === "text") { content = (modal.querySelector("#ov-text").value || "").trim(); }
      else { content = JSON.stringify(collectWidgetConfig(current, modal)); }
      const body = {
        name: (modal.querySelector("#ov-name").value || "").trim() || overlayKindLabel(current),
        kind: current,
        content: content,
        position: modal.querySelector("#ov-pos").value,
        mode: modal.querySelector("#ov-mode").value,
        interval_seconds: Number(modal.querySelector("#ov-interval").value) || 300,
        visible_seconds: Number(modal.querySelector("#ov-visible").value) || 15,
        width: Number(modal.querySelector("#ov-width").value) || 0,
        height: Number(modal.querySelector("#ov-height").value) || 0,
        opacity: Math.min(1, Math.max(0.1, Number(modal.querySelector("#ov-opacity").value) || 1)),
        z_index: Number(modal.querySelector("#ov-z").value) || 50,
        enabled: modal.querySelector("#ov-enabled").checked,
      };
      try {
        if (editing) { await api("/api/screens/" + sc.id + "/overlays/" + ov.id, { method: "PATCH", body: JSON.stringify(body) }); }
        else { await api("/api/screens/" + sc.id + "/overlays", { method: "POST", body: JSON.stringify(body) }); }
        ui.close(); await loadScreens(); renderInspector(); toast({ kind: "ok", msg: editing ? "Overlay atualizado." : "Overlay criado." });
      } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
  }

  function buildOverlay(modal) {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add("show"));
    let closed = false;
    function onKey(e) { if (e.key === "Escape") { e.preventDefault(); close(); } }
    const close = () => { if (closed) return; closed = true; overlay.classList.remove("show"); document.removeEventListener("keydown", onKey, true); setTimeout(() => overlay.remove(), 200); };
    overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
    document.addEventListener("keydown", onKey, true);
    return { overlay, close };
  }

  // Modal guiado de Nova midia: escolha de tipo, campos contextuais e drag-and-drop.
  // ---- v17: helpers de musica de fundo, menu rapido e assistentes ---- //

  /** Garante que a zona tenha uma playlist padrao, criando uma se necessario. */
  async function ensureZonePlaylist(z) {
    if (z.default_playlist_id) return z.default_playlist_id;
    const sc = screen();
    const baseName = (sc ? sc.name + " - " : "") + (z.name || "Zona");
    const pl = await api("/api/playlists", { method: "POST", body: JSON.stringify({ name: baseName }) });
    await api("/api/screens/" + state.activeScreenId + "/zones/" + z.id, { method: "PATCH", body: JSON.stringify({ default_playlist_id: pl.id }) });
    z.default_playlist_id = pl.id;
    await loadPlaylists();
    return pl.id;
  }

  /** Adiciona uma midia ja criada a playlist padrao da zona. */
  async function addMediaToZonePlaylist(z, media, fit) {
    const plId = await ensureZonePlaylist(z);
    warnIfLowRes(media);
    const isVideo = media.type === "video";
    await api("/api/playlists/" + plId + "/items", { method: "POST", body: JSON.stringify({ media_id: media.id, duration: isVideo ? 30 : 12, fit: fit || "cover", transition: "fade", muted: !isVideo }) });
    await loadPlaylists(); await loadScreens();
  }

  /** Menu rapido (dropdown / clique direito) de uma zona. */
  function quickAddToZone(zoneId, kind) {
    const sc = screen();
    const z = sc ? sc.zones.find((x) => x.id === zoneId) : null;
    if (!z) { toast({ kind: "warn", msg: "Selecione uma zona primeiro." }); return; }
    if (kind === "music") { chooseScreenMusic(); return; }
    const titles = { text: "Criar texto", image: "Anexar foto", video: "Anexar video", url: "Adicionar link / YouTube", "text-music": "Texto com musica de fundo", clock: "Adicionar relogio", weather: "Adicionar clima", news: "Adicionar ticker de noticias", promo: "Adicionar ticker de promocoes" };
    const lock = (kind !== "url");
    const presetType = (kind === "text-music") ? "text" : (kind === "url" ? "youtube" : kind);
    openMediaModal({ presetType: presetType, lockType: lock, title: titles[kind] || "Adicionar conteudo", onCreated: async (media) => {
      try {
        await addMediaToZonePlaylist(z, media);
        state.selectedZoneId = z.id; renderAll();
        if (kind === "text-music") { toast({ kind: "ok", msg: "Texto adicionado. Agora escolha a musica de fundo." }); chooseScreenMusic(); }
        else { toast({ kind: "ok", msg: "Conteudo adicionado a zona." }); }
      } catch (err) { toast({ kind: "err", msg: err.message }); }
    } });
  }

  /** Menu de contexto posicionado (clique direito na zona, dentro do canvas). */
  function closeCtxPop() { const m = document.getElementById("ctx-pop"); if (m) m.remove(); }
  function openCtxPop(x, y, items) {
    closeCtxPop();
    const menu = document.createElement("div");
    menu.className = "ctx-menu";
    menu.id = "ctx-pop";
    menu.innerHTML = items.map((o, i) => o.sep ? '<div class="ctx-sep"></div>' : ('<button class="ctx-item' + (o.danger ? " danger" : "") + '" data-ci="' + i + '">' + (o.ic ? ICONS[o.ic] : "") + '<span>' + o.lb + '</span></button>')).join("");
    document.body.appendChild(menu);
    const w = 240; const h = menu.offsetHeight || 280;
    menu.style.left = Math.min(x, window.innerWidth - w - 8) + "px";
    menu.style.top = Math.min(y, window.innerHeight - h - 8) + "px";
    items.forEach((o, i) => { if (o.sep || !o.fn) return; const b = menu.querySelector('[data-ci="' + i + '"]'); if (b) b.addEventListener("click", () => { closeCtxPop(); o.fn(); }); });
    setTimeout(() => document.addEventListener("pointerdown", function onAway(ev) { if (!menu.contains(ev.target)) { closeCtxPop(); document.removeEventListener("pointerdown", onAway); } }), 0);
  }
  async function zoneMenuAction(zoneId, action) {
    const sc = screen(); if (!sc) return;
    const z = zoneOf(zoneId); if (!z) return;
    try {
      if (action === "rename") {
        const name = await promptDialog({ title: "Renomear zona", message: "Novo nome da zona:", icon: "layout", defaultValue: z.name, confirmText: "Salvar" });
        if (!name) return;
        await api("/api/screens/" + sc.id + "/zones/" + z.id, { method: "PATCH", body: JSON.stringify({ name: name }) });
      } else if (action === "dup") {
        await api("/api/screens/" + sc.id + "/zones", { method: "POST", body: JSON.stringify({ name: z.name + " (copia)", x: clamp(z.x + 5, 0, 90), y: clamp(z.y + 5, 0, 90), width: z.width, height: z.height, z_index: (z.z_index || 0) + 1, default_playlist_id: z.default_playlist_id }) });
      } else if (action === "front") {
        const maxZ = sc.zones.reduce((m, zz) => Math.max(m, zz.z_index || 0), 0);
        await api("/api/screens/" + sc.id + "/zones/" + z.id, { method: "PATCH", body: JSON.stringify({ z_index: maxZ + 1 }) });
      } else if (action === "back") {
        const minZ = sc.zones.reduce((m, zz) => Math.min(m, zz.z_index || 0), 0);
        await api("/api/screens/" + sc.id + "/zones/" + z.id, { method: "PATCH", body: JSON.stringify({ z_index: minZ - 1 }) });
      } else if (action === "del") {
        const ok = await confirmDialog({ title: "Excluir zona", message: 'Excluir a zona "' + z.name + '"? Esta acao nao pode ser desfeita.', icon: "trash", confirmText: "Excluir" });
        if (!ok) return;
        await api("/api/screens/" + sc.id + "/zones/" + z.id, { method: "DELETE" });
      }
      await loadScreens(); renderAll(); toast({ kind: "ok", msg: "Zona atualizada." });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }
  function openStageMenu(x, y, px, py) {
    const sc = screen(); if (!sc) return;
    openCtxPop(x, y, [
      { ic: "plus", lb: "Nova zona aqui", fn: () => createZoneFlow(px, py, 40, 30) },
      { ic: "layout", lb: "Layout: 2 zonas (50/50)", fn: () => applyLayoutPreset("split2") },
      { ic: "layout", lb: "Layout: 3 faixas", fn: () => applyLayoutPreset("rows3") },
      { ic: "layout", lb: "Layout: principal + barra", fn: () => applyLayoutPreset("main-bar") },
      { sep: true },
      { ic: "tag", lb: "Rodape de ticker (promo)", fn: () => addTickerFooter(sc) },
    ]);
  }
  // ---- v30: criacao guiada de zona (nome + tipo + ajuste) ---- //
  const ZONE_CONTENT_TYPES = [
    { v: "empty", lb: "Vazia (defino o conteudo depois)" },
    { v: "video", lb: "Video (enviar arquivo)" },
    { v: "url", lb: "YouTube / link de video" },
    { v: "image", lb: "Imagem" },
    { v: "text", lb: "Texto" },
    { v: "clock", lb: "Relogio" },
    { v: "weather", lb: "Clima" },
    { v: "news", lb: "Ticker de noticias" },
    { v: "promo", lb: "Ticker de promocoes" },
  ];
  function createZoneDialog(defaults) {
    const d = defaults || {};
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.setAttribute("role", "dialog");
      const typeOpts = ZONE_CONTENT_TYPES.map((t) => '<option value="' + t.v + '">' + t.lb + '</option>').join("");
      modal.innerHTML =
        '<div class="modal-head"><span class="modal-ico">' + (ICONS.layout || ICONS.info) + '</span><span class="modal-title">Nova zona</span></div>' +
        '<div class="modal-body" style="text-align:left">' +
          '<div class="field"><label>Nome da zona</label><input id="cz-name" class="modal-input" value="' + esc(d.name || "") + '" placeholder="Ex.: Video principal"/></div>' +
          '<div class="field" style="margin-top:10px"><label>Conteudo</label><select id="cz-type" class="modal-input">' + typeOpts + '</select></div>' +
          '<div class="field" id="cz-fit-wrap" style="margin-top:10px"><label>Ajuste do conteudo na zona</label><select id="cz-fit" class="modal-input"><option value="cover">Preencher a zona (cover)</option><option value="contain">Conter inteiro (contain)</option><option value="fill">Esticar (fill)</option></select><span class="hint">"Preencher" evita barras pretas; "conter" mostra a midia inteira.</span></div>' +
        '</div>' +
        '<div class="modal-actions"><button class="btn ghost" data-cz-cancel>Cancelar</button><button class="btn primary" data-cz-ok>Criar zona</button></div>';
      overlay.appendChild(modal);
      document.body.appendChild(overlay);
      requestAnimationFrame(() => overlay.classList.add("show"));
      const typeSel = modal.querySelector("#cz-type");
      const fitWrap = modal.querySelector("#cz-fit-wrap");
      const syncFit = () => { const t = typeSel.value; fitWrap.style.display = (t === "video" || t === "url" || t === "image") ? "" : "none"; };
      typeSel.addEventListener("change", syncFit); syncFit();
      let closed = false;
      const close = (res) => { if (closed) return; closed = true; overlay.classList.remove("show"); document.removeEventListener("keydown", onKey, true); setTimeout(() => overlay.remove(), 200); resolve(res); };
      const onKey = (e) => { if (e.key === "Escape") { e.preventDefault(); close(null); } else if (e.key === "Enter" && e.target && e.target.id === "cz-name") { e.preventDefault(); doOk(); } };
      const doOk = () => { const name = modal.querySelector("#cz-name").value.trim(); close({ name: name, type: typeSel.value, fit: modal.querySelector("#cz-fit").value }); };
      modal.querySelector("[data-cz-cancel]").addEventListener("click", () => close(null));
      modal.querySelector("[data-cz-ok]").addEventListener("click", doOk);
      overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(null); });
      document.addEventListener("keydown", onKey, true);
      setTimeout(() => { const n = modal.querySelector("#cz-name"); if (n) { n.focus(); n.select(); } }, 30);
    });
  }
  function addContentToNewZone(z, type, fit) {
    const titles = { video: "Anexar video", url: "Adicionar YouTube / link", image: "Anexar imagem", text: "Criar texto", clock: "Adicionar relogio", weather: "Adicionar clima", news: "Ticker de noticias", promo: "Ticker de promocoes" };
    const presetType = (type === "url") ? "youtube" : type;
    const lock = (type !== "url");
    openMediaModal({ presetType: presetType, lockType: lock, title: titles[type] || "Adicionar conteudo", onCreated: async (media) => {
      try { await addMediaToZonePlaylist(z, media, fit); state.selectedZoneId = z.id; renderAll(); toast({ kind: "ok", msg: "Conteudo adicionado a zona." }); }
      catch (err) { toast({ kind: "err", msg: err.message }); }
    } });
  }
  async function createZoneFlow(x, y, w, h) {
    const sc = screen();
    if (!sc) { toast({ kind: "warn", msg: "Selecione uma tela primeiro." }); return; }
    const n = sc.zones.length + 1;
    const res = await createZoneDialog({ name: "Zona " + n });
    if (!res) return;
    const name = res.name || ("Zona " + n);
    try {
      const maxZ = sc.zones.reduce((m, z) => Math.max(m, z.z_index || 0), 0);
      await api("/api/screens/" + sc.id + "/zones", { method: "POST", body: JSON.stringify({ name: name, x: clamp(x, 0, 100 - w), y: clamp(y, 0, 100 - h), width: w, height: h, z_index: maxZ + 1 }) });
      await loadScreens();
      const s2 = screen();
      const z = s2 && s2.zones.length ? s2.zones[s2.zones.length - 1] : null;
      if (z) state.selectedZoneId = z.id;
      renderAll();
      toast({ kind: "ok", msg: 'Zona "' + name + '" criada.' });
      if (z && res.type && res.type !== "empty") { addContentToNewZone(z, res.type, res.fit); }
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }
  async function createZoneAt(x, y, w, h, name) {
    const sc = screen(); if (!sc) return;
    try {
      const maxZ = sc.zones.reduce((m, z) => Math.max(m, z.z_index || 0), 0);
      await api("/api/screens/" + sc.id + "/zones", { method: "POST", body: JSON.stringify({ name: name || "Nova zona", x: clamp(x, 0, 100 - w), y: clamp(y, 0, 100 - h), width: w, height: h, z_index: maxZ + 1 }) });
      await loadScreens(); const s2 = screen(); if (s2 && s2.zones.length) state.selectedZoneId = s2.zones[s2.zones.length - 1].id; renderAll(); toast({ kind: "ok", msg: "Zona criada." });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }
  async function applyLayoutPreset(kind) {
    const sc = screen(); if (!sc) return;
    let zones = [];
    if (kind === "split2") zones = [{ name: "Esquerda", x: 0, y: 0, width: 50, height: 100 }, { name: "Direita", x: 50, y: 0, width: 50, height: 100 }];
    else if (kind === "rows3") zones = [{ name: "Topo", x: 0, y: 0, width: 100, height: 33 }, { name: "Meio", x: 0, y: 33, width: 100, height: 34 }, { name: "Base", x: 0, y: 67, width: 100, height: 33 }];
    else if (kind === "main-bar") zones = [{ name: "Principal", x: 0, y: 0, width: 100, height: 80 }, { name: "Barra", x: 0, y: 80, width: 100, height: 20 }];
    if (!zones.length) return;
    const ok = await confirmDialog({ title: "Aplicar layout", message: "Adicionar " + zones.length + " zonas deste layout a tela?", icon: "layout", confirmText: "Aplicar" });
    if (!ok) return;
    try {
      let z0 = sc.zones.reduce((m, z) => Math.max(m, z.z_index || 0), 0);
      for (const def of zones) { z0 += 1; await api("/api/screens/" + sc.id + "/zones", { method: "POST", body: JSON.stringify(Object.assign({ z_index: z0 }, def)) }); }
      await loadScreens(); renderAll(); toast({ kind: "ok", msg: "Layout aplicado." });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }
  function bindTimeline() {
    const pl = timelinePlaylist(); if (!pl) return;
    document.querySelectorAll("#bottom-content [data-tl]").forEach((el) => {
      el.addEventListener("contextmenu", (e) => { e.preventDefault(); openTimelineItemMenu(e.clientX, e.clientY, pl, el.dataset.tl); });
      el.addEventListener("dblclick", (e) => { e.preventDefault(); openTimelineItemMenu(e.clientX, e.clientY, pl, el.dataset.tl); });
    });
  }
  function openTimelineItemMenu(x, y, pl, itemId) {
    const it = pl.items.find((i) => String(i.id) === String(itemId)); if (!it) return;
    openCtxPop(x, y, [
      { ic: "clock", lb: "Editar duracao (" + it.duration + "s)", fn: async () => { const v = await promptDialog({ title: "Duracao do item", message: "Tempo em segundos:", icon: "clock", defaultValue: String(it.duration), confirmText: "Salvar" }); const n = parseInt(v, 10); if (n > 0) updateItem(pl.id, it.id, { duration: n }); } },
      { ic: "music", lb: it.muted ? "Ativar som" : "Silenciar", fn: () => updateItem(pl.id, it.id, { muted: !it.muted }) },
      { ic: "refresh", lb: it.play_full ? "Nao tocar completo" : "Tocar completo (video/audio/YouTube)", fn: () => updateItem(pl.id, it.id, { play_full: !it.play_full }) },
      { sep: true },
      { ic: "up", lb: "Mover para esquerda", fn: () => moveItem(pl, it.id, -1) },
      { ic: "down", lb: "Mover para direita", fn: () => moveItem(pl, it.id, 1) },
      { sep: true },
      { ic: "trash", lb: "Remover item", danger: true, fn: async () => { try { await api("/api/playlists/" + pl.id + "/items/" + it.id, { method: "DELETE" }); await loadPlaylists(); renderSidebar(); renderDoc(); renderBottom(); } catch (err) { toast({ kind: "err", msg: err.message }); } } },
    ]);
  }
  function openZoneQuickMenu(x, y, zoneId) {
    closeZoneQuickMenu();
    const z = zoneOf(zoneId);
    const opts = [
      { k: "text", ic: "text", lb: "Criar texto" },
      { k: "image", ic: "image", lb: "Anexar foto" },
      { k: "video", ic: "video", lb: "Anexar video" },
      { k: "url", ic: "link", lb: "Adicionar link / YouTube" },
      { k: "text-music", ic: "music", lb: "Texto com musica de fundo" },
      { k: "music", ic: "music", lb: "Musica de fundo (tela)" },
      { k: "clock", ic: "clock", lb: "Relogio / data" },
      { k: "weather", ic: "sun", lb: "Clima (tempo)" },
      { k: "news", ic: "text", lb: "Ticker de noticias" },
      { k: "promo", ic: "tag", lb: "Ticker de promocoes" },
    ];
    const menu = document.createElement("div");
    menu.className = "ctx-menu";
    menu.id = "zone-ctx";
    menu.innerHTML = '<div class="ctx-head">' + ICONS.layout + '<span>' + esc(z ? z.name : "Zona") + '</span></div>'
      + opts.map((o) => '<button class="ctx-item" data-qa="' + o.k + '">' + ICONS[o.ic] + '<span>' + o.lb + '</span></button>').join("")
      + '<div class="ctx-sep"></div>'
      + '<button class="ctx-item" data-zm="rename">' + ICONS.text + '<span>Renomear zona</span></button>'
      + '<button class="ctx-item" data-zm="dup">' + ICONS.copy + '<span>Duplicar zona</span></button>'
      + '<button class="ctx-item" data-zm="front">' + ICONS.up + '<span>Trazer para frente</span></button>'
      + '<button class="ctx-item" data-zm="back">' + ICONS.down + '<span>Enviar para tras</span></button>'
      + '<button class="ctx-item danger" data-zm="del">' + ICONS.trash + '<span>Excluir zona</span></button>';
    document.body.appendChild(menu);
    const w = 240; const h = menu.offsetHeight || 280;
    menu.style.left = Math.min(x, window.innerWidth - w - 8) + "px";
    menu.style.top = Math.min(y, window.innerHeight - h - 8) + "px";
    menu.querySelectorAll("[data-qa]").forEach((b) => b.addEventListener("click", () => { const k = b.dataset.qa; closeZoneQuickMenu(); quickAddToZone(zoneId, k); }));
    menu.querySelectorAll("[data-zm]").forEach((b) => b.addEventListener("click", () => { const a = b.dataset.zm; closeZoneQuickMenu(); zoneMenuAction(zoneId, a); }));
  }
  function closeZoneQuickMenu() { const m = document.getElementById("zone-ctx"); if (m) m.remove(); }

  /** Cria uma zona de rodape fixa (15% da altura) com um ticker de promocoes (1 clique). */
  async function addTickerFooter(sc) {
    if (!sc) { toast({ kind: "warn", msg: "Selecione uma tela primeiro." }); return; }
    try {
      const maxZ = sc.zones.reduce((m, z) => Math.max(m, z.z_index || 0), 0);
      const newZone = await api("/api/screens/" + sc.id + "/zones", { method: "POST", body: JSON.stringify({ name: "Ticker (rodape)", x: 0, y: 85, width: 100, height: 15, z_index: maxZ + 1 }) });
      const pl = await api("/api/playlists", { method: "POST", body: JSON.stringify({ name: sc.name + " - Ticker" }) });
      const config = JSON.stringify({ title: "Promocoes", products: [{ name: "Edite suas ofertas aqui", price: "", note: "" }], speed: 50 });
      const created = await api("/api/media/bulk", { method: "POST", body: JSON.stringify({ items: [{ name: "Ticker de promocoes", type: "promo", content: config }] }) });
      const m = Array.isArray(created) ? created[0] : created;
      await api("/api/playlists/" + pl.id + "/items", { method: "POST", body: JSON.stringify({ media_id: m.id, duration: 30, fit: "cover", transition: "none", muted: true }) });
      await api("/api/screens/" + sc.id + "/zones/" + newZone.id, { method: "PATCH", body: JSON.stringify({ default_playlist_id: pl.id }) });
      await loadMedia(); await loadPlaylists(); await loadScreens();
      state.activeScreenId = sc.id; state.selectedZoneId = newZone.id;
      renderAll();
      toast({ kind: "ok", msg: "Rodape de ticker adicionado. Edite os produtos na midia criada." });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  /** Painel de saude das telas: online/offline, ultima reproducao e proof-of-play. */
  async function openHealthPanel() {
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    modal.innerHTML = '<div class="modal-head"><span class="modal-ico">' + ICONS.wifi + '</span><span class="modal-title">Painel de saude das telas</span></div>' +
      '<div class="modal-body" id="hp-body"><p class="hint">Carregando...</p></div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Fechar</button><button class="btn ghost" data-refresh>' + ICONS.refresh + ' Atualizar</button></div>';
    const ui = buildOverlay(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    const body = modal.querySelector("#hp-body");
    const fmtAgo = (sec) => { if (sec == null) return "nunca"; if (sec < 60) return sec + "s atras"; if (sec < 3600) return Math.floor(sec / 60) + " min atras"; if (sec < 86400) return Math.floor(sec / 3600) + " h atras"; return Math.floor(sec / 86400) + " d atras"; };
    const load = async () => {
      body.innerHTML = '<p class="hint">Carregando...</p>';
      try {
        const rows = await loadHealth();
        let pop = [];
        try { pop = await loadProofOfPlay(7); } catch (e) { pop = []; }
        const online = rows.filter((r) => r.online).length;
        const hrows = rows.length ? rows.map((r) => '<tr><td>' + (r.online ? '<span class="tag" style="color:var(--green)">online</span>' : '<span class="tag" style="color:var(--faint)">offline</span>') + '</td><td>' + esc(r.name) + '</td><td class="mono">' + fmtAgo(r.seconds_since_seen) + '</td><td class="mono">' + r.connected_players + '</td></tr>').join("") : '<tr><td colspan="4" class="empty">Nenhuma tela cadastrada.</td></tr>';
        const prows = (pop && pop.length) ? pop.slice(0, 15).map((r) => '<tr><td>' + esc(r.media_name || "?") + '</td><td class="mono">' + r.plays + '</td><td class="mono">' + Math.round((r.total_seconds || 0) / 60) + ' min</td></tr>').join("") : '<tr><td colspan="3" class="empty">Sem dados de exibicao nos ultimos 7 dias.</td></tr>';
        body.innerHTML = '<p class="hint" style="margin-top:0">Telas online: <b>' + online + '/' + rows.length + '</b></p>' +
          '<table class="set-table"><thead><tr><th>Status</th><th>Tela</th><th>Ultima reproducao</th><th>Players</th></tr></thead><tbody>' + hrows + '</tbody></table>' +
          '<label class="mm-label">Proof-of-play (ultimos 7 dias)</label>' +
          '<table class="set-table"><thead><tr><th>Midia</th><th>Exibicoes</th><th>Tempo</th></tr></thead><tbody>' + prows + '</tbody></table>';
      } catch (err) { body.innerHTML = '<p class="empty">' + esc(err.message) + '</p>'; }
    };
    modal.querySelector("[data-refresh]").addEventListener("click", load);
    load();
  }

  // ----------------------- Console Super Admin --------------------- //
  let saTab = "empresas";
  const SA_TABS = [
    { id: "overview", label: "Visao geral" },
    { id: "empresas", label: "Empresas" },
  ];

  /** Abre o console dedicado do super admin (tela cheia). */
  function openSuperAdmin() {
    if (!(state.user && state.user.is_super_admin)) { toast({ kind: "warn", msg: "Acesso restrito ao super admin." }); return; }
    closeMenu();
    $("login").classList.add("hidden");
    $("ide").classList.add("hidden");
    $("superadmin").classList.remove("hidden");
    renderSuperAdmin();
  }

  /** Fecha o console e volta para o Studio. */
  function closeSuperAdmin() {
    $("superadmin").classList.add("hidden");
    $("ide").classList.remove("hidden");
    renderAll();
  }

  function renderSaTabs() {
    const host = $("sa-tabs");
    if (!host) return;
    host.innerHTML = SA_TABS.map((t) => '<button class="sa-tab ' + (t.id === saTab ? "active" : "") + '" data-sa-tab="' + t.id + '">' + t.label + '</button>').join("");
    host.querySelectorAll("[data-sa-tab]").forEach((b) => b.addEventListener("click", () => { saTab = b.dataset.saTab; renderSuperAdmin(); }));
  }

  async function renderSuperAdmin() {
    renderSaTabs();
    const body = $("sa-body");
    if (!body) return;
    body.innerHTML = '<p class="hint">Carregando...</p>';
    let companies = [];
    try { companies = await loadCompanies(); state.companies = companies; }
    catch (err) { body.innerHTML = '<p class="empty">' + esc(err.message) + '</p>'; return; }
    if (saTab === "overview") renderSaOverview(body, companies);
    else renderSaCompanies(body, companies);
  }

  function saSwitcher(id, companies) {
    const curLabel = state.activeCompanyId == null ? "Todas (visao global)" : ((companies.find((c) => c.id === state.activeCompanyId) || {}).name || "?");
    return '<div class="field"><label>Empresa em foco</label><select id="' + id + '"><option value="">Todas (visao global)</option>' + companies.map((c) => '<option value="' + c.id + '"' + (c.id === state.activeCompanyId ? " selected" : "") + '>' + esc(c.name) + '</option>').join("") + '</select></div><span class="hint">Em foco: <b>' + esc(curLabel) + '</b>. Define o que voce ve e edita ao abrir o Studio.</span>';
  }

  function bindSaSwitcher(body, id) {
    const sw = body.querySelector("#" + id);
    if (sw) sw.addEventListener("change", async () => { state.activeCompanyId = sw.value ? Number(sw.value) : null; await loadAll(); toast({ kind: "ok", msg: "Empresa em foco alterada." }); renderSuperAdmin(); });
  }

  function renderSaOverview(body, companies) {
    const sum = (k) => companies.reduce((a, c) => a + (c[k] || 0), 0);
    const cards = [ { k: "Empresas", v: companies.length }, { k: "Telas", v: sum("screens") }, { k: "Midias", v: sum("media") }, { k: "Playlists", v: sum("playlists") }, { k: "Usuarios", v: sum("users") } ];
    body.innerHTML = '<div class="sa-cards">' + cards.map((c) => '<div class="sa-card"><div class="k">' + c.k + '</div><div class="v">' + c.v + '</div></div>').join("") + '</div>' +
      '<div class="sa-panel"><h3 class="sa-section-title">Empresa em foco</h3>' + saSwitcher("sa-switch", companies) +
      '<div style="margin-top:14px"><button class="btn primary" id="sa-go-studio">Abrir Studio</button></div></div>';
    bindSaSwitcher(body, "sa-switch");
    const go = body.querySelector("#sa-go-studio"); if (go) go.addEventListener("click", closeSuperAdmin);
  }

  function renderSaCompanies(body, companies) {
    const rows = companies.map((c) => '<tr><td>' + esc(c.name) + (c.is_active ? '' : ' <span class="tag">inativa</span>') + '</td><td class="mono">' + c.users + '</td><td class="mono">' + c.screens + '</td><td class="mono">' + c.media + '</td><td class="mono">' + c.playlists + '</td><td><button class="btn ghost small" data-enter="' + c.id + '" title="Abrir Studio desta empresa">' + ICONS.eye + '</button><button class="btn ghost small" data-logo="' + c.id + '" title="Enviar logo">' + ICONS.upload + '</button><button class="btn ghost small" data-emerg="' + c.id + '" title="Mensagem de emergencia">' + ICONS.shield + '</button><button class="btn ghost small" data-edit="' + c.id + '" title="Renomear">' + ICONS.settings + '</button><button class="btn danger small" data-delc="' + c.id + '" title="Excluir">' + ICONS.trash + '</button></td></tr>').join("");
    body.innerHTML = '<div class="sa-panel"><h3 class="sa-section-title">Empresa em foco</h3>' + saSwitcher("sa-switch2", companies) + '</div>' +
      '<div class="sa-panel"><h3 class="sa-section-title">Empresas (clientes)</h3><table class="set-table"><thead><tr><th>Empresa</th><th>Usuarios</th><th>Telas</th><th>Midias</th><th>Playlists</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="sa-panel"><h3 class="sa-section-title">Nova empresa</h3>' +
      '<div class="row" style="gap:10px"><div class="field grow"><label>Nome</label><input id="nc-name"/></div><div class="field"><label>Cor (hex)</label><input id="nc-color" placeholder="#7aa2f7"/></div></div>' +
      '<div class="row" style="gap:10px"><div class="field grow"><label>Admin (opcional)</label><input id="nc-admin"/></div><div class="field grow"><label>Senha do admin</label><input type="password" id="nc-pass"/></div></div>' +
      '<button class="btn primary" id="nc-add">' + ICONS.plus + ' Criar empresa</button></div>';
    bindSaSwitcher(body, "sa-switch2");
    body.querySelector("#nc-add").addEventListener("click", async () => {
      const name = body.querySelector("#nc-name").value.trim();
      if (name.length < 2) { toast({ kind: "warn", msg: "Informe o nome da empresa." }); return; }
      const payload = { name: name, primary_color: body.querySelector("#nc-color").value.trim() || null };
      const au = body.querySelector("#nc-admin").value.trim(), ap = body.querySelector("#nc-pass").value;
      if (au && ap) { payload.admin_username = au; payload.admin_password = ap; }
      try { await createCompany(payload); toast({ kind: "ok", msg: "Empresa criada." }); renderSuperAdmin(); } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
    body.querySelectorAll("[data-enter]").forEach((b) => b.addEventListener("click", async () => { state.activeCompanyId = Number(b.dataset.enter); await loadAll(); toast({ kind: "ok", msg: "Abrindo Studio da empresa." }); closeSuperAdmin(); }));
    body.querySelectorAll("[data-delc]").forEach((b) => b.addEventListener("click", async () => { const id = Number(b.dataset.delc); if (!(await confirmDialog({ title: "Excluir empresa", message: "Remover a empresa e TODO o seu conteudo (telas, midias, playlists, usuarios)? Esta acao nao pode ser desfeita.", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await deleteCompany(id); if (state.activeCompanyId === id) { state.activeCompanyId = null; await loadAll(); } toast({ kind: "warn", msg: "Empresa removida." }); renderSuperAdmin(); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
    body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", async () => { const id = Number(b.dataset.edit); const c = companies.find((x) => x.id === id); const name = await promptDialog({ title: "Renomear empresa", message: "Novo nome da empresa:", icon: "settings", defaultValue: c ? c.name : "", confirmText: "Salvar" }); if (!name) return; try { await updateCompany(id, { name: name }); toast({ kind: "ok", msg: "Empresa atualizada." }); await refreshBranding(); renderSuperAdmin(); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
    body.querySelectorAll("[data-logo]").forEach((b) => b.addEventListener("click", () => { const id = Number(b.dataset.logo); const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*"; inp.addEventListener("change", async () => { if (!inp.files || !inp.files[0]) return; try { await uploadCompanyLogo(id, inp.files[0]); toast({ kind: "ok", msg: "Logo atualizado." }); await refreshBranding(); renderSuperAdmin(); } catch (err) { toast({ kind: "err", msg: err.message }); } }); inp.click(); }));
    body.querySelectorAll("[data-emerg]").forEach((b) => b.addEventListener("click", () => { const id = Number(b.dataset.emerg); const c = companies.find((x) => x.id === id); emergencyDialog(c); }));
  }

  /** Painel de super admin: gestao de empresas (clientes) e troca de empresa em foco. */
  async function openCompaniesPanel() {
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    modal.innerHTML = '<div class="modal-head"><span class="modal-ico">' + ICONS.folder + '</span><span class="modal-title">Empresas (super admin)</span></div>' +
      '<div class="modal-body" id="cp-body"><p class="hint">Carregando...</p></div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Fechar</button></div>';
    const ui = buildOverlay(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    const body = modal.querySelector("#cp-body");
    const render = async () => {
      body.innerHTML = '<p class="hint">Carregando...</p>';
      try {
        const companies = await loadCompanies();
        state.companies = companies;
        const curLabel = state.activeCompanyId == null ? "Todas (visao global)" : ((companies.find((c) => c.id === state.activeCompanyId) || {}).name || "?");
        const switcher = '<div class="field"><label>Empresa em foco</label><select id="cp-switch"><option value="">Todas (visao global)</option>' + companies.map((c) => '<option value="' + c.id + '"' + (c.id === state.activeCompanyId ? " selected" : "") + '>' + esc(c.name) + '</option>').join("") + '</select></div><span class="hint" style="display:block;margin:-4px 0 12px">Em foco: <b>' + esc(curLabel) + '</b>. Trocar a empresa afeta todo o painel (telas, midias, playlists).</span>';
        const rows = companies.map((c) => '<tr><td>' + esc(c.name) + (c.is_active ? '' : ' <span class="tag">inativa</span>') + '</td><td class="mono">' + c.users + '</td><td class="mono">' + c.screens + '</td><td class="mono">' + c.media + '</td><td class="mono">' + c.playlists + '</td><td><button class="btn ghost small" data-logo="' + c.id + '" title="Enviar logo">' + ICONS.upload + '</button><button class="btn ghost small" data-emerg="' + c.id + '" title="Mensagem de emergencia">' + ICONS.shield + '</button><button class="btn ghost small" data-edit="' + c.id + '" title="Renomear">' + ICONS.settings + '</button><button class="btn danger small" data-delc="' + c.id + '" title="Excluir">' + ICONS.trash + '</button></td></tr>').join("");
        body.innerHTML = switcher +
          '<table class="set-table"><thead><tr><th>Empresa</th><th>Usuarios</th><th>Telas</th><th>Midias</th><th>Playlists</th><th></th></tr></thead><tbody>' + rows + '</tbody></table>' +
          '<label class="mm-label">Nova empresa</label>' +
          '<div class="row" style="gap:10px"><div class="field grow"><label>Nome</label><input id="nc-name"/></div><div class="field"><label>Cor (hex)</label><input id="nc-color" placeholder="#7aa2f7"/></div></div>' +
          '<div class="row" style="gap:10px"><div class="field grow"><label>Admin (opcional)</label><input id="nc-admin"/></div><div class="field grow"><label>Senha do admin</label><input type="password" id="nc-pass"/></div></div>' +
          '<button class="btn primary" id="nc-add">' + ICONS.plus + ' Criar empresa</button>';
        const sw = body.querySelector("#cp-switch");
        sw.addEventListener("change", async () => { state.activeCompanyId = sw.value ? Number(sw.value) : null; await loadAll(); render(); toast({ kind: "ok", msg: "Empresa em foco alterada." }); });
        body.querySelector("#nc-add").addEventListener("click", async () => {
          const name = body.querySelector("#nc-name").value.trim();
          if (name.length < 2) { toast({ kind: "warn", msg: "Informe o nome da empresa." }); return; }
          const payload = { name: name, primary_color: body.querySelector("#nc-color").value.trim() || null };
          const au = body.querySelector("#nc-admin").value.trim(), ap = body.querySelector("#nc-pass").value;
          if (au && ap) { payload.admin_username = au; payload.admin_password = ap; }
          try { await createCompany(payload); toast({ kind: "ok", msg: "Empresa criada." }); render(); } catch (err) { toast({ kind: "err", msg: err.message }); }
        });
        body.querySelectorAll("[data-delc]").forEach((b) => b.addEventListener("click", async () => { const id = Number(b.dataset.delc); if (!(await confirmDialog({ title: "Excluir empresa", message: "Remover a empresa e TODO o seu conteudo (telas, midias, playlists, usuarios)? Esta acao nao pode ser desfeita.", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await deleteCompany(id); if (state.activeCompanyId === id) { state.activeCompanyId = null; await loadAll(); } toast({ kind: "warn", msg: "Empresa removida." }); render(); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
        body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", async () => { const id = Number(b.dataset.edit); const c = companies.find((x) => x.id === id); const name = await promptDialog({ title: "Renomear empresa", message: "Novo nome da empresa:", icon: "settings", defaultValue: c ? c.name : "", confirmText: "Salvar" }); if (!name) return; try { await updateCompany(id, { name: name }); toast({ kind: "ok", msg: "Empresa atualizada." }); await refreshBranding(); render(); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
        body.querySelectorAll("[data-logo]").forEach((b) => b.addEventListener("click", () => { const id = Number(b.dataset.logo); const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*"; inp.addEventListener("change", async () => { if (!inp.files || !inp.files[0]) return; try { await uploadCompanyLogo(id, inp.files[0]); toast({ kind: "ok", msg: "Logo atualizado." }); await refreshBranding(); render(); } catch (err) { toast({ kind: "err", msg: err.message }); } }); inp.click(); }));
        body.querySelectorAll("[data-emerg]").forEach((b) => b.addEventListener("click", () => { const id = Number(b.dataset.emerg); const c = companies.find((x) => x.id === id); emergencyDialog(c); }));
      } catch (err) { body.innerHTML = '<p class="empty">' + esc(err.message) + '</p>'; }
    };
    render();
  }

  /** Define (ou remove, com null) a musica de fundo da tela atual. */
  async function setScreenMusic(mediaId) {
    const sc = screen(); if (!sc) return;
    try {
      await api("/api/screens/" + sc.id, { method: "PATCH", body: JSON.stringify({ background_audio_id: mediaId }) });
      sc.background_audio_id = mediaId;
      await loadScreens(); renderInspector();
      toast({ kind: "ok", msg: mediaId ? "Musica de fundo definida." : "Musica de fundo removida." });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }
  function uploadScreenMusic() {
    openMediaModal({ presetType: "audio", lockType: true, title: "Enviar musica de fundo", onCreated: async (media) => { await loadMedia(); await setScreenMusic(media.id); } });
  }
  function chooseScreenMusic() {
    const sc = screen(); if (!sc) { toast({ kind: "warn", msg: "Selecione uma tela primeiro." }); return; }
    const audios = state.media.filter((m) => m.type === "audio");
    if (!audios.length) { uploadScreenMusic(); return; }
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.innerHTML = '<div class="modal-head"><span class="modal-ico">' + ICONS.music + '</span><span class="modal-title">Musica de fundo da tela</span></div>' +
      '<div class="modal-body"><div class="field"><label>Escolher audio da biblioteca</label><select id="bm-sel">' + audios.map((a) => '<option value="' + a.id + '"' + (String(a.id) === String(sc.background_audio_id || "") ? " selected" : "") + '>' + esc(a.name) + '</option>').join("") + '</select></div><button class="btn ghost block small" id="bm-upload">' + ICONS.upload + ' Enviar nova musica</button></div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Cancelar</button><button class="btn primary" data-ok>' + ICONS.check + ' Definir</button></div>';
    const ui = buildOverlay(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("#bm-upload").addEventListener("click", () => { ui.close(); uploadScreenMusic(); });
    modal.querySelector("[data-ok]").addEventListener("click", async () => { const v = Number(modal.querySelector("#bm-sel").value); ui.close(); await setScreenMusic(v); });
  }
  function screenMusicField(sc) {
    const audios = state.media.filter((m) => m.type === "audio");
    const cur = sc.background_audio_id || "";
    const sel = '<select id="f-bgaudio"><option value="">- sem musica -</option>' + audios.map((a) => '<option value="' + a.id + '"' + (String(a.id) === String(cur) ? " selected" : "") + '>' + esc(a.name) + '</option>').join("") + '</select>';
    return field("Audio em loop", sel) + '<button class="btn ghost block small" data-upload-music>' + ICONS.upload + ' Enviar musica</button><span class="hint" style="display:block;margin-top:6px">Toca em loop na TV inteira enquanto o conteudo e exibido.</span>';
  }

  /** Pre-visualizacao ao vivo do player, embutida no painel (iframe 16:9). */
  function openLivePreview(sc) {
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    modal.innerHTML = '<div class="modal-head"><span class="modal-ico">' + ICONS.eye + '</span><span class="modal-title">Pre-visualizacao ao vivo - ' + esc(sc.name) + '</span></div>' +
      '<div class="modal-body"><div class="live-frame"><iframe src="' + playerUrl(sc.slug) + '" allow="autoplay; encrypted-media"></iframe></div><span class="hint">Espelha o player em tempo real. As mudancas aparecem automaticamente.</span></div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Fechar</button><button class="btn primary" data-open>' + ICONS.eye + ' Abrir em nova aba</button></div>';
    const ui = buildOverlay(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("[data-open]").addEventListener("click", () => window.open(playerUrl(sc.slug), "_blank"));
  }

  /** Mini-preview visual de um layout de zonas. */
  function layoutPreview(zones) {
    return '<div class="layout-mini">' + zones.map((z) => '<span style="left:' + z.x + '%;top:' + z.y + '%;width:' + z.width + '%;height:' + z.height + '%"></span>').join("") + '</div>';
  }

  /** Assistente de nova tela: nome, fuso e layout inicial (1, 2 ou 3 zonas). */
  async function duplicateScreen(sc) {
    const input = await promptDialog({ title: "Duplicar tela", message: "Nome da nova tela:", icon: "copy", placeholder: sc.name + " (copia)", confirmText: "Duplicar" });
    if (input === null || input === undefined) return;
    const name = (input || "").trim() || (sc.name + " (copia)");
    try {
      const created = await api("/api/screens", { method: "POST", body: JSON.stringify({ name: name, timezone: sc.timezone }) });
      await loadScreens();
      const fresh = state.screens.find((s) => s.id === created.id);
      const mainZone = fresh && fresh.zones[0] ? fresh.zones[0] : null;
      const src = sc.zones.slice().sort((a, b) => a.z_index - b.z_index);
      for (let i = 0; i < src.length; i++) {
        const z = src[i];
        const payload = { name: z.name, x: z.x, y: z.y, width: z.width, height: z.height, z_index: z.z_index, default_playlist_id: z.default_playlist_id };
        if (i === 0 && mainZone) { await api("/api/screens/" + created.id + "/zones/" + mainZone.id, { method: "PATCH", body: JSON.stringify(payload) }); }
        else { await api("/api/screens/" + created.id + "/zones", { method: "POST", body: JSON.stringify(payload) }); }
      }
      if (sc.background_audio_id) { await api("/api/screens/" + created.id, { method: "PATCH", body: JSON.stringify({ background_audio_id: sc.background_audio_id }) }); }
      await loadScreens(); state.activeSection = "screens"; state.activeScreenId = created.id;
      const s = screen(); state.selectedZoneId = s && s.zones[0] ? s.zones[0].id : null;
      renderActivity(); renderAll();
      toast({ kind: "ok", msg: "Tela duplicada com " + src.length + " zona(s)." });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  function openKioskMode(sc) {
    const url = playerUrl(sc.slug);
    const qr = "https://api.qrserver.com/v1/create-qr-code/?size=320x320&margin=10&data=" + encodeURIComponent(url);
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.innerHTML = '<div class="modal-head"><span class="modal-ico">' + ICONS.screen + '</span><span class="modal-title">Modo quiosque - ' + esc(sc.name) + '</span></div>' +
      '<div class="modal-body" style="text-align:center">' +
        '<p class="hint">Abra este endereco no navegador da TV (tela cheia) ou aponte a camera do celular para o QR code.</p>' +
        '<div class="qr-box"><img alt="QR code do player" src="' + qr + '"/></div>' +
        '<div class="field"><label>Link do player (TV)</label><div class="code">' + esc(url) + '</div></div>' +
        '<p class="hint">Dica: ative tela cheia (F11) e desative a suspensao de tela para exibicao continua.</p>' +
      '</div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Fechar</button><button class="btn ghost" data-copy>' + ICONS.copy + ' Copiar link</button><button class="btn primary" data-open>' + ICONS.eye + ' Abrir player</button></div>';
    const ui = buildOverlay(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("[data-copy]").addEventListener("click", () => copyText(url));
    modal.querySelector("[data-open]").addEventListener("click", () => window.open(url, "_blank"));
  }

  const SCREEN_SIZES = [
    { inches: "3", label: "3\" \u2014 mini display", res: ["480x320", "320x480"] },
    { inches: "7", label: "7\" \u2014 painel pequeno", res: ["1024x600", "1280x800"] },
    { inches: "14", label: "14\" \u2014 monitor", res: ["1920x1080", "1366x768"] },
    { inches: "32", label: "32\" \u2014 TV", res: ["1920x1080", "1366x768"] },
    { inches: "43", label: "43\" \u2014 TV Full HD/4K", res: ["1920x1080", "3840x2160"] },
    { inches: "50", label: "50\" \u2014 TV 4K", res: ["3840x2160", "1920x1080"] },
    { inches: "55", label: "55\" \u2014 TV 4K", res: ["3840x2160", "1920x1080"] },
    { inches: "65", label: "65\" \u2014 TV 4K", res: ["3840x2160", "1920x1080"] },
    { inches: "75", label: "75\" \u2014 TV 4K", res: ["3840x2160", "1920x1080"] },
    { inches: "86", label: "86\" \u2014 TV 4K", res: ["3840x2160", "1920x1080"] },
    { inches: "100", label: "100\" \u2014 TV 4K (mural)", res: ["3840x2160", "1920x1080"] },
  ];
  function sizeByInches(inches) { return SCREEN_SIZES.find((s) => s.inches === String(inches)) || SCREEN_SIZES[3]; }
  function screenAspect(sc) {
    const parts = String((sc && sc.resolution) || "1920x1080").toLowerCase().split("x");
    let w = Number(parts[0]) || 1920; let h = Number(parts[1]) || 1080;
    if (((sc && sc.orientation) || "landscape") === "portrait") { const t = w; w = h; h = t; }
    return { w: w, h: h };
  }
  function sizePickerMarkup(curInches, curRes, curOrient) {
    const inches = curInches || "32";
    const size = sizeByInches(inches);
    const sizeOpts = SCREEN_SIZES.map((s) => "<option value=\"" + s.inches + "\"" + (s.inches === inches ? " selected" : "") + ">" + s.label + "</option>").join("");
    const chosenRes = curRes || size.res[0];
    const resOpts = size.res.map((r) => "<option value=\"" + r + "\"" + (r === chosenRes ? " selected" : "") + ">" + r.replace("x", " x ") + " px</option>").join("");
    const orient = curOrient || "landscape";
    return "<div class=\"row\" style=\"gap:10px\">" +
      "<div class=\"field grow\"><label>Tamanho da tela</label><select id=\"sw-size\">" + sizeOpts + "</select></div>" +
      "<div class=\"field grow\"><label>Resolucao</label><select id=\"sw-res\">" + resOpts + "</select></div>" +
      "<div class=\"field\"><label>Orientacao</label><select id=\"sw-orient\"><option value=\"landscape\"" + (orient === "landscape" ? " selected" : "") + ">Horizontal</option><option value=\"portrait\"" + (orient === "portrait" ? " selected" : "") + ">Vertical</option></select></div>" +
      "</div>";
  }
  function bindSizePicker(root) {
    const sizeSel = root.querySelector("#sw-size");
    const resSel = root.querySelector("#sw-res");
    if (sizeSel && resSel) {
      sizeSel.addEventListener("change", () => {
        const size = sizeByInches(sizeSel.value);
        resSel.innerHTML = size.res.map((r) => "<option value=\"" + r + "\">" + r.replace("x", " x ") + " px</option>").join("");
      });
    }
    return () => ({
      size_inches: sizeSel ? sizeSel.value : null,
      resolution: resSel ? resSel.value : null,
      orientation: root.querySelector("#sw-orient") ? root.querySelector("#sw-orient").value : "landscape",
    });
  }
  function openScreenSizeModal(sc) {
    const modal = document.createElement("div");
    modal.className = "modal";
    const curInches = sc.size_inches || "32";
    modal.innerHTML = "<div class=\"modal-head\"><span class=\"modal-ico\">" + ICONS.screen + "</span><span class=\"modal-title\">Tamanho da tela</span></div>" +
      "<div class=\"modal-body\">" + sizePickerMarkup(curInches, sc.resolution, sc.orientation || "landscape") + "<p style=\"color:#94a3b8;font-size:12px;margin-top:8px\">A area de criacao passa a usar a proporcao da tela escolhida, para o conteudo preencher a tela sem sobras nos cantos.</p></div>" +
      "<div class=\"modal-actions\"><button class=\"btn ghost\" data-cancel>Cancelar</button><button class=\"btn primary\" data-save>" + ICONS.check + " Salvar</button></div>";
    const ui = buildOverlay(modal);
    const readSize = bindSizePicker(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("[data-save]").addEventListener("click", async () => {
      const sz = readSize();
      try {
        await api("/api/screens/" + sc.id, { method: "PATCH", body: JSON.stringify({ resolution: sz.resolution, orientation: sz.orientation, size_inches: sz.size_inches }) });
        ui.close(); await loadScreens(); renderAll(); toast({ kind: "ok", msg: "Tamanho da tela atualizado." });
      } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
  }

  function openScreenWizard() {
    let chosen = "full";
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    const cards = Object.keys(SCREEN_LAYOUTS).map((k) => '<button type="button" class="layout-card" data-layout="' + k + '">' + layoutPreview(SCREEN_LAYOUTS[k].zones) + '<span>' + SCREEN_LAYOUTS[k].label + '</span></button>').join("");
    modal.innerHTML = '<div class="modal-head"><span class="modal-ico">' + ICONS.screen + '</span><span class="modal-title">Nova tela</span></div>' +
      '<div class="modal-body"><div class="field"><label>Nome da tela</label><input id="sw-name" value="Nova TV"/></div>' +
      '<div class="row" style="gap:10px"><div class="field grow"><label>Fuso horario</label><input id="sw-tz" value="America/Sao_Paulo"/></div><div class="field grow"><label>Grupo de sincronia (opcional)</label><input id="sw-sync" placeholder="ex.: loja-1"/></div></div>' +
      sizePickerMarkup("32", null, "landscape") +
      '<div class="field"><label>Template (cenario pronto)</label><select id="sw-template"><option value="">Personalizado (escolher layout abaixo)</option></select></div>' +
      '<label class="mm-label" id="sw-layout-label">Layout inicial</label><div class="layout-grid" id="sw-layout-grid">' + cards + '</div></div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Cancelar</button><button class="btn primary" data-create>' + ICONS.check + ' Criar tela</button></div>';
    const ui = buildOverlay(modal);
    const readSize = bindSizePicker(modal);
    const setLayout = (k) => { chosen = k; modal.querySelectorAll(".layout-card").forEach((c) => c.classList.toggle("active", c.dataset.layout === k)); };
    modal.querySelectorAll(".layout-card").forEach((c) => c.addEventListener("click", () => setLayout(c.dataset.layout)));
    setLayout("full");
    const tplSel = modal.querySelector("#sw-template");
    loadTemplates().then((tpls) => { (tpls || []).filter((t) => t.key !== "blank").forEach((t) => { const o = document.createElement("option"); o.value = t.key; o.textContent = t.name + " - " + t.description; tplSel.appendChild(o); }); });
    const layoutGrid = modal.querySelector("#sw-layout-grid"); const layoutLabel = modal.querySelector("#sw-layout-label");
    tplSel.addEventListener("change", () => { const useTpl = !!tplSel.value; layoutGrid.style.opacity = useTpl ? "0.4" : "1"; layoutGrid.style.pointerEvents = useTpl ? "none" : "auto"; if (layoutLabel) layoutLabel.textContent = useTpl ? "Layout (definido pelo template)" : "Layout inicial"; });
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("[data-create]").addEventListener("click", async () => {
      const name = modal.querySelector("#sw-name").value.trim() || "Nova TV";
      const tz = modal.querySelector("#sw-tz").value.trim() || "America/Sao_Paulo";
      const template = tplSel.value || null;
      const syncGroup = (modal.querySelector("#sw-sync").value || "").trim() || null;
      const sz = readSize();
      try {
        const created = await api("/api/screens", { method: "POST", body: JSON.stringify({ name: name, timezone: tz, template: template, sync_group: syncGroup, resolution: sz.resolution, orientation: sz.orientation, size_inches: sz.size_inches }) });
        if (!template) {
          const layout = SCREEN_LAYOUTS[chosen].zones;
          await loadScreens();
          const fresh = state.screens.find((s) => s.id === created.id);
          const mainZone = fresh && fresh.zones[0] ? fresh.zones[0] : null;
          if (mainZone) {
            const first = layout[0];
            await api("/api/screens/" + created.id + "/zones/" + mainZone.id, { method: "PATCH", body: JSON.stringify({ name: first.name, x: first.x, y: first.y, width: first.width, height: first.height, z_index: 0 }) });
          }
          for (let i = 1; i < layout.length; i++) {
            const zl = layout[i];
            await api("/api/screens/" + created.id + "/zones", { method: "POST", body: JSON.stringify({ name: zl.name, x: zl.x, y: zl.y, width: zl.width, height: zl.height, z_index: i }) });
          }
        }
        ui.close();
        await loadScreens(); state.activeSection = "screens"; state.activeScreenId = created.id;
        const s = screen(); state.selectedZoneId = s && s.zones[0] ? s.zones[0].id : null;
        renderActivity(); renderAll();
        toast({ kind: "ok", msg: template ? "Tela criada a partir do template." : "Tela criada com " + SCREEN_LAYOUTS[chosen].zones.length + " zona(s)." });
      } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
  }

  // ---- v18: formularios e leitura de config dos widgets dinamicos ---- //
  function widgetFormHtml(t) {
    if (t === "clock") return '<div class="field"><label>3. Titulo (opcional)</label><input id="wf-title" placeholder="Ex.: Agora"/></div><div class="row" style="gap:10px"><div class="field grow"><label>Formato</label><select id="wf-format"><option value="24h">24 horas</option><option value="12h">12 horas (AM/PM)</option></select></div><div class="field grow"><label>Mostrar data</label><select id="wf-showdate"><option value="1">Sim</option><option value="0">Nao</option></select></div></div><span class="hint">Relogio atualizado em tempo real no fuso da TV.</span>';
    if (t === "weather") return '<div class="field"><label>3. Cidade</label><input id="wf-city" placeholder="Ex.: Sao Paulo"/></div><div class="field"><label>Titulo (opcional)</label><input id="wf-title" placeholder="Padrao: nome da cidade"/></div><div class="row" style="gap:10px"><div class="field grow"><label>Latitude (opcional)</label><input id="wf-lat" placeholder="Ex.: -23.55"/></div><div class="field grow"><label>Longitude (opcional)</label><input id="wf-lon" placeholder="Ex.: -46.63"/></div></div><span class="hint">Dados automaticos via open-meteo (sem chave). Atualiza a cada 10 min. Informe latitude/longitude para uma localizacao exata (sobrepoe a cidade).</span>';
    if (t === "news") return '<div class="field"><label>3. Feeds RSS (um por linha)</label><textarea id="wf-feeds" rows="3" placeholder="https://g1.globo.com/rss/g1/"></textarea></div><div class="field"><label>Mensagens manuais (uma por linha, opcional)</label><textarea id="wf-messages" rows="3" placeholder="Bem-vindo!"></textarea></div><div class="row" style="gap:10px"><div class="field grow"><label>Titulo</label><input id="wf-title" placeholder="Noticias"/></div><div class="field grow"><label>Velocidade (s)</label><input id="wf-speed" type="number" value="60"/></div></div><span class="hint">As manchetes dos feeds sao buscadas pelo servidor e combinadas com suas mensagens.</span>';
    if (t === "countdown") return '<div class="field"><label>3. Titulo (opcional)</label><input id="wf-title" placeholder="Ex.: Faltam"/></div><div class="field"><label>Data/hora alvo</label><input id="wf-target" type="datetime-local"/></div><div class="field"><label>Mensagem ao zerar</label><input id="wf-done" placeholder="Chegou o grande dia!"/></div><span class="hint">Contagem regressiva ate a data/hora (fuso da TV).</span>';
    if (t === "qrcode") return '<div class="field"><label>3. Conteudo do QR (URL ou texto)</label><input id="wf-data" placeholder="https://seusite.com"/></div><div class="row" style="gap:10px"><div class="field grow"><label>Titulo (opcional)</label><input id="wf-title" placeholder="Aponte a camera"/></div><div class="field grow"><label>Tamanho (px)</label><input id="wf-size" type="number" value="320"/></div></div><span class="hint">O QR e gerado automaticamente (requer internet na TV).</span>';
    if (t === "rates") return '<div class="field"><label>3. Pares de moedas (um por linha: USD-BRL)</label><textarea id="wf-pairs" rows="4" placeholder="USD-BRL&#10;EUR-BRL&#10;GBP-BRL"></textarea></div><div class="field"><label>Titulo (opcional)</label><input id="wf-title" placeholder="Cotacoes"/></div><span class="hint">Cotacoes via servidor (sem chave). Atualiza a cada 10 min.</span>';
    return '<div class="field"><label>3. Produtos (um por linha: Nome | preco | obs)</label><textarea id="wf-products" rows="5" placeholder="Pizza grande | R$ 49,90 | ate sexta"></textarea></div><div class="row" style="gap:10px"><div class="field grow"><label>Titulo</label><input id="wf-title" placeholder="Promocoes"/></div><div class="field grow"><label>Velocidade (s)</label><input id="wf-speed" type="number" value="50"/></div></div><span class="hint">Faixa deslizante (vermelha), ideal no rodape da zona.</span>';
  }
  function collectWidgetConfig(t, modal) {
    const val = (id) => { const e = modal.querySelector(id); return e ? e.value : ""; };
    const lines = (id) => (val(id) || "").split("\n").map((s) => s.trim()).filter(Boolean);
    const title = (val("#wf-title") || "").trim();
    if (t === "clock") return { title: title, format: val("#wf-format") || "24h", showDate: val("#wf-showdate") !== "0" };
    if (t === "weather") { const cfg = { title: title, city: (val("#wf-city") || "").trim() || "Sao Paulo" }; const la = parseFloat(val("#wf-lat")); const lo = parseFloat(val("#wf-lon")); if (!isNaN(la) && !isNaN(lo)) { cfg.lat = la; cfg.lon = lo; } return cfg; }
    if (t === "news") return { title: title || "Noticias", feeds: lines("#wf-feeds"), messages: lines("#wf-messages"), speed: Number(val("#wf-speed")) || 60 };
    if (t === "countdown") return { title: title, target: val("#wf-target") || "", doneText: (val("#wf-done") || "").trim() };
    if (t === "qrcode") return { title: title, data: (val("#wf-data") || "").trim(), size: Number(val("#wf-size")) || 320 };
    if (t === "rates") return { title: title || "Cotacoes", pairs: lines("#wf-pairs").map((s) => s.toUpperCase()) };
    const products = lines("#wf-products").map((line) => { const p = line.split("|").map((s) => s.trim()); return { name: p[0] || "", price: p[1] || "", note: p[2] || "" }; });
    return { title: title || "Promocoes", products: products, speed: Number(val("#wf-speed")) || 50 };
  }

  function openMediaModal(opts) {
    opts = opts || {};
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    modal.setAttribute("role", "dialog"); modal.setAttribute("aria-modal", "true");
    let current = opts.presetType || "image";
    const typeBtns = Object.keys(TYPE_LABEL).map((t) => '<button class="type-pick" data-type="' + t + '">' + ICONS[TYPE_ICON[t]] + '<span>' + TYPE_LABEL[t] + '</span></button>').join("");
    const folderOpts = '<option value="">Sem pasta</option>' + state.folders.map((f) => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join("");
    modal.innerHTML =
      '<div class="modal-head"><span class="modal-ico">' + ICONS.media + '</span><span class="modal-title">' + esc(opts.title || "Nova midia") + '</span></div>' +
      '<div class="modal-body">' +
        (opts.lockType ? '' : '<label class="mm-label">1. Tipo de conteudo</label><div class="type-grid">' + typeBtns + '</div>') +
        '<div class="field"><label>2. Nome</label><input id="mm-name" placeholder="Ex.: Promo de inverno"/></div>' +
        '<div id="mm-dynamic"></div>' +
        '<div class="row" style="gap:10px"><div class="field grow"><label>Pasta (opcional)</label><select id="mm-folder">' + folderOpts + '</select></div><div class="field grow"><label>Tags (separadas por virgula)</label><input id="mm-tags" placeholder="promo, inverno"/></div></div>' +
      '</div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Cancelar</button><button class="btn primary" data-create>' + ICONS.check + ' Adicionar</button></div>';
    const ui = buildOverlay(modal);
    const dyn = modal.querySelector("#mm-dynamic");
    const renderDynamic = () => {
      if (current === "image" || current === "video" || current === "audio") {
        const label = current === "image" ? "a imagem" : (current === "audio" ? "o audio" : "o video");
        const accept = current === "image" ? "image/*" : (current === "audio" ? "audio/*" : "video/*");
        dyn.innerHTML = '<label class="mm-label">3. Arquivo</label><div class="dropzone" id="mm-drop"><div class="dz-inner">' + ICONS.upload + '<p>Arraste ' + label + ' aqui ou <b>clique para escolher</b></p><span class="dz-file" id="mm-file-name">Nenhum arquivo selecionado</span></div><input type="file" id="mm-file" accept="' + accept + '" hidden/></div>';
        const dz = modal.querySelector("#mm-drop"); const fi = modal.querySelector("#mm-file"); const fn = modal.querySelector("#mm-file-name");
        const setName = () => { fn.textContent = fi.files[0] ? fi.files[0].name : "Nenhum arquivo selecionado"; };
        dz.addEventListener("click", () => fi.click());
        fi.addEventListener("change", setName);
        ["dragover", "dragenter"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
        ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
        dz.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) { fi.files = e.dataTransfer.files; setName(); } });
      } else if (current === "text" || current === "html") {
        const tplRow = '<label class="mm-label">Modelos prontos</label><div class="tpl-row">' + Object.keys(MEDIA_TEMPLATES).map((k) => '<button type="button" class="chip tpl-pick" data-tpl="' + k + '">' + MEDIA_TEMPLATES[k].label + '</button>').join("") + '</div>';
        dyn.innerHTML = tplRow + '<div class="field"><label>3. Conteudo ' + (current === "html" ? "(HTML)" : "(texto)") + '</label><textarea id="mm-value" rows="6" placeholder="' + (current === "html" ? "<h1>Ola</h1>" : "Digite o texto que aparecera na tela") + '"></textarea><span class="hint">' + (current === "html" ? "Aceita HTML simples. Evite scripts." : "Texto exibido em tela cheia. Use um modelo acima para comecar.") + '</span></div>';
        dyn.querySelectorAll(".tpl-pick").forEach((b) => b.addEventListener("click", () => {
          const tpl = MEDIA_TEMPLATES[b.dataset.tpl];
          const ta = modal.querySelector("#mm-value");
          if (ta) ta.value = (current === "html" ? tpl.html : tpl.text);
          const nm = modal.querySelector("#mm-name");
          if (nm && !nm.value.trim()) nm.value = tpl.label;
        }));
      } else if (WIDGET_TYPES.indexOf(current) !== -1) {
        dyn.innerHTML = widgetFormHtml(current);
      } else {
        const ph = current === "youtube" ? "https://youtube.com/watch?v=..." : (current === "embed" ? "https://... (pagina ou musica para incorporar)" : (current === "live" ? "https://.../stream.m3u8" : "https://exemplo.com"));
        const help = current === "youtube" ? "Cole o link do video do YouTube." : (current === "embed" ? "Pagina ou conteudo incorporavel." : (current === "live" ? "URL de stream HLS (.m3u8). RTSP precisa de gateway para HLS." : "Pagina web que sera exibida."));
        dyn.innerHTML = '<div class="field"><label>3. URL de origem</label><input id="mm-value" placeholder="' + ph + '"/><span class="hint">' + help + '</span></div>';
      }
    };
    const setType = (t) => { current = t; modal.querySelectorAll(".type-pick").forEach((b) => b.classList.toggle("active", b.dataset.type === t)); renderDynamic(); };
    modal.querySelectorAll(".type-pick").forEach((b) => b.addEventListener("click", () => setType(b.dataset.type)));
    setType(current);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("[data-create]").addEventListener("click", async () => {
      const name = modal.querySelector("#mm-name").value.trim();
      if (!name) { toast({ kind: "warn", msg: "Informe um nome." }); return; }
      const folderId = modal.querySelector("#mm-folder").value;
      const tags = modal.querySelector("#mm-tags").value;
      try {
        let created;
        if (current === "image" || current === "video" || current === "audio") {
          const file = modal.querySelector("#mm-file").files[0];
          if (!file) { toast({ kind: "warn", msg: "Selecione um arquivo." }); return; }
          const fd = new FormData(); fd.append("name", name); fd.append("file", file);
          const dims = await readMediaDims(file, current); if (dims) { fd.append("width", dims.width); fd.append("height", dims.height); }
          if (folderId) fd.append("folder_id", folderId);
          if (tags.trim()) fd.append("tags", tags);
          created = await api("/api/media/upload", { method: "POST", body: fd });
        } else if (WIDGET_TYPES.indexOf(current) !== -1) {
          const body = { name, type: current, content: JSON.stringify(collectWidgetConfig(current, modal)), tags: tags.split(",").map((s) => s.trim()).filter(Boolean) };
          if (folderId) body.folder_id = Number(folderId);
          created = await api("/api/media", { method: "POST", body: JSON.stringify(body) });
        } else {
          const value = modal.querySelector("#mm-value").value;
          const body = { name, type: current, tags: tags.split(",").map((s) => s.trim()).filter(Boolean) };
          if (folderId) body.folder_id = Number(folderId);
          if (current === "url" || current === "youtube" || current === "embed" || current === "live") body.source_url = value; else body.content = value;
          created = await api("/api/media", { method: "POST", body: JSON.stringify(body) });
        }
        ui.close(); await loadMedia(); renderSidebar(); renderDoc();
        if (opts.onCreated) { await opts.onCreated(created); } else { toast({ kind: "ok", msg: "Midia adicionada." }); }
      } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
    setTimeout(() => { const n = modal.querySelector("#mm-name"); if (n) n.focus(); }, 40);
  }

  // Modal de importacao em massa de URLs/textos (uma entrada por linha).
  function openBulkModal() {
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    const typeOpts = ["url", "youtube", "embed", "text", "html"].map((t) => '<option value="' + t + '">' + TYPE_LABEL[t] + '</option>').join("");
    const folderOpts = '<option value="">Sem pasta</option>' + state.folders.map((f) => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join("");
    modal.innerHTML =
      '<div class="modal-head"><span class="modal-ico">' + ICONS.link + '</span><span class="modal-title">Importar em massa</span></div>' +
      '<div class="modal-body">' +
        '<p class="hint">Uma entrada por linha. Use <b>Nome | valor</b> para nomear, ou apenas o valor. Imagens e videos nao entram aqui (use Nova midia).</p>' +
        '<div class="row" style="gap:10px"><div class="field grow"><label>Tipo</label><select id="bk-type">' + typeOpts + '</select></div><div class="field grow"><label>Pasta (opcional)</label><select id="bk-folder">' + folderOpts + '</select></div></div>' +
        '<div class="field"><label>Itens</label><textarea id="bk-items" rows="8" placeholder="Promo 1 | https://youtube.com/watch?v=abc&#10;https://exemplo.com/pagina"></textarea></div>' +
      '</div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Cancelar</button><button class="btn primary" data-create>' + ICONS.upload + ' Importar</button></div>';
    const ui = buildOverlay(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    modal.querySelector("[data-create]").addEventListener("click", async () => {
      const type = modal.querySelector("#bk-type").value;
      const folderId = modal.querySelector("#bk-folder").value;
      const lines = modal.querySelector("#bk-items").value.split("\n").map((l) => l.trim()).filter(Boolean);
      if (!lines.length) { toast({ kind: "warn", msg: "Adicione ao menos uma linha." }); return; }
      const isContent = (type === "text" || type === "html");
      const items = lines.map((line) => {
        let name = line, value = line;
        const sep = line.indexOf("|");
        if (sep !== -1) { name = line.slice(0, sep).trim(); value = line.slice(sep + 1).trim(); }
        const it = { name: name || value, type };
        if (folderId) it.folder_id = Number(folderId);
        if (isContent) it.content = value; else it.source_url = value;
        return it;
      });
      try { const created = await bulkImportMedia(items); ui.close(); await loadMedia(); renderSidebar(); renderDoc(); toast({ kind: "ok", msg: (created ? created.length : items.length) + " midia(s) importada(s)." }); } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
  }

  async function createFolder() {
    const name = await promptDialog({ title: "Nova pasta", message: "Nome da pasta de midias:", icon: "folder", placeholder: "Ex.: Campanhas", confirmText: "Criar" });
    if (!name) return;
    try { await api("/api/folders", { method: "POST", body: JSON.stringify({ name }) }); state.folders = await loadFolders(); renderSidebar(); renderDoc(); toast({ kind: "ok", msg: "Pasta criada." }); } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  function renderMediaInspector() {
    const m = mediaById(state.selectedMediaId);
    if (!m) return '<div class="insp-head">' + ICONS.media + '<span>Midias</span></div><div class="insp-section"><p class="empty" style="padding:0">Selecione uma midia para editar nome, conteudo, pasta e tags.</p></div>';
    let valField = "";
    if (m.type === "text" || m.type === "html") valField = field("Conteudo", '<textarea id="mi-content" rows="4">' + esc(m.content || "") + '</textarea>');
    else if (m.type === "url" || m.type === "youtube" || m.type === "embed") valField = field("URL de origem", '<input id="mi-url" value="' + esc(m.source_url || "") + '"/>');
    else { const isAV = (m.type === "image" || m.type === "video"); valField = field("Arquivo atual", '<div class="code">' + esc(m.path || "-") + '</div>') + (isAV ? '<div class="field"><label>Substituir arquivo</label><input type="file" id="mi-file" accept="' + (m.type === "image" ? "image/*" : "video/*") + '"/></div>' : ''); }
    const folderOpts = '<option value="">Sem pasta</option>' + state.folders.map((f) => '<option value="' + f.id + '"' + (m.folder_id === f.id ? " selected" : "") + '>' + esc(f.name) + '</option>').join("");
    return '<div class="insp-head">' + ICONS[TYPE_ICON[m.type]] + '<span>' + esc(m.name) + '</span></div><div class="insp-section"><h5>' + TYPE_LABEL[m.type] + '</h5>' +
      field("Nome", '<input id="mi-name" value="' + esc(m.name) + '"/>') + valField +
      field("Pasta", '<select id="mi-folder">' + folderOpts + '</select>') +
      field("Tags (separadas por virgula)", '<input id="mi-tags" value="' + esc((m.tags || []).join(", ")) + '"/>') +
      '<button class="btn primary block small" data-save-media>' + ICONS.check + ' Salvar</button></div>';
  }
  function bindMediaInspector() {
    const insp = $("inspector"); const m = mediaById(state.selectedMediaId); if (!m) return;
    const save = insp.querySelector("[data-save-media]"); if (!save) return;
    save.addEventListener("click", async () => {
      try {
        const fileI = $("mi-file");
        if (fileI && fileI.files[0]) { const fd = new FormData(); fd.append("file", fileI.files[0]); await api("/api/media/" + m.id + "/file", { method: "POST", body: fd }); }
        const patch = { name: $("mi-name").value };
        if ($("mi-content")) patch.content = $("mi-content").value;
        if ($("mi-url")) patch.source_url = $("mi-url").value;
        if ($("mi-folder")) patch.folder_id = $("mi-folder").value ? Number($("mi-folder").value) : null;
        if ($("mi-tags")) patch.tags = $("mi-tags").value.split(",").map((s) => s.trim()).filter(Boolean);
        await api("/api/media/" + m.id, { method: "PATCH", body: JSON.stringify(patch) });
        await loadMedia(); renderSidebar(); renderDoc(); renderInspector(); toast({ kind: "ok", msg: "Midia atualizada." });
      } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
  }

  // ---------------------------- Configuracoes ---------------------- //
  async function openSettings() {
    const modal = document.createElement("div");
    modal.className = "modal modal-wide";
    modal.innerHTML =
      '<div class="modal-head"><span class="modal-ico">' + ICONS.settings + '</span><span class="modal-title">Configuracoes</span></div>' +
      '<div class="set-tabs"><button class="set-tab active" data-stab="account">' + ICONS.lock + ' Conta</button><button class="set-tab" data-stab="users">' + ICONS.user + ' Usuarios</button><button class="set-tab" data-stab="audit">' + ICONS.terminal + ' Auditoria</button></div>' +
      '<div class="modal-body" id="set-body"></div>' +
      '<div class="modal-actions"><button class="btn ghost" data-cancel>Fechar</button></div>';
    const ui = buildOverlay(modal);
    modal.querySelector("[data-cancel]").addEventListener("click", ui.close);
    const body = modal.querySelector("#set-body");
    const tabs = modal.querySelectorAll(".set-tab");
    const show = async (tab) => {
      tabs.forEach((t) => t.classList.toggle("active", t.dataset.stab === tab));
      if (tab === "account") {
        body.innerHTML = '<div class="field"><label>Senha atual</label><input type="password" id="sp-cur"/></div><div class="field"><label>Nova senha (min. 6)</label><input type="password" id="sp-new"/></div><div class="field"><label>Confirmar nova senha</label><input type="password" id="sp-conf"/></div><button class="btn primary" id="sp-save">' + ICONS.check + ' Alterar senha</button>';
        body.querySelector("#sp-save").addEventListener("click", async () => {
          const cur = body.querySelector("#sp-cur").value, nw = body.querySelector("#sp-new").value, cf = body.querySelector("#sp-conf").value;
          if (nw.length < 6) { toast({ kind: "warn", msg: "A nova senha deve ter ao menos 6 caracteres." }); return; }
          if (nw !== cf) { toast({ kind: "warn", msg: "As senhas nao conferem." }); return; }
          try { await changePassword(cur, nw); toast({ kind: "ok", msg: "Senha alterada." }); ui.close(); } catch (err) { toast({ kind: "err", msg: err.message }); }
        });
      } else if (tab === "users") {
        body.innerHTML = '<p class="hint">Carregando...</p>';
        try {
          const users = await loadUsers();
          const rows = users.map((u) => '<tr><td>' + esc(u.username) + '</td><td><span class="tag">' + esc(u.role) + '</span></td><td>' + (u.is_active ? "ativo" : "inativo") + '</td></tr>').join("");
          body.innerHTML = '<table class="set-table"><thead><tr><th>Usuario</th><th>Papel</th><th>Status</th></tr></thead><tbody>' + rows + '</tbody></table>' +
            '<label class="mm-label">Novo usuario</label>' +
            '<div class="row" style="gap:10px"><div class="field grow"><label>Usuario</label><input id="nu-name"/></div><div class="field grow"><label>Senha</label><input type="password" id="nu-pass"/></div><div class="field"><label>Papel</label><select id="nu-role"><option value="viewer">viewer</option><option value="editor" selected>editor</option><option value="admin">admin</option></select></div></div>' +
            '<button class="btn primary" id="nu-add">' + ICONS.plus + ' Criar usuario</button>';
          body.querySelector("#nu-add").addEventListener("click", async () => {
            const username = body.querySelector("#nu-name").value.trim(), password = body.querySelector("#nu-pass").value, role = body.querySelector("#nu-role").value;
            if (username.length < 3 || password.length < 6) { toast({ kind: "warn", msg: "Usuario (min. 3) e senha (min. 6) obrigatorios." }); return; }
            try { await createUser({ username, password, role }); toast({ kind: "ok", msg: "Usuario criado." }); show("users"); } catch (err) { toast({ kind: "err", msg: err.message }); }
          });
        } catch (err) { body.innerHTML = '<p class="empty">' + (/403|permiss|admin/i.test(err.message) ? "Apenas administradores podem gerenciar usuarios." : esc(err.message)) + '</p>'; }
      } else {
        body.innerHTML = '<p class="hint">Carregando...</p>';
        try {
          const data = await loadAudit(80);
          const items = Array.isArray(data) ? data : (data.items || []);
          if (!items.length) { body.innerHTML = '<p class="empty">Sem registros de auditoria.</p>'; return; }
          body.innerHTML = '<table class="set-table"><thead><tr><th>Quando</th><th>Usuario</th><th>Acao</th></tr></thead><tbody>' + items.map((a) => '<tr><td class="mono">' + esc(String(a.created_at || a.timestamp || "").slice(0, 19).replace("T", " ")) + '</td><td>' + esc(a.username || a.actor || "-") + '</td><td>' + esc(a.action || a.event || "-") + '</td></tr>').join("") + '</tbody></table>';
        } catch (err) { body.innerHTML = '<p class="empty">' + (/403|permiss|admin/i.test(err.message) ? "Apenas administradores podem ver a auditoria." : esc(err.message)) + '</p>'; }
      }
    };
    tabs.forEach((t) => t.addEventListener("click", () => show(t.dataset.stab)));
    show("account");
  }

  // ---------------------------- Playlists -------------------------- //
  function renderPlaylistDoc() {
    const pl = playlistById(state.openPlaylistId);
    if (!pl) return '<div class="empty">Nenhuma playlist selecionada. Use o botao + na barra lateral.</div>';
    const head = '<div class="item-row row between" style="margin-bottom:12px"><strong style="font-size:14px">' + esc(pl.name) + '</strong><span class="row"><button class="btn ghost small" data-rename-pl>Renomear</button><button class="btn danger small" data-del-pl>' + ICONS.trash + ' Excluir</button></span></div>';
    const items = pl.items.length ? pl.items.map((it, i) => itemRow(pl, it, i)).join("") : '<div class="empty">Sem itens. Adicione abaixo.</div>';
    const mediaOpts = state.media.map((m) => '<option value="' + m.id + '">' + esc(m.name) + ' (' + TYPE_LABEL[m.type] + ')</option>').join("");
    const add = '<div class="item-row row wrap" style="margin-top:12px;gap:10px"><select id="pi-media" style="flex:1;min-width:160px">' + mediaOpts + '</select><input id="pi-dur" type="number" min="1" value="10" class="mini" title="Duracao (s)"/><select id="pi-fit">' + FITS.map((f) => '<option value="' + f + '">' + FIT_LABELS[f] + '</option>').join("") + '</select><select id="pi-focal" title="Ponto focal">' + FOCALS.map((f) => '<option value="' + f + '">' + FOCAL_LABELS[f] + '</option>').join("") + '</select><select id="pi-trans">' + TRANSITIONS.map((t) => '<option>' + t + '</option>').join("") + '</select><label class="row" style="gap:5px"><input id="pi-sound" type="checkbox"/> som</label><label class="row" style="gap:5px" title="Tocar a midia inteira"><input id="pi-full" type="checkbox"/> completo</label><button class="btn primary small" id="pi-add">' + ICONS.plus + ' Item</button></div>';
    return '<div class="pl-editor">' + head + '<div class="pl-items">' + items + '</div>' + add + '</div>';
  }
  function itemRow(pl, it, i) {
    const md = it.media;
    return '<div class="item-row" data-item="' + it.id + '"><span class="tag">' + (i + 1) + '</span>' + ICONS[TYPE_ICON[md.type]] + '<span class="grow">' + esc(md.name) + '</span>' +
      '<input type="number" min="1" value="' + it.duration + '" class="mini" data-it-dur="' + it.id + '" title="Duracao (s)"/>' +
      '<select data-it-fit="' + it.id + '">' + FITS.map((f) => '<option value="' + f + '" ' + (f === it.fit ? "selected" : "") + '>' + FIT_LABELS[f] + '</option>').join("") + '</select>' +
      '<select data-it-focal="' + it.id + '" title="Ponto focal (corte)">' + FOCALS.map((f) => '<option value="' + f + '" ' + (f === (it.focal || "center") ? "selected" : "") + '>' + FOCAL_LABELS[f] + '</option>').join("") + '</select>' +
      '<select data-it-trans="' + it.id + '">' + TRANSITIONS.map((t) => '<option ' + (t === it.transition ? "selected" : "") + '>' + t + '</option>').join("") + '</select>' +
      '<label class="row" style="gap:4px" title="Som"><input type="checkbox" data-it-sound="' + it.id + '" ' + (it.muted ? "" : "checked") + '/></label>' +
      '<label class="row" style="gap:4px" title="Tocar a midia inteira (video/audio/YouTube)"><input type="checkbox" data-it-full="' + it.id + '" ' + (it.play_full ? "checked" : "") + '/>\u25B6</label>' +
      '<button class="btn ghost small" data-it-up="' + it.id + '">' + ICONS.up + '</button><button class="btn ghost small" data-it-down="' + it.id + '">' + ICONS.down + '</button>' +
      '<button class="btn danger small" data-it-del="' + it.id + '">' + ICONS.trash + '</button></div>';
  }
  function bindPlaylistDoc() {
    const doc = $("doc"); const pl = playlistById(state.openPlaylistId); if (!pl) return;
    const rn = doc.querySelector("[data-rename-pl]"); if (rn) rn.addEventListener("click", async () => { const name = await promptDialog({ title: "Renomear playlist", message: "Digite o novo nome da playlist:", icon: "playlist", defaultValue: pl.name, placeholder: "Nome da playlist", confirmText: "Salvar" }); if (!name) return; try { await api("/api/playlists/" + pl.id, { method: "PATCH", body: JSON.stringify({ name }) }); await loadPlaylists(); renderSidebar(); renderDoc(); toast({ kind: "ok", msg: "Playlist renomeada." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
    const dp = doc.querySelector("[data-del-pl]"); if (dp) dp.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir playlist", message: "Tem certeza que deseja excluir esta playlist?", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/playlists/" + pl.id, { method: "DELETE" }); state.openPlaylistId = null; await loadPlaylists(); fixSelection(); renderSidebar(); renderDoc(); renderBottom(); toast({ kind: "warn", msg: "Playlist excluida." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
    const add = $("pi-add"); if (add) add.addEventListener("click", async () => { const media_id = Number($("pi-media").value); if (!media_id) { toast({ kind: "warn", msg: "Selecione uma midia." }); return; } const body = { media_id, duration: Number($("pi-dur").value) || 10, fit: $("pi-fit").value, focal: $("pi-focal").value, transition: $("pi-trans").value, muted: !$("pi-sound").checked, play_full: $("pi-full") ? $("pi-full").checked : false }; try { await api("/api/playlists/" + pl.id + "/items", { method: "POST", body: JSON.stringify(body) }); await loadPlaylists(); renderSidebar(); renderDoc(); renderBottom(); toast({ kind: "ok", msg: "Item adicionado." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
    doc.querySelectorAll("[data-it-dur]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itDur, { duration: Number(el.value) })));
    doc.querySelectorAll("[data-it-fit]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itFit, { fit: el.value })));
    doc.querySelectorAll("[data-it-focal]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itFocal, { focal: el.value })));
    doc.querySelectorAll("[data-it-trans]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itTrans, { transition: el.value })));
    doc.querySelectorAll("[data-it-sound]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itSound, { muted: !el.checked })));
    doc.querySelectorAll("[data-it-full]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itFull, { play_full: el.checked })));
    doc.querySelectorAll("[data-it-del]").forEach((el) => el.addEventListener("click", async () => { try { await api("/api/playlists/" + pl.id + "/items/" + el.dataset.itDel, { method: "DELETE" }); await loadPlaylists(); renderSidebar(); renderDoc(); renderBottom(); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
    doc.querySelectorAll("[data-it-up]").forEach((el) => el.addEventListener("click", () => moveItem(pl, Number(el.dataset.itUp), -1)));
    doc.querySelectorAll("[data-it-down]").forEach((el) => el.addEventListener("click", () => moveItem(pl, Number(el.dataset.itDown), 1)));
  }
  async function updateItem(plId, itemId, patch) { try { await api("/api/playlists/" + plId + "/items/" + itemId, { method: "PATCH", body: JSON.stringify(patch) }); await loadPlaylists(); renderBottom(); } catch (err) { toast({ kind: "err", msg: err.message }); } }
  async function moveItem(pl, itemId, dir) {
    const ids = pl.items.map((it) => it.id);
    const idx = ids.indexOf(itemId); const ni = idx + dir;
    if (ni < 0 || ni >= ids.length) return;
    ids.splice(ni, 0, ids.splice(idx, 1)[0]);
    try { await api("/api/playlists/" + pl.id + "/reorder", { method: "POST", body: JSON.stringify({ item_ids: ids }) }); await loadPlaylists(); renderSidebar(); renderDoc(); renderBottom(); } catch (err) { toast({ kind: "err", msg: err.message }); }
  }

  // --------------------------- Agendamentos ------------------------ //
  function renderSchedulesDoc() {
    const rows = [];
    state.screens.forEach((s) => s.zones.forEach((z) => z.schedules.forEach((sc) => {
      const pl = playlistById(sc.playlist_id);
      const days = (sc.days_of_week || "").split(",").filter((x) => x !== "").map((d) => DAYS_FULL[Number(d)].slice(0, 3)).join(", ");
      rows.push('<tr><td>' + esc(s.name) + '</td><td>' + esc(z.name) + '</td><td>' + esc(pl ? pl.name : "?") + '</td><td class="mono">' + minToHHMM(sc.start_minute) + " - " + minToHHMM(sc.end_minute) + '</td><td>' + days + '</td><td class="mono">' + sc.priority + '</td></tr>');
    })));
    if (!rows.length) return '<div class="empty">Nenhum agendamento. Selecione uma zona na secao Telas e use o inspetor para criar regras por horario e dia.</div>';
    return '<table class="sched-table"><thead><tr><th>Tela</th><th>Zona</th><th>Playlist</th><th>Horario</th><th>Dias</th><th>Prio</th></tr></thead><tbody>' + rows.join("") + '</tbody></table>';
  }
  function bindSchedulesDoc() { /* somente leitura */ }

  // -------------------------- Painel inferior ---------------------- //
  const BOTTOM = [
    { id: "timeline", label: "Linha do tempo", icon: "timeline" },
    { id: "logs", label: "Saida", icon: "terminal" },
    { id: "problems", label: "Problemas", icon: "alert" },
  ];
  function computeProblems() {
    const probs = [];
    state.screens.forEach((s) => s.zones.forEach((z) => {
      const pl = playlistById(z.default_playlist_id);
      if (!z.schedules.length && (!pl || pl.items.length === 0)) probs.push({ kind: "warn", desc: 'Zona "' + z.name + '" sem playlist com itens.', where: s.slug });
      if (z.x + z.width > 100 || z.y + z.height > 100) probs.push({ kind: "err", desc: 'Zona "' + z.name + '" ultrapassa os limites da tela.', where: s.slug });
    }));
    return probs;
  }
  function renderBottom() {
    const probs = computeProblems();
    $("bottom-tabs").innerHTML = BOTTOM.map((b) => '<button class="bt ' + (b.id === state.bottomTab ? "active" : "") + '" data-bt="' + b.id + '">' + ICONS[b.icon] + '<span>' + b.label + '</span>' + (b.id === "problems" && probs.length ? '<span class="badge">' + probs.length + '</span>' : "") + '</button>').join("");
    $("bottom-tabs").querySelectorAll("[data-bt]").forEach((b) => b.addEventListener("click", () => { state.bottomTab = b.dataset.bt; renderBottom(); }));
    const c = $("bottom-content");
    if (state.bottomTab === "timeline") { c.innerHTML = renderTimeline(); bindTimeline(); }
    else if (state.bottomTab === "logs") c.innerHTML = renderLogs();
    else c.innerHTML = renderProblems(probs);
  }
  function timelinePlaylist() {
    if (state.activeSection === "playlists" && state.openPlaylistId) return playlistById(state.openPlaylistId);
    const z = zone(); if (z && z.default_playlist_id) return playlistById(z.default_playlist_id);
    return null;
  }
  function renderTimeline() {
    const pl = timelinePlaylist();
    if (!pl || !pl.items.length) return '<div class="empty">Selecione uma zona com playlist (ou uma playlist) para ver a linha do tempo.</div>';
    const total = pl.items.reduce((a, b) => a + b.duration, 0);
    const alts = ["", "alt", "alt2"];
    return '<div class="timeline"><div class="track-head"><span>' + esc(pl.name) + '</span><span class="mono">ciclo total: ' + total + 's</span></div><div class="track">' + pl.items.map((it, i) => '<div class="seg ' + alts[i % 3] + '" data-tl="' + it.id + '" data-tl-pl="' + pl.id + '" title="Clique direito para editar" style="flex:' + it.duration + '"><strong>' + esc(it.media.name) + '</strong><small>' + it.duration + 's - ' + it.transition + (it.muted ? " - mudo" : " - som") + (it.play_full ? " - completo" : "") + '</small></div>').join("") + '</div></div>';
  }
  function renderLogs() {
    const now = new Date();
    const t = (s) => new Date(now.getTime() - s * 1000).toLocaleTimeString("pt-BR");
    const sc = screen();
    const lines = [
      { lvl: "ok", t: t(3), m: "Sessao autenticada no painel" },
      { lvl: "info", t: t(20), m: "Dados sincronizados: " + state.screens.length + " telas, " + state.playlists.length + " playlists, " + state.media.length + " midias" },
      { lvl: "info", t: t(64), m: "Alteracoes aplicadas ao vivo via /api/display/" + (sc ? sc.slug : "-") },
      { lvl: "warn", t: t(150), m: "Autoplay com som depende do navegador do player (use modo quiosque)" },
    ];
    return lines.map((l) => '<div class="logline"><span class="t">' + l.t + '</span><span class="lvl ' + l.lvl + '">' + l.lvl.toUpperCase() + '</span><span>' + esc(l.m) + '</span></div>').join("");
  }
  function renderProblems(probs) {
    if (!probs.length) return '<div class="empty">Nenhum problema detectado. Layout consistente.</div>';
    return probs.map((p) => '<div class="problem ' + p.kind + '">' + ICONS.alert + '<div><div class="desc">' + esc(p.desc) + '</div><div class="where">' + esc(p.where) + '</div></div></div>').join("");
  }

  // ---------------------------- Status bar ------------------------- //
  function renderStatus() {
    const sc = screen();
    const online = state.screens.filter(isOnline).length;
    const probs = computeProblems().length;
    const sbEl = $("statusbar");
    sbEl.innerHTML = '<span class="si"><span class="pulse"></span> Ao vivo</span>' +
      '<span class="si">' + ICONS.screen + ' ' + (sc ? esc(sc.slug) : "-") + '</span>' +
      '<span class="spacer"></span>' +
      '<span class="si">' + ICONS.wifi + ' ' + online + '/' + state.screens.length + ' online</span>' +
      '<span class="si">' + ICONS.alert + ' ' + probs + ' problema(s)</span>' +
      '<span class="si btn-like" data-preview>' + ICONS.eye + ' Pre-visualizar</span>' +
      '<span class="si btn-like" data-reload>' + ICONS.refresh + ' Recarregar</span>';
    const pv = sbEl.querySelector("[data-preview]"); if (pv) pv.addEventListener("click", () => { if (sc) window.open(playerUrl(sc.slug), "_blank"); else toast({ kind: "warn", msg: "Crie uma tela primeiro." }); });
    sbEl.querySelector("[data-reload]").addEventListener("click", () => loadAll());
  }

  function copyText(text) { if (navigator.clipboard) navigator.clipboard.writeText(text).then(() => toast({ kind: "ok", msg: "Copiado." })).catch(() => toast({ kind: "warn", msg: text })); else toast({ kind: "info", msg: text }); }

  // ------------------------- Paleta de comandos -------------------- //
  const COMMANDS = [
    { icon: "screen", label: "Ir para: Telas", run: () => goSection("screens") },
    { icon: "media", label: "Ir para: Midias", run: () => goSection("media") },
    { icon: "playlist", label: "Ir para: Playlists", run: () => goSection("playlists") },
    { icon: "clock", label: "Ir para: Agendamentos", run: () => goSection("schedules") },
    { icon: "plus", label: "Nova tela", run: () => handleSideAct("add-screen") },
    { icon: "plus", label: "Nova playlist", run: () => handleSideAct("add-playlist") },
    { icon: "eye", label: "Pre-visualizar player da tela atual", run: () => { const s = screen(); if (s) window.open(playerUrl(s.slug), "_blank"); } },
    { icon: "refresh", label: "Recarregar dados", run: () => loadAll() },
    { icon: "sun", label: "Alternar tema claro/escuro", run: () => toggleTheme() },
    { icon: "wifi", label: "Saude das telas (online/offline)", run: () => reportHealth() },
    { icon: "timeline", label: "Relatorio de exibicao (proof-of-play 7d)", run: () => reportProofOfPlay() },
    { icon: "info", label: "Abrir guia de uso (tutorial)", run: () => openOnboard() },
    { icon: "power", label: "Sair (logout)", run: () => logout() },
  ];
  let palIndex = 0, palFiltered = COMMANDS;
  function goSection(sec) { state.activeSection = sec; renderActivity(); renderSidebar(); renderTabs(); renderDoc(); renderInspector(); renderBottom(); }
  function openPalette() { $("palette").hidden = false; const inp = $("palette-input"); inp.value = ""; palFiltered = COMMANDS; palIndex = 0; renderPalette(); inp.focus(); }
  function closePalette() { $("palette").hidden = true; }
  function renderPalette() {
    $("palette-list").innerHTML = palFiltered.map((c, i) => '<li class="' + (i === palIndex ? "active" : "") + '" data-cmd="' + i + '"><span class="pi">' + ICONS[c.icon] + '</span><span>' + esc(c.label) + '</span></li>').join("") || '<li><span class="pi">' + ICONS.search + '</span><span>Nenhum comando</span></li>';
    $("palette-list").querySelectorAll("[data-cmd]").forEach((li) => li.addEventListener("click", () => runPalette(Number(li.dataset.cmd))));
  }
  function runPalette(i) { const c = palFiltered[i]; closePalette(); if (c) c.run(); }

  // --------------------------- Onboarding -------------------------- //
  // Guia de uso exibido automaticamente nas primeiras vezes que o painel e
  // acessado. O estado fica em localStorage para nao reabrir a cada visita;
  // pode ser reaberto a qualquer momento pela paleta de comandos.
  const ONBOARD_KEY = "tvmedia_onboarded";
  const TOUR = [
    { icon: "logo", title: "Bem-vindo ao tvMedia Studio", text: "Este painel controla o que aparece nas suas TVs. Em poucos passos voce cria uma tela, envia midias, monta uma sequencia e publica. Use Anterior e Proximo para navegar neste guia." },
    { icon: "screen", title: "1. Telas", text: "Cada tela representa uma TV. Na secao Telas voce cria a tela e desenha Zonas: areas onde o conteudo aparece. Arraste e redimensione as zonas direto no canvas, como caixas na tela." },
    { icon: "media", title: "2. Midias", text: "Na secao Midias voce envia imagens e videos do seu computador, ou cadastra links (YouTube, paginas web, musica). Tudo o que sera exibido fica guardado aqui para reaproveitar." },
    { icon: "playlist", title: "3. Playlists", text: "Uma playlist e a sequencia de midias que toca em loop. Defina a duracao de cada item, o efeito de transicao, o modo de ajuste (cobrir ou conter) e o audio. Depois ligue a playlist a uma zona da tela." },
    { icon: "clock", title: "4. Agendamentos", text: "Quer conteudos diferentes por horario ou dia da semana? Em Agendamentos voce define quando cada playlist toca em cada zona. Sem agendamento, a playlist padrao da zona e usada o tempo todo." },
    { icon: "eye", title: "5. Publicar na TV", text: "Abra a tela, copie o link do player e abra esse link no navegador da TV (ou use o botao Pre-visualizar). As mudancas feitas aqui aparecem na TV ao vivo, sem precisar recarregar a pagina." },
    { icon: "sun", title: "6. Widgets e tickers", text: "Alem de imagens e videos, adicione widgets: relogio, clima (automatico pela cidade), ticker de noticias (RSS + mensagens) e ticker de promocoes. Clique com o botao direito numa zona e escolha o widget, ou use Nova midia." },
    { icon: "search", title: "Dica final", text: "Pressione Ctrl+K a qualquer momento para abrir a paleta de comandos e ir direto a qualquer acao. Para rever este guia depois, procure por 'Abrir guia de uso' na paleta. Bom trabalho!" },
  ];
  let tourIndex = 0;
  function renderOnboard() {
    const s = TOUR[tourIndex];
    $("onboard-figure").innerHTML = ICONS[s.icon] || ICONS.info;
    $("onboard-step").textContent = "Passo " + (tourIndex + 1) + " de " + TOUR.length;
    $("onboard-title").textContent = s.title;
    $("onboard-text").textContent = s.text;
    $("onboard-dots").innerHTML = TOUR.map((_, i) => '<span class="dot ' + (i === tourIndex ? "on" : "") + '" data-dot="' + i + '"></span>').join("");
    $("onboard-dots").querySelectorAll("[data-dot]").forEach((d) => d.addEventListener("click", () => { tourIndex = Number(d.dataset.dot); renderOnboard(); }));
    $("onboard-prev").disabled = tourIndex === 0;
    $("onboard-next").textContent = tourIndex === TOUR.length - 1 ? "Concluir" : "Proximo";
  }
  function openOnboard() { tourIndex = 0; $("onboard").hidden = false; renderOnboard(); }
  function closeOnboard() { $("onboard").hidden = true; localStorage.setItem(ONBOARD_KEY, "1"); }
  function maybeOnboard() { if (!localStorage.getItem(ONBOARD_KEY)) setTimeout(openOnboard, 450); }

  // ------------------------------- Tema ---------------------------- //
  function toggleTheme() {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("adsignage_studio_theme", next);
    const meta = document.querySelector('meta[name="theme-color"]'); if (meta) meta.setAttribute("content", next === "dark" ? "#1a1b26" : "#e6e7ed");
    toast({ kind: "info", msg: "Tema " + (next === "dark" ? "escuro" : "claro") + " ativado.", timeout: 1500 });
  }

  // --------------------------- Render geral ------------------------ //
  function renderAll() { renderActivity(); renderMenu(); renderSidebar(); renderTabs(); renderDoc(); renderInspector(); renderBottom(); renderStatus(); }

  // ----------------------------- Auth ------------------------------ //
  async function showApp() {
    $("login").classList.add("hidden"); $("ide").classList.remove("hidden");
    if (!state.user) {
      try { const me = await loadMe(); state.user = { username: me.username, role: me.role, is_super_admin: !!me.is_super_admin, company_id: me.company_id }; }
      catch (e) { /* segue sem perfil */ }
    }
    await loadAll(); maybeOnboard();
  }
  function logout() {
    try {
      if (token) fetch("/api/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + token }, keepalive: true }).catch(() => {});
    } catch (e) { /* best-effort */ }
    token = null; state.user = null; state.activeCompanyId = null; state.companies = []; state.branding = null; localStorage.removeItem(TOKEN_KEY); $("superadmin").classList.add("hidden"); $("ide").classList.add("hidden"); $("login").classList.remove("hidden");
  }

  // --------------------------- Inicializacao ----------------------- //
  function init() {
    document.documentElement.setAttribute("data-theme", localStorage.getItem("adsignage_studio_theme") || "dark");
    $("brand-mark").innerHTML = ICONS.logo;
    $("login-mark").innerHTML = ICONS.logo;
    $("cmd-open-icon").innerHTML = ICONS.search;
    $("logout-icon").innerHTML = ICONS.power;
    $("sa-mark").innerHTML = ICONS.shield;
    $("sa-studio-ico").innerHTML = ICONS.layout;
    $("sa-logout-ico").innerHTML = ICONS.power;
    $("sa-open-studio").addEventListener("click", closeSuperAdmin);
    $("sa-logout").addEventListener("click", logout);

    $("login-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const password = $("login-password").value; const errEl = $("login-error"); errEl.textContent = "";
      const usernameEl = $("login-username"); const username = usernameEl && usernameEl.value.trim() ? usernameEl.value.trim() : undefined;
      try {
        const resp = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: username, password: password }) });
        if (!resp.ok) throw new Error("Senha incorreta.");
        const json = await resp.json(); token = json.token; state.user = { username: json.username, role: json.role, is_super_admin: !!json.is_super_admin, company_id: json.company_id, company_name: json.company_name }; state.activeCompanyId = null; localStorage.setItem(TOKEN_KEY, token); await showApp(); if (state.user && state.user.is_super_admin) openSuperAdmin();
      } catch (err) { errEl.textContent = err.message; }
    });
    $("logout").addEventListener("click", logout);
    $("onboard-skip").addEventListener("click", closeOnboard);
    $("onboard-prev").addEventListener("click", () => { if (tourIndex > 0) { tourIndex--; renderOnboard(); } });
    $("onboard-next").addEventListener("click", () => { if (tourIndex < TOUR.length - 1) { tourIndex++; renderOnboard(); } else { closeOnboard(); } });
    $("onboard").addEventListener("click", (e) => { if (e.target === $("onboard")) closeOnboard(); });
    $("cmd-open").addEventListener("click", openPalette);
    $("palette").addEventListener("click", (e) => { if (e.target === $("palette")) closePalette(); });
    $("palette-input").addEventListener("input", (e) => { const q = e.target.value.toLowerCase(); palFiltered = COMMANDS.filter((c) => c.label.toLowerCase().includes(q)); palIndex = 0; renderPalette(); });
    $("palette-input").addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); palIndex = Math.min(palIndex + 1, palFiltered.length - 1); renderPalette(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); palIndex = Math.max(palIndex - 1, 0); renderPalette(); }
      else if (e.key === "Enter") { e.preventDefault(); runPalette(palIndex); }
    });
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); if ($("login").classList.contains("hidden")) { $("palette").hidden ? openPalette() : closePalette(); } }
      else if (e.key === "Escape") { closePalette(); closeMenu(); closeZoneQuickMenu(); }
    });
    // Fecha os menus suspensos ao clicar em qualquer lugar fora deles.
    document.addEventListener("click", (e) => { if (openMenuIndex !== null && !e.target.closest(".menu-group")) closeMenu(); });
    document.addEventListener("click", (e) => { if (!e.target.closest("#zone-ctx")) closeZoneQuickMenu(); });

    if ("serviceWorker" in navigator) window.addEventListener("load", () => {
      navigator.serviceWorker.register("sw.js").then((reg) => { reg.update(); }).catch(() => {});
      let swReloaded = false;
      navigator.serviceWorker.addEventListener("controllerchange", () => { if (swReloaded) return; swReloaded = true; location.reload(); });
    });

    setInterval(() => { if (token && !isDragging && $("palette").hidden && state.activeSection === "screens") { loadScreens().then(() => { renderSidebar(); renderStatus(); }).catch(() => {}); } }, 30000);

    if (token) showApp(); else logout();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
