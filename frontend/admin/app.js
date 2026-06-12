/**
 * AdSignage — Painel administrativo (v2).
 *
 * Funcionalidades:
 *  - Autenticação por senha (token de sessão armazenado em localStorage).
 *  - Gestão de mídias (upload de imagem/vídeo, criação de texto/HTML/URL).
 *  - Gestão de playlists e itens (com duração, ajuste/fit e transição).
 *  - Gestão de telas, zonas (layout em %) e agendamentos por horário/dia.
 *
 * Todas as chamadas à API passam pelo wrapper `api()`, que injeta o token e
 * trata expiração de sessão (401 -> volta para a tela de login).
 */

(() => {
  "use strict";

  const TOKEN_KEY = "adsignage_token";
  /** @type {string|null} Token de sessão atual. */
  let token = localStorage.getItem(TOKEN_KEY);

  // Elementos principais.
  const loginView = document.getElementById("login");
  const appView = document.getElementById("app");
  const toastEl = document.getElementById("toast");

  // ----------------------------------------------------------------- //
  // Utilidades
  // ----------------------------------------------------------------- //

  /**
   * Exibe uma notificação temporária (toast).
   * @param {string} message Mensagem a exibir.
   * @param {"info"|"success"|"error"} [type="info"] Estilo do toast.
   */
  function toast(message, type = "info") {
    toastEl.textContent = message;
    toastEl.className = `toast show ${type}`;
    setTimeout(() => (toastEl.className = "toast"), 3000);
  }

  /**
   * Wrapper de fetch para a API, injetando o token e tratando erros comuns.
   * @param {string} path Caminho relativo (ex.: "/api/media").
   * @param {RequestInit} [options={}] Opções do fetch.
   * @returns {Promise<any>} Corpo JSON da resposta (ou null em 204).
   */
  async function api(path, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const resp = await fetch(path, { ...options, headers });
    if (resp.status === 401) {
      logout();
      throw new Error("Sessão expirada. Faça login novamente.");
    }
    if (!resp.ok) {
      let detail = `Erro ${resp.status}`;
      try { detail = (await resp.json()).detail || detail; } catch { /* ignore */ }
      throw new Error(detail);
    }
    return resp.status === 204 ? null : resp.json();
  }

  /**
   * Escapa texto para inserção segura como HTML.
   * @param {unknown} value Valor a escapar.
   * @returns {string} Texto escapado.
   */
  function esc(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  // ----------------------------------------------------------------- //
  // Autenticação
  // ----------------------------------------------------------------- //

  /** Mostra a aplicação e carrega os dados iniciais. */
  function showApp() {
    loginView.classList.add("hidden");
    appView.classList.remove("hidden");
    loadMedia();
    loadPlaylists();
    loadScreens();
  }

  /** Encerra a sessão e volta à tela de login. */
  function logout() {
    token = null;
    localStorage.removeItem(TOKEN_KEY);
    appView.classList.add("hidden");
    loginView.classList.remove("hidden");
  }

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const password = document.getElementById("login-password").value;
    const errorEl = document.getElementById("login-error");
    errorEl.textContent = "";
    try {
      const data = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!data.ok) throw new Error("Senha incorreta.");
      const json = await data.json();
      token = json.token;
      localStorage.setItem(TOKEN_KEY, token);
      showApp();
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });

  document.getElementById("logout").addEventListener("click", logout);

  // ----------------------------------------------------------------- //
  // Navegação por abas
  // ----------------------------------------------------------------- //
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
    });
  });

  // ----------------------------------------------------------------- //
  // Mídias
  // ----------------------------------------------------------------- //
  /** @type {Array<Object>} Cache das mídias carregadas. */
  let mediaCache = [];

  /** Carrega e renderiza a lista de mídias. */
  async function loadMedia() {
    try {
      mediaCache = await api("/api/media");
      renderMedia();
    } catch (err) { toast(err.message, "error"); }
  }

  /** Renderiza os cards de mídia. */
  function renderMedia() {
    const list = document.getElementById("media-list");
    if (mediaCache.length === 0) {
      list.innerHTML = `<p class="muted">Nenhuma mídia cadastrada.</p>`;
      return;
    }
    list.innerHTML = mediaCache.map((m) => {
      let preview;
      if (m.type === "image") {
        preview = `<img class="thumb" src="/media/${esc(m.path)}" alt="" />`;
      } else if (m.type === "video") {
        preview = `<video class="thumb" src="/media/${esc(m.path)}" muted></video>`;
      } else {
        preview = `<div class="thumb placeholder">${esc(m.type.toUpperCase())}</div>`;
      }
      return `<div class="card">
        ${preview}
        <h3>${esc(m.name)}</h3>
        <div class="meta">Tipo: ${esc(m.type)}</div>
        <div class="row between">
          <span class="badge">#${m.id}</span>
          <button class="btn danger small" data-del-media="${m.id}">Excluir</button>
        </div>
      </div>`;
    }).join("");

    list.querySelectorAll("[data-del-media]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Excluir esta mídia?")) return;
        try {
          await api(`/api/media/${btn.dataset.delMedia}`, { method: "DELETE" });
          toast("Mídia excluída.", "success");
          loadMedia();
        } catch (err) { toast(err.message, "error"); }
      });
    });
  }

  document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("upload-name").value;
    const file = document.getElementById("upload-file").files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("name", name);
    fd.append("file", file);
    try {
      await api("/api/media/upload", { method: "POST", body: fd });
      toast("Mídia enviada.", "success");
      e.target.reset();
      loadMedia();
    } catch (err) { toast(err.message, "error"); }
  });

  document.getElementById("content-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("content-name").value;
    const type = document.getElementById("content-type").value;
    const value = document.getElementById("content-value").value;
    const body = { name, type };
    if (["url", "youtube", "embed"].includes(type)) body.source_url = value;
    else body.content = value;
    try {
      await api("/api/media", { method: "POST", body: JSON.stringify(body) });
      toast("Mídia criada.", "success");
      e.target.reset();
      loadMedia();
    } catch (err) { toast(err.message, "error"); }
  });

  // ----------------------------------------------------------------- //
  // Playlists
  // ----------------------------------------------------------------- //
  /** @type {Array<Object>} Cache das playlists. */
  let playlistCache = [];
  /** @type {number|null} ID da playlist aberta no detalhe. */
  let openPlaylistId = null;

  /** Carrega e renderiza a lista de playlists. */
  async function loadPlaylists() {
    try {
      playlistCache = await api("/api/playlists");
      renderPlaylists();
      if (openPlaylistId) renderPlaylistDetail(openPlaylistId);
    } catch (err) { toast(err.message, "error"); }
  }

  /** Renderiza a lista lateral de playlists. */
  function renderPlaylists() {
    const list = document.getElementById("playlists-list");
    if (playlistCache.length === 0) {
      list.innerHTML = `<p class="muted">Nenhuma playlist.</p>`;
      return;
    }
    list.innerHTML = playlistCache.map((p) => `
      <div class="list-item ${p.id === openPlaylistId ? "active" : ""}" data-playlist="${p.id}">
        <span>${esc(p.name)}</span>
        <span class="badge">${p.items.length} itens</span>
      </div>`).join("");
    list.querySelectorAll("[data-playlist]").forEach((el) => {
      el.addEventListener("click", () => {
        openPlaylistId = Number(el.dataset.playlist);
        renderPlaylists();
        renderPlaylistDetail(openPlaylistId);
      });
    });
  }

  /**
   * Renderiza o painel de detalhe de uma playlist (itens + controles).
   * @param {number} playlistId ID da playlist a exibir.
   */
  function renderPlaylistDetail(playlistId) {
    const detail = document.getElementById("playlist-detail");
    const playlist = playlistCache.find((p) => p.id === playlistId);
    if (!playlist) { detail.innerHTML = `<p class="muted">Playlist removida.</p>`; return; }

    const fitOptions = ["contain", "cover", "fill"];
    const transOptions = ["fade", "slide", "none"];
    const mediaOptions = mediaCache
      .map((m) => `<option value="${m.id}">${esc(m.name)} (${esc(m.type)})</option>`)
      .join("");

    const itemsHtml = playlist.items.length === 0
      ? `<p class="muted">Sem itens. Adicione abaixo.</p>`
      : playlist.items.map((it) => `
        <div class="item-row">
          <span class="badge">#${it.position + 1}</span>
          <span class="grow">${esc(it.media.name)} <span class="muted">(${esc(it.media.type)})</span></span>
          <label class="field">dur(s)
            <input type="number" min="1" value="${it.duration}" style="width:70px" data-dur="${it.id}" />
          </label>
          <label class="field">ajuste
            <select data-fit="${it.id}">${fitOptions.map((f) => `<option ${f === it.fit ? "selected" : ""}>${f}</option>`).join("")}</select>
          </label>
          <label class="field">transição
            <select data-trans="${it.id}">${transOptions.map((t) => `<option ${t === it.transition ? "selected" : ""}>${t}</option>`).join("")}</select>
          </label>
          <label class="field">som
            <input type="checkbox" data-mute="${it.id}" ${it.muted ? "" : "checked"} />
          </label>
          <button class="btn danger small" data-del-item="${it.id}">x</button>
        </div>`).join("");

    detail.innerHTML = `
      <div class="row between">
        <h3>${esc(playlist.name)}</h3>
        <div class="row">
          <button class="btn ghost small" id="rename-playlist">Renomear</button>
          <button class="btn danger small" id="delete-playlist">Excluir playlist</button>
        </div>
      </div>
      <div>${itemsHtml}</div>
      <div class="subcard">
        <h3>Adicionar item</h3>
        <div class="row">
          <select id="add-media">${mediaOptions}</select>
          <input type="number" id="add-duration" min="1" value="10" placeholder="seg" style="width:80px" />
          <select id="add-fit">${fitOptions.map((f) => `<option>${f}</option>`).join("")}</select>
          <select id="add-trans">${transOptions.map((t) => `<option>${t}</option>`).join("")}</select>
          <label class="field">som <input type="checkbox" id="add-mute" /></label>
          <button class="btn primary small" id="add-item">Adicionar</button>
        </div>
      </div>`;

    // Atualização inline de itens.
    detail.querySelectorAll("[data-dur]").forEach((el) =>
      el.addEventListener("change", () => updateItem(playlistId, el.dataset.dur, { duration: Number(el.value) })));
    detail.querySelectorAll("[data-fit]").forEach((el) =>
      el.addEventListener("change", () => updateItem(playlistId, el.dataset.fit, { fit: el.value })));
    detail.querySelectorAll("[data-trans]").forEach((el) =>
      el.addEventListener("change", () => updateItem(playlistId, el.dataset.trans, { transition: el.value })));
    detail.querySelectorAll("[data-mute]").forEach((el) =>
      el.addEventListener("change", () => updateItem(playlistId, el.dataset.mute, { muted: !el.checked })));
    detail.querySelectorAll("[data-del-item]").forEach((el) =>
      el.addEventListener("click", () => deleteItem(playlistId, el.dataset.delItem)));

    document.getElementById("add-item").addEventListener("click", async () => {
      const media_id = Number(document.getElementById("add-media").value);
      const duration = Number(document.getElementById("add-duration").value);
      const fit = document.getElementById("add-fit").value;
      const transition = document.getElementById("add-trans").value;
      const muted = !document.getElementById("add-mute").checked;
      if (!media_id) { toast("Selecione uma mídia.", "error"); return; }
      try {
        await api(`/api/playlists/${playlistId}/items`, {
          method: "POST",
          body: JSON.stringify({ media_id, duration, fit, transition, muted }),
        });
        toast("Item adicionado.", "success");
        loadPlaylists();
      } catch (err) { toast(err.message, "error"); }
    });

    document.getElementById("rename-playlist").addEventListener("click", async () => {
      const name = prompt("Novo nome:", playlist.name);
      if (!name) return;
      try {
        await api(`/api/playlists/${playlistId}`, { method: "PATCH", body: JSON.stringify({ name }) });
        loadPlaylists();
      } catch (err) { toast(err.message, "error"); }
    });

    document.getElementById("delete-playlist").addEventListener("click", async () => {
      if (!confirm("Excluir esta playlist?")) return;
      try {
        await api(`/api/playlists/${playlistId}`, { method: "DELETE" });
        openPlaylistId = null;
        document.getElementById("playlist-detail").innerHTML = `<p class="muted">Selecione uma playlist.</p>`;
        loadPlaylists();
      } catch (err) { toast(err.message, "error"); }
    });
  }

  /**
   * Atualiza um item de playlist.
   * @param {number} playlistId ID da playlist.
   * @param {string|number} itemId ID do item.
   * @param {Object} patch Campos a atualizar.
   */
  async function updateItem(playlistId, itemId, patch) {
    try {
      await api(`/api/playlists/${playlistId}/items/${itemId}`, {
        method: "PATCH", body: JSON.stringify(patch),
      });
      toast("Item atualizado.", "success");
      loadPlaylists();
    } catch (err) { toast(err.message, "error"); }
  }

  /**
   * Remove um item de playlist.
   * @param {number} playlistId ID da playlist.
   * @param {string|number} itemId ID do item.
   */
  async function deleteItem(playlistId, itemId) {
    try {
      await api(`/api/playlists/${playlistId}/items/${itemId}`, { method: "DELETE" });
      loadPlaylists();
    } catch (err) { toast(err.message, "error"); }
  }

  document.getElementById("playlist-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("playlist-name").value;
    try {
      await api("/api/playlists", { method: "POST", body: JSON.stringify({ name }) });
      toast("Playlist criada.", "success");
      e.target.reset();
      loadPlaylists();
    } catch (err) { toast(err.message, "error"); }
  });

  // ----------------------------------------------------------------- //
  // Telas, zonas e agendamentos
  // ----------------------------------------------------------------- //
  /** @type {Array<Object>} Cache das telas. */
  let screenCache = [];
  const DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

  /** Carrega e renderiza a lista de telas. */
  async function loadScreens() {
    try {
      screenCache = await api("/api/screens");
      renderScreens();
    } catch (err) { toast(err.message, "error"); }
  }

  /**
   * Converte minutos desde a meia-noite em "HH:MM".
   * @param {number} minutes Minutos (0..1440).
   * @returns {string} Hora formatada.
   */
  function minutesToHHMM(minutes) {
    const h = String(Math.floor(minutes / 60)).padStart(2, "0");
    const m = String(minutes % 60).padStart(2, "0");
    return `${h}:${m}`;
  }

  /**
   * Converte "HH:MM" em minutos desde a meia-noite.
   * @param {string} value Hora no formato HH:MM.
   * @returns {number} Minutos.
   */
  function hhmmToMinutes(value) {
    const [h, m] = value.split(":").map(Number);
    return (h || 0) * 60 + (m || 0);
  }

  /** Renderiza os cards de tela (com zonas e agendamentos). */
  function renderScreens() {
    const list = document.getElementById("screens-list");
    if (screenCache.length === 0) {
      list.innerHTML = `<p class="muted">Nenhuma tela cadastrada.</p>`;
      return;
    }
    const now = Date.now();
    const playlistOptions = (selected) =>
      `<option value="">— sem playlist —</option>` +
      playlistCache.map((p) => `<option value="${p.id}" ${p.id === selected ? "selected" : ""}>${esc(p.name)}</option>`).join("");

    list.innerHTML = screenCache.map((s) => {
      const online = s.last_seen && (now - new Date(s.last_seen).getTime() < 60000);
      const playerUrl = `${location.origin}/player/?screen=${s.slug}`;
      const zonesPreview = s.zones.map((z) =>
        `<div class="zone-box" style="left:${z.x}%;top:${z.y}%;width:${z.width}%;height:${z.height}%">${esc(z.name)}</div>`
      ).join("");

      const zonesHtml = s.zones.map((z) => {
        const schedules = z.schedules.map((sc) => `
          <div class="item-row">
            <span class="grow">${esc(playlistCache.find((p) => p.id === sc.playlist_id)?.name || "?")}
              <span class="muted">· ${minutesToHHMM(sc.start_minute)}–${minutesToHHMM(sc.end_minute)}
              · ${sc.days_of_week.split(",").map((d) => DAYS[Number(d)] || d).join(" ")}
              · prio ${sc.priority}</span>
            </span>
            <button class="btn danger small" data-del-sched="${z.id}:${sc.id}">x</button>
          </div>`).join("");

        return `<div class="subcard">
          <div class="row between">
            <strong>${esc(z.name)}</strong>
            <button class="btn danger small" data-del-zone="${s.id}:${z.id}">Remover zona</button>
          </div>
          <div class="grid-4">
            <label class="field">x% <input type="number" value="${z.x}" data-zone-x="${s.id}:${z.id}" /></label>
            <label class="field">y% <input type="number" value="${z.y}" data-zone-y="${s.id}:${z.id}" /></label>
            <label class="field">larg% <input type="number" value="${z.width}" data-zone-w="${s.id}:${z.id}" /></label>
            <label class="field">alt% <input type="number" value="${z.height}" data-zone-h="${s.id}:${z.id}" /></label>
          </div>
          <div class="row" style="margin-top:8px">
            <label class="field grow">Playlist padrão
              <select data-zone-pl="${s.id}:${z.id}">${playlistOptions(z.default_playlist_id)}</select>
            </label>
          </div>
          <div style="margin-top:10px">
            <div class="muted" style="margin-bottom:6px">Agendamentos</div>
            ${schedules || '<p class="muted">Nenhum agendamento (usa a playlist padrão).</p>'}
            <div class="grid-4" style="margin-top:6px">
              <label class="field">Playlist
                <select data-sched-pl="${z.id}">${playlistCache.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select>
              </label>
              <label class="field">Início <input type="time" value="08:00" data-sched-start="${z.id}" /></label>
              <label class="field">Fim <input type="time" value="18:00" data-sched-end="${z.id}" /></label>
              <label class="field">Prioridade <input type="number" value="1" data-sched-prio="${z.id}" /></label>
            </div>
            <div class="row" style="margin-top:6px">
              <span class="muted">Dias:</span>
              ${DAYS.map((d, i) => `<label class="badge"><input type="checkbox" data-sched-day="${z.id}" value="${i}" ${i < 5 ? "checked" : ""}/> ${d}</label>`).join("")}
              <button class="btn primary small" data-add-sched="${z.id}">Agendar</button>
            </div>
          </div>
        </div>`;
      }).join("");

      return `<div class="card" style="grid-column:1/-1">
        <div class="row between">
          <h3>${esc(s.name)}</h3>
          <span class="badge ${online ? "online" : "offline"}">${online ? "online" : "offline"}</span>
        </div>
        <div class="meta">Fuso: ${esc(s.timezone)}</div>
        <div class="row"><span class="muted">URL da TV:</span> <span class="code">${esc(playerUrl)}</span>
          <button class="btn ghost small" data-copy="${esc(playerUrl)}">Copiar</button></div>
        <div class="zone-preview">${zonesPreview}</div>
        ${zonesHtml}
        <div class="subcard">
          <div class="row between">
            <strong>Nova zona</strong>
            <button class="btn primary small" data-add-zone="${s.id}">Adicionar zona</button>
          </div>
        </div>
        <div class="row between">
          <span class="badge">${s.slug}</span>
          <button class="btn danger small" data-del-screen="${s.id}">Excluir tela</button>
        </div>
      </div>`;
    }).join("");

    bindScreenEvents();
  }

  /** Associa os eventos dos cards de tela após render. */
  function bindScreenEvents() {
    const list = document.getElementById("screens-list");

    list.querySelectorAll("[data-copy]").forEach((b) =>
      b.addEventListener("click", () => {
        navigator.clipboard.writeText(b.dataset.copy).then(() => toast("URL copiada.", "success"));
      }));

    list.querySelectorAll("[data-del-screen]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!confirm("Excluir esta tela?")) return;
        try { await api(`/api/screens/${b.dataset.delScreen}`, { method: "DELETE" }); loadScreens(); }
        catch (err) { toast(err.message, "error"); }
      }));

    // Zonas: criar.
    list.querySelectorAll("[data-add-zone]").forEach((b) =>
      b.addEventListener("click", async () => {
        try {
          await api(`/api/screens/${b.dataset.addZone}/zones`, {
            method: "POST",
            body: JSON.stringify({ name: "Nova zona", x: 0, y: 0, width: 50, height: 50, z_index: 1 }),
          });
          toast("Zona criada.", "success");
          loadScreens();
        } catch (err) { toast(err.message, "error"); }
      }));

    // Zonas: remover.
    list.querySelectorAll("[data-del-zone]").forEach((b) =>
      b.addEventListener("click", async () => {
        const [screenId, zoneId] = b.dataset.delZone.split(":");
        if (!confirm("Remover esta zona?")) return;
        try { await api(`/api/screens/${screenId}/zones/${zoneId}`, { method: "DELETE" }); loadScreens(); }
        catch (err) { toast(err.message, "error"); }
      }));

    // Zonas: atualizar geometria/playlist.
    const zoneFieldMap = {
      "zoneX": "x", "zoneY": "y", "zoneW": "width", "zoneH": "height",
    };
    Object.entries(zoneFieldMap).forEach(([dataKey, field]) => {
      list.querySelectorAll(`[data-${dataKey.replace(/([A-Z])/g, "-$1").toLowerCase()}]`).forEach((el) =>
        el.addEventListener("change", () => {
          const [screenId, zoneId] = el.dataset[dataKey].split(":");
          patchZone(screenId, zoneId, { [field]: Number(el.value) });
        }));
    });
    list.querySelectorAll("[data-zone-pl]").forEach((el) =>
      el.addEventListener("change", () => {
        const [screenId, zoneId] = el.dataset.zonePl.split(":");
        patchZone(screenId, zoneId, { default_playlist_id: el.value ? Number(el.value) : null });
      }));

    // Agendamentos: adicionar.
    list.querySelectorAll("[data-add-sched]").forEach((b) =>
      b.addEventListener("click", async () => {
        const zoneId = b.dataset.addSched;
        const playlist_id = Number(list.querySelector(`[data-sched-pl="${zoneId}"]`).value);
        const start_minute = hhmmToMinutes(list.querySelector(`[data-sched-start="${zoneId}"]`).value);
        const end_minute = hhmmToMinutes(list.querySelector(`[data-sched-end="${zoneId}"]`).value);
        const priority = Number(list.querySelector(`[data-sched-prio="${zoneId}"]`).value);
        const days = Array.from(list.querySelectorAll(`[data-sched-day="${zoneId}"]:checked`)).map((c) => c.value);
        if (!playlist_id) { toast("Selecione uma playlist.", "error"); return; }
        if (days.length === 0) { toast("Selecione ao menos um dia.", "error"); return; }
        try {
          await api(`/api/zones/${zoneId}/schedules`, {
            method: "POST",
            body: JSON.stringify({
              playlist_id, start_minute, end_minute, priority,
              days_of_week: days.join(","),
            }),
          });
          toast("Agendamento criado.", "success");
          loadScreens();
        } catch (err) { toast(err.message, "error"); }
      }));

    // Agendamentos: remover.
    list.querySelectorAll("[data-del-sched]").forEach((b) =>
      b.addEventListener("click", async () => {
        const [zoneId, schedId] = b.dataset.delSched.split(":");
        try { await api(`/api/zones/${zoneId}/schedules/${schedId}`, { method: "DELETE" }); loadScreens(); }
        catch (err) { toast(err.message, "error"); }
      }));
  }

  /**
   * Atualiza uma zona via API.
   * @param {string|number} screenId ID da tela.
   * @param {string|number} zoneId ID da zona.
   * @param {Object} patch Campos a atualizar.
   */
  async function patchZone(screenId, zoneId, patch) {
    try {
      await api(`/api/screens/${screenId}/zones/${zoneId}`, {
        method: "PATCH", body: JSON.stringify(patch),
      });
      toast("Zona atualizada.", "success");
      loadScreens();
    } catch (err) { toast(err.message, "error"); }
  }

  document.getElementById("screen-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("screen-name").value;
    const timezone = document.getElementById("screen-tz").value || "America/Sao_Paulo";
    try {
      await api("/api/screens", { method: "POST", body: JSON.stringify({ name, timezone }) });
      toast("Tela criada.", "success");
      e.target.reset();
      document.getElementById("screen-tz").value = "America/Sao_Paulo";
      loadScreens();
    } catch (err) { toast(err.message, "error"); }
  });

  // Atualiza o status online/offline das telas periodicamente.
  setInterval(() => { if (token) loadScreens(); }, 30000);

  // ----------------------------------------------------------------- //
  // Bootstrap
  // ----------------------------------------------------------------- //
  if (token) showApp(); else logout();
})();
