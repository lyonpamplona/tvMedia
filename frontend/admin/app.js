/**
 * AdSignage Studio - painel de edicao profissional (estilo IDE) para
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
  };

  const TYPE_ICON = { image: "image", video: "video", text: "text", html: "code", url: "link", youtube: "youtube", embed: "music" };
  const TYPE_LABEL = { image: "Imagem", video: "Video", text: "Texto", html: "HTML", url: "URL", youtube: "YouTube", embed: "Embed" };
  const FITS = ["contain", "cover", "fill"];
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
    activeSection: "screens",
    activeScreenId: null,
    selectedZoneId: null,
    selectedMediaId: null,
    openPlaylistId: null,
    bottomTab: "timeline",
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

  /** Carrega todos os dados e renderiza o painel. */
  async function loadAll() {
    try {
      await Promise.all([loadMedia(), loadPlaylists(), loadScreens()]);
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
      '<button class="act" data-act="theme" title="Alternar tema">' + ICONS.sun + '</button>' +
      '<button class="act" data-act="settings" title="Configuracoes">' + ICONS.settings + '</button>';
    bar.querySelectorAll("[data-sec]").forEach((b) => b.addEventListener("click", () => { state.activeSection = b.dataset.sec; renderActivity(); renderSidebar(); renderTabs(); renderDoc(); renderInspector(); renderBottom(); }));
    bar.querySelector('[data-act="theme"]').addEventListener("click", toggleTheme);
    bar.querySelector('[data-act="settings"]').addEventListener("click", () => toast({ kind: "info", title: "Configuracoes", msg: "Tema, PWA e sessao ficam na barra de atividades e titulo." }));
  }

  function renderMenu() {
    const items = ["Projeto", "Editar", "Visualizar", "Ajuda"];
    $("menu").innerHTML = items.map((m) => '<button data-menu="' + m + '">' + m + '</button>').join("");
    $("menu").querySelectorAll("[data-menu]").forEach((b) => b.addEventListener("click", () => openPalette()));
  }

  // ----------------------------- Sidebar --------------------------- //
  function sideHead(title, actions) {
    return '<div class="side-head"><span>' + title + '</span><span class="acts">' + (actions || []).map((a) => '<button data-side-act="' + a.act + '" title="' + a.title + '">' + ICONS[a.icon] + '</button>').join("") + '</span></div>';
  }

  function renderSidebar() {
    const sb = $("sidebar");
    if (state.activeSection === "screens") {
      sb.innerHTML = sideHead("Telas", [{ act: "add-screen", icon: "plus", title: "Nova tela" }, { act: "reload", icon: "refresh", title: "Recarregar" }]) +
        '<div class="tree"><div class="tree-group"><div class="tree-label" data-toggle><span class="chev">' + ICONS.chevron + '</span><span>Dispositivos</span></div><div class="tree-children">' +
        (state.screens.length ? state.screens.map((s) => '<div class="tree-item ' + (s.id === state.activeScreenId ? "active" : "") + '" data-screen="' + s.id + '"><span class="dot ' + (isOnline(s) ? "on" : "off") + '"></span><span class="name">' + esc(s.name) + '</span><span class="tag">' + s.zones.length + 'z</span></div>').join("") : '<div class="empty">Nenhuma tela.</div>') +
        '</div></div></div>';
    } else if (state.activeSection === "media") {
      sb.innerHTML = sideHead("Midias", [{ act: "reload", icon: "refresh", title: "Recarregar" }]) +
        '<div class="tree">' + (state.media.length ? state.media.map((m) => '<div class="tree-item ' + (m.id === state.selectedMediaId ? "active" : "") + '" data-media="' + m.id + '">' + ICONS[TYPE_ICON[m.type]] + '<span class="name">' + esc(m.name) + '</span><span class="tag">' + TYPE_LABEL[m.type] + '</span></div>').join("") : '<div class="empty">Nenhuma midia.</div>') + '</div>';
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
      else if (act === "add-screen") {
        const created = await api("/api/screens", { method: "POST", body: JSON.stringify({ name: "Nova TV", timezone: "America/Sao_Paulo" }) });
        await loadScreens(); state.activeScreenId = created.id; const s = screen(); state.selectedZoneId = s && s.zones[0] ? s.zones[0].id : null; renderAll(); toast({ kind: "ok", msg: "Tela criada." });
      } else if (act === "add-playlist") {
        const created = await api("/api/playlists", { method: "POST", body: JSON.stringify({ name: "Nova playlist" }) });
        await loadPlaylists(); state.openPlaylistId = created.id; renderSidebar(); renderTabs(); renderDoc(); toast({ kind: "ok", msg: "Playlist criada." });
      }
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
    stage.innerHTML = sc.zones.slice().sort((a, b) => a.z_index - b.z_index).map((z) => {
      const pl = playlistById(z.default_playlist_id);
      const body = pl ? esc(pl.name) + " - " + pl.items.length + " item(s)" : "Sem playlist padrao";
      return '<div class="zone ' + (z.id === state.selectedZoneId ? "selected" : "") + '" data-zone="' + z.id + '" style="left:' + z.x + '%;top:' + z.y + '%;width:' + z.width + '%;height:' + z.height + '%"><div class="zone-label">' + ICONS.layout + '<span>' + esc(z.name) + '</span></div><div class="zone-body">' + body + '</div><div class="resize" data-resize="' + z.id + '"></div></div>';
    }).join("");
    $("stage-hint").textContent = sc.name + " - " + sc.zones.length + " zona(s) - arraste para mover, use o canto para redimensionar";
    bindZoneInteractions();
  }

  function bindZoneInteractions() {
    const stage = $("stage");
    stage.querySelectorAll("[data-zone]").forEach((el) => {
      el.addEventListener("pointerdown", (e) => {
        if (e.target.closest("[data-resize]")) return;
        const z = zoneOf(Number(el.dataset.zone));
        state.selectedZoneId = z.id; renderInspector(); markSelected();
        startDrag(e, z, "move");
      });
    });
    stage.querySelectorAll("[data-resize]").forEach((el) => {
      el.addEventListener("pointerdown", (e) => { e.stopPropagation(); const z = zoneOf(Number(el.dataset.resize)); state.selectedZoneId = z.id; renderInspector(); markSelected(); startDrag(e, z, "resize"); });
    });
  }
  function zoneOf(id) { return screen().zones.find((z) => z.id === id); }
  function markSelected() { const stage = $("stage"); if (!stage) return; stage.querySelectorAll("[data-zone]").forEach((el) => el.classList.toggle("selected", Number(el.dataset.zone) === state.selectedZoneId)); }

  function startDrag(e, z, mode) {
    e.preventDefault();
    isDragging = true;
    const rect = $("stage").getBoundingClientRect();
    const sx = e.clientX, sy = e.clientY;
    const o = { x: z.x, y: z.y, w: z.width, h: z.height };
    const move = (ev) => {
      const dx = ((ev.clientX - sx) / rect.width) * 100;
      const dy = ((ev.clientY - sy) / rect.height) * 100;
      if (mode === "move") { z.x = clamp(Math.round(o.x + dx), 0, 100 - z.width); z.y = clamp(Math.round(o.y + dy), 0, 100 - z.height); }
      else { z.width = clamp(Math.round(o.w + dx), 5, 100 - z.x); z.height = clamp(Math.round(o.h + dy), 5, 100 - z.y); }
      applyZoneGeometry(z); syncInspectorGeometry(z);
    };
    const up = async () => {
      document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); isDragging = false;
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
      '<div class="insp-section"><h5>Conteudo</h5>' + field("Playlist padrao", '<select id="f-playlist"><option value="">- sem playlist -</option>' + state.playlists.map((p) => '<option value="' + p.id + '"' + (p.id === z.default_playlist_id ? " selected" : "") + '>' + esc(p.name) + '</option>').join("") + '</select>') +
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
      '<button class="btn ghost block small" style="margin-top:8px" data-preview-screen>' + ICONS.eye + ' Pre-visualizar player</button></div>' +
      '<div class="insp-section"><button class="btn block" data-add-zone>' + ICONS.plus + ' Adicionar zona</button><button class="btn danger block small" style="margin-top:8px" data-del-screen>' + ICONS.trash + ' Excluir tela</button></div>';
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
      const dz = insp.querySelector("[data-dup-zone]"); if (dz) dz.addEventListener("click", async () => { try { await api("/api/screens/" + screenId + "/zones", { method: "POST", body: JSON.stringify({ name: z.name + " (copia)", x: clamp(z.x + 5, 0, 90), y: clamp(z.y + 5, 0, 90), width: z.width, height: z.height, z_index: z.z_index + 1, default_playlist_id: z.default_playlist_id }) }); await loadScreens(); const s = screen(); state.selectedZoneId = s.zones[s.zones.length - 1].id; renderAll(); toast({ kind: "ok", msg: "Zona duplicada." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
      const del = insp.querySelector("[data-del-zone]"); if (del) del.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir zona", message: "Tem certeza que deseja excluir esta zona? Esta acao nao pode ser desfeita.", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/screens/" + screenId + "/zones/" + z.id, { method: "DELETE" }); await loadScreens(); const s = screen(); state.selectedZoneId = s && s.zones[0] ? s.zones[0].id : null; renderAll(); toast({ kind: "warn", msg: "Zona excluida." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
      insp.querySelectorAll("#sf-days .day").forEach((d) => d.addEventListener("click", () => d.classList.toggle("on")));
      const as = insp.querySelector("[data-add-sched]"); if (as) as.addEventListener("click", () => addSchedule(z.id));
      insp.querySelectorAll("[data-del-sched]").forEach((b) => b.addEventListener("click", () => deleteSchedule(z.id, Number(b.dataset.delSched))));
    } else {
      const sc = screen();
      const sn = $("f-sname"); if (sn) { sn.addEventListener("input", () => { sc.name = sn.value; renderTabs(); renderSidebar(); }); sn.addEventListener("change", () => patchScreen(sc.id, { name: sn.value })); }
      const tz = $("f-tz"); if (tz) tz.addEventListener("change", () => patchScreen(sc.id, { timezone: tz.value }));
      const cl = insp.querySelector("[data-copy-link]"); if (cl) cl.addEventListener("click", () => copyText(playerUrl(sc.slug)));
      const pv = insp.querySelector("[data-preview-screen]"); if (pv) pv.addEventListener("click", () => window.open(playerUrl(sc.slug), "_blank"));
      const az = insp.querySelector("[data-add-zone]"); if (az) az.addEventListener("click", async () => { try { await api("/api/screens/" + sc.id + "/zones", { method: "POST", body: JSON.stringify({ name: "Nova zona", x: 10, y: 10, width: 40, height: 40, z_index: sc.zones.length + 1 }) }); await loadScreens(); const s = screen(); state.selectedZoneId = s.zones[s.zones.length - 1].id; renderAll(); toast({ kind: "ok", msg: "Zona adicionada." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
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

  // ----------------------------- Midias ---------------------------- //
  function renderMediaDoc() {
    const typeOpts = Object.keys(TYPE_LABEL).map((t) => '<option value="' + t + '">' + TYPE_LABEL[t] + '</option>').join("");
    const form = '<div class="item-row row wrap" style="gap:10px;margin-bottom:14px"><input id="m-name" placeholder="Nome da midia" style="flex:1;min-width:160px"/><select id="m-type">' + typeOpts + '</select><input id="m-file" type="file" accept="image/*,video/*"/><input id="m-value" placeholder="Texto, HTML ou URL" class="hidden" style="flex:1;min-width:160px"/><button class="btn primary small" id="m-add">' + ICONS.plus + ' Adicionar</button></div>';
    const grid = state.media.length ? '<div class="media-grid">' + state.media.map(mediaCard).join("") + '</div>' : '<div class="empty">Nenhuma midia cadastrada.</div>';
    return form + grid;
  }
  function mediaCard(m) {
    let thumb;
    if (m.type === "image" && m.path) thumb = '<div class="thumb"><img src="/media/' + esc(m.path) + '" alt=""/></div>';
    else if (m.type === "video" && m.path) thumb = '<div class="thumb"><video src="/media/' + esc(m.path) + '" muted></video></div>';
    else thumb = '<div class="thumb placeholder">' + ICONS[TYPE_ICON[m.type]] + '</div>';
    return '<div class="media-card" data-mcard="' + m.id + '">' + thumb + '<div class="mc-body"><div class="mc-name">' + esc(m.name) + '</div><div class="mc-foot"><span class="tag">' + TYPE_LABEL[m.type] + '</span><button class="btn danger small" data-del-media="' + m.id + '">' + ICONS.trash + '</button></div></div></div>';
  }
  function bindMediaDoc() {
    const doc = $("doc");
    const typeSel = $("m-type"); const fileI = $("m-file"); const valI = $("m-value");
    const sync = () => { const t = typeSel.value; const isFile = (t === "image" || t === "video"); fileI.classList.toggle("hidden", !isFile); valI.classList.toggle("hidden", isFile); };
    sync(); typeSel.addEventListener("change", sync);
    $("m-add").addEventListener("click", addMedia);
    doc.querySelectorAll("[data-mcard]").forEach((c) => c.addEventListener("click", (e) => { if (e.target.closest("[data-del-media]")) return; state.selectedMediaId = Number(c.dataset.mcard); renderSidebar(); renderInspector(); }));
    doc.querySelectorAll("[data-del-media]").forEach((b) => b.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir midia", message: "Tem certeza que deseja excluir esta midia?", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/media/" + b.dataset.delMedia, { method: "DELETE" }); await loadMedia(); renderSidebar(); renderDoc(); toast({ kind: "warn", msg: "Midia excluida." }); } catch (err) { toast({ kind: "err", msg: err.message }); } }));
  }
  async function addMedia() {
    const name = $("m-name").value.trim();
    const type = $("m-type").value;
    if (!name) { toast({ kind: "warn", msg: "Informe um nome." }); return; }
    try {
      if (type === "image" || type === "video") {
        const file = $("m-file").files[0]; if (!file) { toast({ kind: "warn", msg: "Selecione um arquivo." }); return; }
        const fd = new FormData(); fd.append("name", name); fd.append("file", file);
        await api("/api/media/upload", { method: "POST", body: fd });
      } else {
        const value = $("m-value").value;
        const body = { name, type };
        if (type === "url" || type === "youtube" || type === "embed") body.source_url = value; else body.content = value;
        await api("/api/media", { method: "POST", body: JSON.stringify(body) });
      }
      await loadMedia(); renderSidebar(); renderDoc(); toast({ kind: "ok", msg: "Midia adicionada." });
    } catch (err) { toast({ kind: "err", msg: err.message }); }
  }
  function renderMediaInspector() {
    const m = mediaById(state.selectedMediaId);
    if (!m) return '<div class="insp-head">' + ICONS.media + '<span>Midias</span></div><div class="insp-section"><p class="empty" style="padding:0">Selecione uma midia para editar nome e conteudo.</p></div>';
    let valField = "";
    if (m.type === "text" || m.type === "html") valField = field("Conteudo", '<textarea id="mi-content">' + esc(m.content || "") + '</textarea>');
    else if (m.type === "url" || m.type === "youtube" || m.type === "embed") valField = field("URL de origem", '<input id="mi-url" value="' + esc(m.source_url || "") + '"/>');
    else valField = '<div class="field"><label>Arquivo</label><div class="code">' + esc(m.path || "-") + '</div></div>';
    return '<div class="insp-head">' + ICONS[TYPE_ICON[m.type]] + '<span>' + esc(m.name) + '</span></div><div class="insp-section"><h5>' + TYPE_LABEL[m.type] + '</h5>' + field("Nome", '<input id="mi-name" value="' + esc(m.name) + '"/>') + valField + '<button class="btn primary block small" data-save-media>' + ICONS.check + ' Salvar</button></div>';
  }
  function bindMediaInspector() {
    const insp = $("inspector"); const m = mediaById(state.selectedMediaId); if (!m) return;
    const save = insp.querySelector("[data-save-media]"); if (!save) return;
    save.addEventListener("click", async () => {
      const patch = { name: $("mi-name").value };
      if ($("mi-content")) patch.content = $("mi-content").value;
      if ($("mi-url")) patch.source_url = $("mi-url").value;
      try { await api("/api/media/" + m.id, { method: "PATCH", body: JSON.stringify(patch) }); await loadMedia(); renderSidebar(); renderDoc(); renderInspector(); toast({ kind: "ok", msg: "Midia atualizada." }); } catch (err) { toast({ kind: "err", msg: err.message }); }
    });
  }

  // ---------------------------- Playlists -------------------------- //
  function renderPlaylistDoc() {
    const pl = playlistById(state.openPlaylistId);
    if (!pl) return '<div class="empty">Nenhuma playlist selecionada. Use o botao + na barra lateral.</div>';
    const head = '<div class="item-row row between" style="margin-bottom:12px"><strong style="font-size:14px">' + esc(pl.name) + '</strong><span class="row"><button class="btn ghost small" data-rename-pl>Renomear</button><button class="btn danger small" data-del-pl>' + ICONS.trash + ' Excluir</button></span></div>';
    const items = pl.items.length ? pl.items.map((it, i) => itemRow(pl, it, i)).join("") : '<div class="empty">Sem itens. Adicione abaixo.</div>';
    const mediaOpts = state.media.map((m) => '<option value="' + m.id + '">' + esc(m.name) + ' (' + TYPE_LABEL[m.type] + ')</option>').join("");
    const add = '<div class="item-row row wrap" style="margin-top:12px;gap:10px"><select id="pi-media" style="flex:1;min-width:160px">' + mediaOpts + '</select><input id="pi-dur" type="number" min="1" value="10" class="mini" title="Duracao (s)"/><select id="pi-fit">' + FITS.map((f) => '<option>' + f + '</option>').join("") + '</select><select id="pi-trans">' + TRANSITIONS.map((t) => '<option>' + t + '</option>').join("") + '</select><label class="row" style="gap:5px"><input id="pi-sound" type="checkbox"/> som</label><button class="btn primary small" id="pi-add">' + ICONS.plus + ' Item</button></div>';
    return '<div class="pl-editor">' + head + '<div class="pl-items">' + items + '</div>' + add + '</div>';
  }
  function itemRow(pl, it, i) {
    const md = it.media;
    return '<div class="item-row" data-item="' + it.id + '"><span class="tag">' + (i + 1) + '</span>' + ICONS[TYPE_ICON[md.type]] + '<span class="grow">' + esc(md.name) + '</span>' +
      '<input type="number" min="1" value="' + it.duration + '" class="mini" data-it-dur="' + it.id + '" title="Duracao (s)"/>' +
      '<select data-it-fit="' + it.id + '">' + FITS.map((f) => '<option ' + (f === it.fit ? "selected" : "") + '>' + f + '</option>').join("") + '</select>' +
      '<select data-it-trans="' + it.id + '">' + TRANSITIONS.map((t) => '<option ' + (t === it.transition ? "selected" : "") + '>' + t + '</option>').join("") + '</select>' +
      '<label class="row" style="gap:4px" title="Som"><input type="checkbox" data-it-sound="' + it.id + '" ' + (it.muted ? "" : "checked") + '/></label>' +
      '<button class="btn ghost small" data-it-up="' + it.id + '">' + ICONS.up + '</button><button class="btn ghost small" data-it-down="' + it.id + '">' + ICONS.down + '</button>' +
      '<button class="btn danger small" data-it-del="' + it.id + '">' + ICONS.trash + '</button></div>';
  }
  function bindPlaylistDoc() {
    const doc = $("doc"); const pl = playlistById(state.openPlaylistId); if (!pl) return;
    const rn = doc.querySelector("[data-rename-pl]"); if (rn) rn.addEventListener("click", async () => { const name = await promptDialog({ title: "Renomear playlist", message: "Digite o novo nome da playlist:", icon: "playlist", defaultValue: pl.name, placeholder: "Nome da playlist", confirmText: "Salvar" }); if (!name) return; try { await api("/api/playlists/" + pl.id, { method: "PATCH", body: JSON.stringify({ name }) }); await loadPlaylists(); renderSidebar(); renderDoc(); toast({ kind: "ok", msg: "Playlist renomeada." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
    const dp = doc.querySelector("[data-del-pl]"); if (dp) dp.addEventListener("click", async () => { if (!(await confirmDialog({ title: "Excluir playlist", message: "Tem certeza que deseja excluir esta playlist?", icon: "trash", confirmText: "Excluir", danger: true }))) return; try { await api("/api/playlists/" + pl.id, { method: "DELETE" }); state.openPlaylistId = null; await loadPlaylists(); fixSelection(); renderSidebar(); renderDoc(); renderBottom(); toast({ kind: "warn", msg: "Playlist excluida." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
    const add = $("pi-add"); if (add) add.addEventListener("click", async () => { const media_id = Number($("pi-media").value); if (!media_id) { toast({ kind: "warn", msg: "Selecione uma midia." }); return; } const body = { media_id, duration: Number($("pi-dur").value) || 10, fit: $("pi-fit").value, transition: $("pi-trans").value, muted: !$("pi-sound").checked }; try { await api("/api/playlists/" + pl.id + "/items", { method: "POST", body: JSON.stringify(body) }); await loadPlaylists(); renderSidebar(); renderDoc(); renderBottom(); toast({ kind: "ok", msg: "Item adicionado." }); } catch (err) { toast({ kind: "err", msg: err.message }); } });
    doc.querySelectorAll("[data-it-dur]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itDur, { duration: Number(el.value) })));
    doc.querySelectorAll("[data-it-fit]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itFit, { fit: el.value })));
    doc.querySelectorAll("[data-it-trans]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itTrans, { transition: el.value })));
    doc.querySelectorAll("[data-it-sound]").forEach((el) => el.addEventListener("change", () => updateItem(pl.id, el.dataset.itSound, { muted: !el.checked })));
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
    if (state.bottomTab === "timeline") c.innerHTML = renderTimeline();
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
    return '<div class="timeline"><div class="track-head"><span>' + esc(pl.name) + '</span><span class="mono">ciclo total: ' + total + 's</span></div><div class="track">' + pl.items.map((it, i) => '<div class="seg ' + alts[i % 3] + '" style="flex:' + it.duration + '"><strong>' + esc(it.media.name) + '</strong><small>' + it.duration + 's - ' + it.transition + (it.muted ? " - mudo" : " - som") + '</small></div>').join("") + '</div></div>';
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
  const ONBOARD_KEY = "adsignage_onboarded";
  const TOUR = [
    { icon: "logo", title: "Bem-vindo ao AdSignage Studio", text: "Este painel controla o que aparece nas suas TVs. Em poucos passos voce cria uma tela, envia midias, monta uma sequencia e publica. Use Anterior e Proximo para navegar neste guia." },
    { icon: "screen", title: "1. Telas", text: "Cada tela representa uma TV. Na secao Telas voce cria a tela e desenha Zonas: areas onde o conteudo aparece. Arraste e redimensione as zonas direto no canvas, como caixas na tela." },
    { icon: "media", title: "2. Midias", text: "Na secao Midias voce envia imagens e videos do seu computador, ou cadastra links (YouTube, paginas web, musica). Tudo o que sera exibido fica guardado aqui para reaproveitar." },
    { icon: "playlist", title: "3. Playlists", text: "Uma playlist e a sequencia de midias que toca em loop. Defina a duracao de cada item, o efeito de transicao, o modo de ajuste (cobrir ou conter) e o audio. Depois ligue a playlist a uma zona da tela." },
    { icon: "clock", title: "4. Agendamentos", text: "Quer conteudos diferentes por horario ou dia da semana? Em Agendamentos voce define quando cada playlist toca em cada zona. Sem agendamento, a playlist padrao da zona e usada o tempo todo." },
    { icon: "eye", title: "5. Publicar na TV", text: "Abra a tela, copie o link do player e abra esse link no navegador da TV (ou use o botao Pre-visualizar). As mudancas feitas aqui aparecem na TV ao vivo, sem precisar recarregar a pagina." },
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
  function showApp() { $("login").classList.add("hidden"); $("ide").classList.remove("hidden"); loadAll(); maybeOnboard(); }
  function logout() { token = null; localStorage.removeItem(TOKEN_KEY); $("ide").classList.add("hidden"); $("login").classList.remove("hidden"); }

  // --------------------------- Inicializacao ----------------------- //
  function init() {
    document.documentElement.setAttribute("data-theme", localStorage.getItem("adsignage_studio_theme") || "dark");
    $("brand-mark").innerHTML = ICONS.logo;
    $("login-mark").innerHTML = ICONS.logo;
    $("cmd-open-icon").innerHTML = ICONS.search;
    $("logout-icon").innerHTML = ICONS.power;

    $("login-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const password = $("login-password").value; const errEl = $("login-error"); errEl.textContent = "";
      try {
        const resp = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
        if (!resp.ok) throw new Error("Senha incorreta.");
        const json = await resp.json(); token = json.token; localStorage.setItem(TOKEN_KEY, token); showApp();
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
      else if (e.key === "Escape") closePalette();
    });

    if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));

    setInterval(() => { if (token && !isDragging && $("palette").hidden && state.activeSection === "screens") { loadScreens().then(() => { renderSidebar(); renderStatus(); }).catch(() => {}); } }, 30000);

    if (token) showApp(); else logout();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
