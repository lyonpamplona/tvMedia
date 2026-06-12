/**
 * AdSignage Studio - Prototipo de IDE de edicao para sinalizacao digital.
 *
 * Prototipo navegavel com dados de exemplo (mock) em memoria. Demonstra um
 * painel profissional completo: barra de atividades, explorer em arvore,
 * editor com canvas de zonas arrastaveis/redimensionaveis, inspetor de
 * propriedades com edicao ao vivo, painel inferior (linha do tempo, logs e
 * problemas), paleta de comandos (Ctrl+K), toasts e barra de status.
 *
 * Todos os icones sao SVG (nenhum emoji). A estrutura mapeia a API real.
 */
(() => {
  "use strict";

  // ----------------------------- Icones SVG ------------------------ //
  const S = (p, vb) => `<svg viewBox="${vb || "0 0 24 24"}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
  const ICONS = {
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
    publish: S('<path d="M12 19V5M5 12l7-7 7 7"/>'),
    eye: S('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>'),
    copy: S('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
    trash: S('<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>'),
    move: S('<path d="M12 2v20M2 12h20M9 5l3-3 3 3M9 19l3 3 3 3M5 9l-3 3 3 3M19 9l3 3-3 3"/>'),
    sun: S('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M5 5l1.5 1.5M17.5 17.5 19 19M2 12h2M20 12h2M5 19l1.5-1.5M17.5 6.5 19 5"/>'),
    branch: S('<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 8.5v7M18 10.5c0 3-4 2.5-4 6.5-0 0"/>'),
    wifi: S('<path d="M5 12a10 10 0 0 1 14 0M8.5 15.5a5 5 0 0 1 7 0M12 19h.01"/>'),
  };

  const TYPE_ICON = { image: "image", video: "video", text: "text", html: "code", url: "link", youtube: "youtube", embed: "music" };
  const TYPE_LABEL = { image: "Imagem", video: "Video", text: "Texto", html: "HTML", url: "URL", youtube: "YouTube", embed: "Musica" };
  const FITS = ["contain", "cover", "fill"];
  const TRANSITIONS = ["none", "fade", "slide"];
  const DAYS = ["S", "T", "Q", "Q", "S", "S", "D"];

  // ----------------------- Dados de exemplo ------------------------ //
  let uid = 100;
  const nid = () => ++uid;

  const state = {
    media: [
      { id: 1, name: "Promo Verao.jpg", type: "image" },
      { id: 2, name: "Institucional.mp4", type: "video" },
      { id: 3, name: "Lo-fi Beats", type: "embed" },
      { id: 4, name: "Ofertas do dia", type: "youtube" },
      { id: 5, name: "Aviso de horario", type: "text" },
      { id: 6, name: "Cardapio.html", type: "html" },
    ],
    playlists: [
      { id: 1, name: "Vitrine principal", items: [
        { id: 11, mediaId: 1, duration: 12, fit: "cover", transition: "fade", muted: true },
        { id: 12, mediaId: 2, duration: 30, fit: "contain", transition: "slide", muted: false },
        { id: 13, mediaId: 4, duration: 20, fit: "cover", transition: "fade", muted: true },
      ] },
      { id: 2, name: "Faixa de musica", items: [
        { id: 21, mediaId: 3, duration: 60, fit: "contain", transition: "none", muted: false },
      ] },
      { id: 3, name: "Rodape de avisos", items: [
        { id: 31, mediaId: 5, duration: 8, fit: "contain", transition: "fade", muted: true },
        { id: 32, mediaId: 6, duration: 10, fit: "contain", transition: "fade", muted: true },
      ] },
    ],
    screens: [
      { id: 1, name: "TV Entrada", slug: "tv-entrada", online: true, timezone: "America/Sao_Paulo",
        zones: [
          { id: 101, name: "Principal", x: 0, y: 0, w: 100, h: 80, z: 1, playlistId: 1,
            schedules: [{ id: 201, playlistId: 1, days: [0,1,2,3,4], start: "08:00", end: "18:00", priority: 10 }] },
          { id: 102, name: "Rodape", x: 0, y: 80, w: 100, h: 20, z: 2, playlistId: 3, schedules: [] },
        ] },
      { id: 2, name: "TV Caixa", slug: "tv-caixa", online: false, timezone: "America/Sao_Paulo",
        zones: [
          { id: 103, name: "Tela cheia", x: 0, y: 0, w: 100, h: 100, z: 1, playlistId: 2, schedules: [] },
        ] },
    ],
    activeSection: "screens",
    activeScreenId: 1,
    selectedZoneId: 101,
    bottomTab: "timeline",
    revision: "a1b2c3d4",
  };

  const $ = (id) => document.getElementById(id);
  const screen = () => state.screens.find((s) => s.id === state.activeScreenId);
  const zone = () => (screen() ? screen().zones.find((z) => z.id === state.selectedZoneId) : null);
  const playlistById = (id) => state.playlists.find((p) => p.id === id);
  const mediaById = (id) => state.media.find((m) => m.id === id);
  const esc = (v) => { const d = document.createElement("div"); d.textContent = v == null ? "" : String(v); return d.innerHTML; };
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

  // ------------------------------ Toasts --------------------------- //
  function toast(opts) {
    const o = typeof opts === "string" ? { msg: opts } : opts;
    const kind = o.kind || "info";
    const ico = { ok: "check", info: "info", warn: "alert", err: "alert" }[kind] || "info";
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.innerHTML = `<span class="tico">${ICONS[ico]}</span>` +
      `<div class="tbody"><div class="ttitle">${esc(o.title || ({ ok: "Sucesso", info: "Informacao", warn: "Atencao", err: "Erro" }[kind]))}</div>` +
      `<div class="tmsg">${esc(o.msg || "")}</div></div>` +
      `<button class="tclose">${ICONS.close}</button>`;
    $("toast-stack").appendChild(el);
    requestAnimationFrame(() => el.classList.add("show"));
    const kill = () => { el.classList.remove("show"); setTimeout(() => el.remove(), 300); };
    el.querySelector(".tclose").addEventListener("click", kill);
    setTimeout(kill, o.timeout || 3200);
  }

  // ---------------------------- Atividades ------------------------- //
  const SECTIONS = [
    { id: "screens", label: "Telas", icon: "screen" },
    { id: "media", label: "Midias", icon: "media" },
    { id: "playlists", label: "Playlists", icon: "playlist" },
    { id: "schedules", label: "Agendamentos", icon: "clock" },
    { id: "search", label: "Buscar", icon: "search" },
  ];

  function renderActivity() {
    $("activitybar").innerHTML =
      SECTIONS.map((s) => `<button class="act ${s.id === state.activeSection ? "active" : ""}" data-sec="${s.id}" title="${s.label}">${ICONS[s.icon]}</button>`).join("") +
      `<div class="spacer"></div>` +
      `<button class="act" data-act="theme" title="Alternar tema">${ICONS.sun}</button>` +
      `<button class="act" data-sec="settings" title="Configuracoes">${ICONS.settings}</button>`;
    $("activitybar").querySelectorAll("[data-sec]").forEach((b) => b.addEventListener("click", () => { state.activeSection = b.dataset.sec; renderSidebar(); renderActivity(); }));
    $("activitybar").querySelector('[data-act="theme"]').addEventListener("click", toggleTheme);
  }

  // ------------------------------ Menu ----------------------------- //
  function renderMenu() {
    const items = ["Projeto", "Editar", "Inserir", "Visualizar", "Publicar", "Ajuda"];
    $("menu").innerHTML = items.map((m) => `<button data-menu="${m}">${m}</button>`).join("");
    $("menu").querySelectorAll("[data-menu]").forEach((b) => b.addEventListener("click", () => toast({ kind: "info", title: b.dataset.menu, msg: "Menu de exemplo do prototipo." })));
  }

  // ----------------------------- Sidebar --------------------------- //
  function sideHead(title, actions) {
    return `<div class="side-head"><span>${title}</span><span class="acts">${(actions || []).map((a) => `<button data-side-act="${a.act}" title="${a.title}">${ICONS[a.icon]}</button>`).join("")}</span></div>`;
  }

  function renderSidebar() {
    const sb = $("sidebar");
    if (state.activeSection === "screens") {
      sb.innerHTML = sideHead("Telas", [{ act: "add-screen", icon: "plus", title: "Nova tela" }, { act: "reload", icon: "refresh", title: "Recarregar" }]) +
        `<div class="tree"><div class="tree-group"><div class="tree-label" data-toggle><span class="chev">${ICONS.chevron}</span><span>Dispositivos</span></div><div class="tree-children">` +
        state.screens.map((s) => `<div class="tree-item ${s.id === state.activeScreenId ? "active" : ""}" data-screen="${s.id}"><span class="dot ${s.online ? "on" : "off"}"></span><span class="name">${esc(s.name)}</span><span class="tag">${s.zones.length}z</span></div>`).join("") +
        `</div></div></div>`;
    } else if (state.activeSection === "media") {
      sb.innerHTML = sideHead("Midias", [{ act: "add-media", icon: "plus", title: "Adicionar midia" }]) +
        `<div class="tree">` + state.media.map((m) => `<div class="tree-item" data-media="${m.id}">${ICONS[TYPE_ICON[m.type]]}<span class="name">${esc(m.name)}</span><span class="tag">${TYPE_LABEL[m.type]}</span></div>`).join("") + `</div>`;
    } else if (state.activeSection === "playlists") {
      sb.innerHTML = sideHead("Playlists", [{ act: "add-playlist", icon: "plus", title: "Nova playlist" }]) +
        `<div class="tree">` + state.playlists.map((p) => `<div class="tree-group"><div class="tree-label" data-toggle><span class="chev">${ICONS.chevron}</span>${ICONS.playlist}<span style="flex:1">${esc(p.name)}</span><span class="tag">${p.items.length}</span></div><div class="tree-children">` +
        p.items.map((it) => { const md = mediaById(it.mediaId); return `<div class="tree-item" data-toast="Item: ${esc(md ? md.name : "?")}">${ICONS[TYPE_ICON[md ? md.type : "text"]]}<span class="name">${esc(md ? md.name : "?")}</span><span class="tag">${it.duration}s</span></div>`; }).join("") +
        `</div></div>`).join("") + `</div>`;
    } else if (state.activeSection === "schedules") {
      const rows = [];
      state.screens.forEach((s) => s.zones.forEach((z) => z.schedules.forEach((sc) => {
        const pl = playlistById(sc.playlistId);
        rows.push(`<div class="tree-item" data-toast="Agendamento de ${esc(s.name)} / ${esc(z.name)}">${ICONS.clock}<span class="name">${esc(pl ? pl.name : "?")} ${sc.start}-${sc.end}</span><span class="tag">P${sc.priority}</span></div>`);
      })));
      sb.innerHTML = sideHead("Agendamentos") + `<div class="tree">${rows.join("") || '<div class="empty">Nenhum agendamento.</div>'}</div>`;
    } else if (state.activeSection === "search") {
      sb.innerHTML = sideHead("Buscar") + `<div style="padding:10px 12px"><div class="field"><input id="side-search" placeholder="Buscar em todo o projeto..."/></div><div class="empty">Digite para filtrar telas, midias e playlists.</div></div>`;
    } else {
      sb.innerHTML = sideHead("Configuracoes") + `<div class="tree">` +
        `<div class="tree-item" data-act="theme">${ICONS.sun}<span class="name">Alternar tema</span></div>` +
        `<div class="tree-item" data-toast="PWA ativo: instalavel e offline">${ICONS.check}<span class="name">PWA habilitado</span></div>` +
        `<div class="tree-item" data-toast="Revisao ${state.revision}">${ICONS.branch}<span class="name">Revisao do projeto</span></div>` +
        `</div>`;
    }
    bindSidebar();
  }

  function bindSidebar() {
    const sb = $("sidebar");
    sb.querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", () => b.closest(".tree-group").classList.toggle("collapsed")));
    sb.querySelectorAll("[data-screen]").forEach((b) => b.addEventListener("click", () => { state.activeScreenId = +b.dataset.screen; const sc = screen(); state.selectedZoneId = sc.zones[0] ? sc.zones[0].id : null; renderAll(); }));
    sb.querySelectorAll("[data-media]").forEach((b) => b.addEventListener("click", () => { const m = mediaById(+b.dataset.media); toast({ kind: "info", title: m.name, msg: `Tipo: ${TYPE_LABEL[m.type]}` }); }));
    sb.querySelectorAll("[data-toast]").forEach((b) => b.addEventListener("click", () => toast({ kind: "info", msg: b.dataset.toast })));
    sb.querySelectorAll('[data-act="theme"]').forEach((b) => b.addEventListener("click", toggleTheme));
    sb.querySelectorAll("[data-side-act]").forEach((b) => b.addEventListener("click", () => handleSideAct(b.dataset.sideAct)));
  }

  function handleSideAct(act) {
    if (act === "add-screen") { const id = nid(); state.screens.push({ id, name: "Nova TV", slug: `tv-${id}`, online: false, timezone: "America/Sao_Paulo", zones: [{ id: nid(), name: "Principal", x: 0, y: 0, w: 100, h: 100, z: 1, playlistId: state.playlists[0].id, schedules: [] }] }); state.activeScreenId = id; state.selectedZoneId = screen().zones[0].id; renderAll(); toast({ kind: "ok", msg: "Tela criada." }); }
    else if (act === "add-playlist") { const id = nid(); state.playlists.push({ id, name: "Nova playlist", items: [] }); renderSidebar(); toast({ kind: "ok", msg: "Playlist criada." }); }
    else if (act === "add-media") { const id = nid(); state.media.push({ id, name: `midia-${id}.png`, type: "image" }); renderSidebar(); toast({ kind: "ok", msg: "Midia adicionada." }); }
    else if (act === "reload") { renderAll(); toast({ kind: "info", msg: "Projeto recarregado." }); }
  }

  // ------------------------------- Tabs ---------------------------- //
  function renderTabs() {
    const sc = screen();
    $("tabsbar").innerHTML = state.screens.map((s) => `<div class="tab ${s.id === state.activeScreenId ? "active" : ""}" data-tab="${s.id}">${ICONS.screen}<span>${esc(s.name)}</span><span class="close" data-close="${s.id}">${ICONS.close}</span></div>`).join("");
    $("tabsbar").querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) return; state.activeScreenId = +b.dataset.tab; const s = screen(); state.selectedZoneId = s.zones[0] ? s.zones[0].id : null; renderAll(); }));
    $("tabsbar").querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); toast({ kind: "info", msg: "Prototipo: a aba permanece aberta." }); }));
    void sc;
  }

  // ------------------------------ Canvas --------------------------- //
  function renderStage() {
    const sc = screen();
    const stage = $("stage");
    if (!sc) { stage.innerHTML = ""; return; }
    stage.innerHTML = sc.zones.slice().sort((a, b) => a.z - b.z).map((z) => {
      const pl = playlistById(z.playlistId);
      return `<div class="zone ${z.id === state.selectedZoneId ? "selected" : ""}" data-zone="${z.id}" style="left:${z.x}%;top:${z.y}%;width:${z.w}%;height:${z.h}%">` +
        `<div class="zone-label">${ICONS.layout}<span>${esc(z.name)}</span></div>` +
        `<div class="zone-body">${pl ? esc(pl.name) + " - " + pl.items.length + " itens" : "Sem playlist"}</div>` +
        `<div class="resize" data-resize="${z.id}"></div></div>`;
    }).join("");
    $("stage-hint").textContent = `${sc.name} - ${sc.zones.length} zona(s) - clique e arraste para mover/redimensionar`;
    bindZoneInteractions();
  }

  function bindZoneInteractions() {
    const stage = $("stage");
    stage.querySelectorAll("[data-zone]").forEach((el) => {
      const z = screen().zones.find((zz) => zz.id === +el.dataset.zone);
      el.addEventListener("pointerdown", (e) => {
        if (e.target.closest("[data-resize]")) return;
        state.selectedZoneId = z.id; renderInspector(); renderStage();
        startDrag(e, z, "move");
      });
    });
    stage.querySelectorAll("[data-resize]").forEach((el) => {
      const z = screen().zones.find((zz) => zz.id === +el.dataset.resize);
      el.addEventListener("pointerdown", (e) => { e.stopPropagation(); state.selectedZoneId = z.id; startDrag(e, z, "resize"); });
    });
  }

  function startDrag(e, z, mode) {
    e.preventDefault();
    const rect = $("stage").getBoundingClientRect();
    const sx = e.clientX, sy = e.clientY;
    const o = { x: z.x, y: z.y, w: z.w, h: z.h };
    const move = (ev) => {
      const dx = ((ev.clientX - sx) / rect.width) * 100;
      const dy = ((ev.clientY - sy) / rect.height) * 100;
      if (mode === "move") { z.x = clamp(Math.round(o.x + dx), 0, 100 - z.w); z.y = clamp(Math.round(o.y + dy), 0, 100 - z.h); }
      else { z.w = clamp(Math.round(o.w + dx), 5, 100 - z.x); z.h = clamp(Math.round(o.h + dy), 5, 100 - z.y); }
      updateStageGeometry(z); updateInspectorGeometry(z);
    };
    const up = () => { document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); markDirty(); };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  function updateStageGeometry(z) {
    const el = $("stage").querySelector(`[data-zone="${z.id}"]`);
    if (el) { el.style.left = z.x + "%"; el.style.top = z.y + "%"; el.style.width = z.w + "%"; el.style.height = z.h + "%"; }
  }
  function updateInspectorGeometry(z) {
    ["x", "y", "w", "h"].forEach((k) => { const i = $("f-" + k); if (i) i.value = z[k]; const v = $("v-" + k); if (v) v.textContent = z[k] + "%"; });
  }

  // ---------------------------- Inspector -------------------------- //
  function renderInspector() {
    const insp = $("inspector");
    const z = zone();
    const sc = screen();
    if (!z) {
      insp.innerHTML = `<div class="insp-head">${ICONS.screen}<span>Propriedades da tela</span></div>` +
        (sc ? screenProps(sc) : `<div class="empty">Selecione uma tela.</div>`);
      bindInspector(); return;
    }
    insp.innerHTML = `<div class="insp-head">${ICONS.layout}<span>Zona: ${esc(z.name)}</span></div>` +
      `<div class="insp-section"><h5>Identificacao</h5>` +
      field("Nome", `<input id="f-name" value="${esc(z.name)}"/>`) +
      field("Camada (z-index)", `<input id="f-z" type="number" value="${z.z}"/>`) + `</div>` +
      `<div class="insp-section"><h5>Geometria (% da tela)</h5>` +
      `<div class="grid2">` + rangeField("x", "X", z.x) + rangeField("y", "Y", z.y) + rangeField("w", "Largura", z.w) + rangeField("h", "Altura", z.h) + `</div></div>` +
      `<div class="insp-section"><h5>Conteudo</h5>` +
      field("Playlist padrao", `<select id="f-playlist">${state.playlists.map((p) => `<option value="${p.id}" ${p.id === z.playlistId ? "selected" : ""}>${esc(p.name)}</option>`).join("")}</select>`) +
      `<button class="btn ghost block small" data-open-playlist>${ICONS.playlist} Abrir editor da playlist</button></div>` +
      `<div class="insp-section"><h5>Agendamentos</h5>${z.schedules.map(schedCard).join("") || '<div class="empty">Sem agendamentos. A playlist padrao toca sempre.</div>'}` +
      `<button class="btn ghost block small" data-add-sched>${ICONS.plus} Adicionar agendamento</button></div>` +
      `<div class="insp-section"><button class="btn block" data-dup-zone>${ICONS.copy} Duplicar zona</button>` +
      `<button class="btn ghost block small" style="margin-top:8px;color:var(--red)" data-del-zone>${ICONS.trash} Excluir zona</button></div>`;
    bindInspector();
  }

  function screenProps(sc) {
    return `<div class="insp-section"><h5>Tela</h5>` +
      field("Nome", `<input id="f-sname" value="${esc(sc.name)}"/>`) +
      field("Slug (link publico)", `<input id="f-slug" value="${esc(sc.slug)}"/>`) +
      field("Fuso horario", `<input id="f-tz" value="${esc(sc.timezone)}"/>`) +
      `<div class="switch"><span>Online</span><span class="sw ${sc.online ? "on" : ""}" data-toggle-online></span></div>` +
      `<div class="field"><label>Link do player</label><div class="code" style="font-family:var(--mono);font-size:11px;color:var(--muted);background:var(--panel-2);border:1px solid var(--border);padding:7px 9px;border-radius:7px;overflow:auto">/player/?screen=${esc(sc.slug)}</div></div>` +
      `<button class="btn ghost block small" data-copy-link>${ICONS.copy} Copiar link</button></div>` +
      `<div class="insp-section"><button class="btn block" data-add-zone>${ICONS.plus} Adicionar zona</button></div>`;
  }

  function field(label, inner) { return `<div class="field"><label>${label}</label>${inner}</div>`; }
  function rangeField(key, label, val) {
    return `<div class="field"><label>${label}</label><div class="range-row"><input id="f-${key}" type="range" min="0" max="100" value="${val}" data-geo="${key}"/><span class="val" id="v-${key}">${val}%</span></div></div>`;
  }
  function schedCard(sc) {
    const pl = playlistById(sc.playlistId);
    return `<div class="sched"><div class="row"><strong>${esc(pl ? pl.name : "?")}</strong><span class="tag" style="font-family:var(--mono);font-size:10px;color:var(--muted)">${sc.start} - ${sc.end} - P${sc.priority}</span></div>` +
      `<div class="days">${DAYS.map((d, i) => `<span class="day ${sc.days.includes(i) ? "on" : ""}">${d}</span>`).join("")}</div></div>`;
  }

  function bindInspector() {
    const z = zone();
    const insp = $("inspector");
    if (z) {
      const nameI = $("f-name"); if (nameI) nameI.addEventListener("input", () => { z.name = nameI.value; renderStage(); renderTabs(); });
      const zI = $("f-z"); if (zI) zI.addEventListener("input", () => { z.z = +zI.value || 1; renderStage(); });
      insp.querySelectorAll("[data-geo]").forEach((r) => r.addEventListener("input", () => { const k = r.dataset.geo; z[k] = clamp(+r.value, 0, 100); const v = $("v-" + k); if (v) v.textContent = z[k] + "%"; updateStageGeometry(z); markDirtyQuiet(); }));
      const pl = $("f-playlist"); if (pl) pl.addEventListener("change", () => { z.playlistId = +pl.value; renderStage(); markDirty(); });
      const op = insp.querySelector("[data-open-playlist]"); if (op) op.addEventListener("click", () => { state.activeSection = "playlists"; renderActivity(); renderSidebar(); toast({ kind: "info", msg: "Editor da playlist aberto na barra lateral." }); });
      const as = insp.querySelector("[data-add-sched]"); if (as) as.addEventListener("click", () => { z.schedules.push({ id: nid(), playlistId: z.playlistId, days: [0,1,2,3,4], start: "09:00", end: "17:00", priority: 10 }); renderInspector(); toast({ kind: "ok", msg: "Agendamento adicionado." }); });
      const dz = insp.querySelector("[data-dup-zone]"); if (dz) dz.addEventListener("click", () => { const c = JSON.parse(JSON.stringify(z)); c.id = nid(); c.name = z.name + " (copia)"; c.x = clamp(z.x + 5, 0, 90); c.y = clamp(z.y + 5, 0, 90); screen().zones.push(c); state.selectedZoneId = c.id; renderAll(); toast({ kind: "ok", msg: "Zona duplicada." }); });
      const del = insp.querySelector("[data-del-zone]"); if (del) del.addEventListener("click", () => { const sc = screen(); sc.zones = sc.zones.filter((zz) => zz.id !== z.id); state.selectedZoneId = sc.zones[0] ? sc.zones[0].id : null; renderAll(); toast({ kind: "warn", msg: "Zona excluida." }); });
    } else {
      const sn = $("f-sname"); if (sn) sn.addEventListener("input", () => { screen().name = sn.value; renderTabs(); renderSidebar(); });
      const sl = $("f-slug"); if (sl) sl.addEventListener("input", () => { screen().slug = sl.value; });
      const tz = $("f-tz"); if (tz) tz.addEventListener("input", () => { screen().timezone = tz.value; });
      const on = insp.querySelector("[data-toggle-online]"); if (on) on.addEventListener("click", () => { screen().online = !screen().online; renderAll(); });
      const cl = insp.querySelector("[data-copy-link]"); if (cl) cl.addEventListener("click", () => toast({ kind: "ok", msg: "Link copiado (prototipo)." }));
      const az = insp.querySelector("[data-add-zone]"); if (az) az.addEventListener("click", () => { const id = nid(); screen().zones.push({ id, name: "Nova zona", x: 10, y: 10, w: 40, h: 40, z: screen().zones.length + 1, playlistId: state.playlists[0].id, schedules: [] }); state.selectedZoneId = id; renderAll(); toast({ kind: "ok", msg: "Zona adicionada." }); });
    }
  }

  // -------------------------- Painel inferior ---------------------- //
  const BOTTOM = [
    { id: "timeline", label: "Linha do tempo", icon: "timeline" },
    { id: "logs", label: "Saida", icon: "terminal" },
    { id: "problems", label: "Problemas", icon: "alert" },
  ];

  function computeProblems() {
    const probs = [];
    state.screens.forEach((s) => s.zones.forEach((z) => {
      const pl = playlistById(z.playlistId);
      if (!pl || pl.items.length === 0) probs.push({ kind: "warn", desc: `Zona "${z.name}" sem itens de playlist.`, where: `${s.slug}` });
      if (z.x + z.w > 100 || z.y + z.h > 100) probs.push({ kind: "err", desc: `Zona "${z.name}" ultrapassa os limites da tela.`, where: `${s.slug}` });
    }));
    return probs;
  }

  function renderBottom() {
    const probs = computeProblems();
    $("bottom-tabs").innerHTML = BOTTOM.map((b) => `<button class="bt ${b.id === state.bottomTab ? "active" : ""}" data-bt="${b.id}">${ICONS[b.icon]}<span>${b.label}</span>${b.id === "problems" && probs.length ? `<span class="badge">${probs.length}</span>` : ""}</button>`).join("");
    $("bottom-tabs").querySelectorAll("[data-bt]").forEach((b) => b.addEventListener("click", () => { state.bottomTab = b.dataset.bt; renderBottom(); }));
    const c = $("bottom-content");
    if (state.bottomTab === "timeline") c.innerHTML = renderTimeline();
    else if (state.bottomTab === "logs") c.innerHTML = renderLogs();
    else c.innerHTML = renderProblems(probs);
  }

  function renderTimeline() {
    const z = zone();
    const pl = z ? playlistById(z.playlistId) : null;
    if (!pl || !pl.items.length) return `<div class="empty">Selecione uma zona com playlist para ver a linha do tempo.</div>`;
    const total = pl.items.reduce((a, b) => a + b.duration, 0);
    const alts = ["", "alt", "alt2"];
    return `<div class="timeline"><div class="track-head"><span>${esc(pl.name)}</span><span style="font-family:var(--mono)">ciclo total: ${total}s</span></div>` +
      `<div class="track">` + pl.items.map((it, i) => { const md = mediaById(it.mediaId); return `<div class="seg ${alts[i % 3]}" style="flex:${it.duration}" data-toast="${esc(md ? md.name : "?")} - ${it.duration}s - ${it.fit}/${it.transition}"><strong>${esc(md ? md.name : "?")}</strong><small>${it.duration}s - ${it.transition}${it.muted ? " - mudo" : ""}</small></div>`; }).join("") + `</div></div>`;
  }

  function renderLogs() {
    const now = new Date();
    const t = (m) => new Date(now.getTime() - m * 1000).toLocaleTimeString("pt-BR");
    const lines = [
      { lvl: "ok", t: t(2), m: `Player conectado: ${screen() ? screen().slug : "-"}` },
      { lvl: "info", t: t(40), m: "WebSocket /ws/display estabelecido" },
      { lvl: "info", t: t(95), m: `Revisao publicada: ${state.revision}` },
      { lvl: "warn", t: t(160), m: "Autoplay com som bloqueado pelo navegador (use modo quiosque)" },
      { lvl: "ok", t: t(220), m: "Cache offline atualizado (service worker)" },
    ];
    return lines.map((l) => `<div class="logline"><span class="t">${l.t}</span><span class="lvl ${l.lvl}">${l.lvl.toUpperCase()}</span><span>${esc(l.m)}</span></div>`).join("");
  }

  function renderProblems(probs) {
    if (!probs.length) return `<div class="empty">Nenhum problema detectado. Tudo certo para publicar.</div>`;
    return probs.map((p) => `<div class="problem ${p.kind}">${ICONS[p.kind === "err" ? "alert" : "alert"]}<div><div class="desc">${esc(p.desc)}</div><div class="where">${esc(p.where)}</div></div></div>`).join("");
  }

  // ---------------------------- Status bar ------------------------- //
  function renderStatus() {
    const sc = screen();
    const online = state.screens.filter((s) => s.online).length;
    const probs = computeProblems().length;
    $("statusbar").innerHTML =
      `<span class="si"><span class="pulse"></span> Conectado</span>` +
      `<span class="si">${ICONS.branch} ${state.revision}</span>` +
      `<span class="si">${ICONS.screen} ${sc ? esc(sc.slug) : "-"}</span>` +
      `<span class="spacer"></span>` +
      `<span class="si">${ICONS.wifi} ${online}/${state.screens.length} online</span>` +
      `<span class="si">${ICONS.alert} ${probs} problema(s)</span>` +
      `<span class="si btn-like" data-preview>${ICONS.eye} Pre-visualizar</span>` +
      `<span class="si btn-like" data-publish>${ICONS.publish} Publicar</span>`;
    $("statusbar").querySelector("[data-preview]").addEventListener("click", () => toast({ kind: "info", title: "Pre-visualizacao", msg: "Abriria o player em nova aba (prototipo)." }));
    $("statusbar").querySelector("[data-publish]").addEventListener("click", publish);
  }

  function publish() {
    const probs = computeProblems();
    if (probs.some((p) => p.kind === "err")) { state.bottomTab = "problems"; renderBottom(); toast({ kind: "err", title: "Publicacao bloqueada", msg: "Corrija os erros antes de publicar." }); return; }
    state.revision = Math.random().toString(16).slice(2, 10);
    renderStatus();
    toast({ kind: "ok", title: "Publicado", msg: `As telas receberao a revisao ${state.revision} em tempo real.` });
  }

  let dirtyTimer = null;
  function markDirty() { toast({ kind: "info", msg: "Alteracoes pendentes - clique em Publicar.", timeout: 1800 }); }
  function markDirtyQuiet() { clearTimeout(dirtyTimer); dirtyTimer = setTimeout(() => {}, 200); }

  // ------------------------- Paleta de comandos -------------------- //
  const COMMANDS = [
    { icon: "screen", label: "Ir para: Telas", run: () => { state.activeSection = "screens"; renderActivity(); renderSidebar(); } },
    { icon: "media", label: "Ir para: Midias", run: () => { state.activeSection = "media"; renderActivity(); renderSidebar(); } },
    { icon: "playlist", label: "Ir para: Playlists", run: () => { state.activeSection = "playlists"; renderActivity(); renderSidebar(); } },
    { icon: "clock", label: "Ir para: Agendamentos", run: () => { state.activeSection = "schedules"; renderActivity(); renderSidebar(); } },
    { icon: "plus", label: "Nova tela", run: () => handleSideAct("add-screen") },
    { icon: "plus", label: "Nova zona na tela atual", run: () => { const insp = $("inspector"); state.selectedZoneId = null; renderInspector(); const az = insp.querySelector("[data-add-zone]"); if (az) az.click(); } },
    { icon: "plus", label: "Nova playlist", run: () => handleSideAct("add-playlist") },
    { icon: "publish", label: "Publicar alteracoes", run: publish },
    { icon: "eye", label: "Pre-visualizar player", run: () => toast({ kind: "info", msg: "Abriria o player (prototipo)." }) },
    { icon: "sun", label: "Alternar tema claro/escuro", run: toggleTheme },
  ];
  let palIndex = 0, palFiltered = COMMANDS;
  function openPalette() {
    $("palette").hidden = false; const inp = $("palette-input"); inp.value = ""; palFiltered = COMMANDS; palIndex = 0; renderPalette(); inp.focus();
  }
  function closePalette() { $("palette").hidden = true; }
  function renderPalette() {
    $("palette-list").innerHTML = palFiltered.map((c, i) => `<li class="${i === palIndex ? "active" : ""}" data-cmd="${i}"><span class="pi">${ICONS[c.icon]}</span><span>${esc(c.label)}</span></li>`).join("") || `<li><span class="pi">${ICONS.search}</span><span>Nenhum comando</span></li>`;
    $("palette-list").querySelectorAll("[data-cmd]").forEach((li) => li.addEventListener("click", () => runPalette(+li.dataset.cmd)));
  }
  function runPalette(i) { const c = palFiltered[i]; closePalette(); if (c) c.run(); }

  // ------------------------------- Tema ---------------------------- //
  function toggleTheme() {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("adsignage_studio_theme", next);
    toast({ kind: "info", msg: `Tema ${next === "dark" ? "escuro" : "claro"} ativado.`, timeout: 1500 });
  }

  // ---------------------------- Render geral ----------------------- //
  function renderAll() { renderActivity(); renderMenu(); renderSidebar(); renderTabs(); renderStage(); renderInspector(); renderBottom(); renderStatus(); }

  // ------------------------------ Eventos -------------------------- //
  $("cmd-open").addEventListener("click", openPalette);
  $("cmd-open-icon").innerHTML = ICONS.search;
  $("palette").addEventListener("click", (e) => { if (e.target === $("palette")) closePalette(); });
  $("palette-input").addEventListener("input", (e) => { const q = e.target.value.toLowerCase(); palFiltered = COMMANDS.filter((c) => c.label.toLowerCase().includes(q)); palIndex = 0; renderPalette(); });
  $("palette-input").addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); palIndex = Math.min(palIndex + 1, palFiltered.length - 1); renderPalette(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); palIndex = Math.max(palIndex - 1, 0); renderPalette(); }
    else if (e.key === "Enter") { e.preventDefault(); runPalette(palIndex); }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("palette").hidden ? openPalette() : closePalette(); }
    else if (e.key === "Escape") closePalette();
  });

  // ------------------ PWA: instalacao + service worker ------------- //
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => { navigator.serviceWorker.register("sw.js").catch(() => {}); });
  }

  // ---------------------------- Bootstrap -------------------------- //
  document.documentElement.setAttribute("data-theme", localStorage.getItem("adsignage_studio_theme") || "dark");
  renderAll();
  setTimeout(() => toast({ kind: "ok", title: "AdSignage Studio", msg: "Pressione Ctrl+K para a paleta de comandos.", timeout: 4200 }), 500);
})();
