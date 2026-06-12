/**
 * Lógica do painel administrativo do AdSignage.
 *
 * Consome a API REST para gerenciar telas, playlists e mídias. Como o backend
 * notifica os players via WebSocket a cada alteração, qualquer edição feita
 * aqui reflete imediatamente nas TVs conectadas.
 */

/** Caminho base da API (mesma origem do painel). */
const API = "/api";

/**
 * Wrapper sobre fetch que trata JSON e erros de forma centralizada.
 *
 * @param {string} path - Caminho relativo à raiz (ex.: "/media").
 * @param {RequestInit} [options] - Opções do fetch.
 * @returns {Promise<any>} Corpo da resposta já desserializado (ou null em 204).
 * @throws {Error} Quando a resposta tem status de erro.
 */
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : undefined,
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Erro ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

/**
 * Exibe uma notificação temporária (toast) no canto da tela.
 * @param {string} message - Texto da mensagem.
 * @param {boolean} [isError=false] - Se true, aplica estilo de erro.
 */
function toast(message, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => (el.className = "toast"), 2600);
}

/** Escapa texto para inserção segura em HTML. */
function esc(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

// --------------------------------------------------------------------------- //
// Navegação por abas
// --------------------------------------------------------------------------- //
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
  });
});

// --------------------------------------------------------------------------- //
// MÍDIAS
// --------------------------------------------------------------------------- //

/** Carrega e renderiza a lista de mídias. */
async function loadMedia() {
  const media = await api("/media");
  const container = document.getElementById("media-list");
  container.innerHTML = "";
  media.forEach((m) => {
    const card = document.createElement("div");
    card.className = "card";
    let preview = "";
    if (m.type === "image") preview = `<img class="thumb" src="/media/${m.path}" />`;
    else if (m.type === "video") preview = `<video class="thumb" src="/media/${m.path}" muted></video>`;
    else preview = `<div class="thumb" style="display:flex;align-items:center;justify-content:center">${m.type.toUpperCase()}</div>`;
    card.innerHTML = `
      ${preview}
      <div class="title">${esc(m.name)}</div>
      <div class="meta">Tipo: ${m.type}</div>
      <div class="row">
        <span class="badge">#${m.id}</span>
        <button class="small danger" data-del="${m.id}">Excluir</button>
      </div>`;
    card.querySelector("[data-del]").addEventListener("click", async () => {
      if (!confirm(`Excluir "${m.name}"?`)) return;
      await api(`/media/${m.id}`, { method: "DELETE" });
      toast("Mídia excluída");
      loadMedia();
    });
    container.appendChild(card);
  });
}

document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("upload-name").value;
  const file = document.getElementById("upload-file").files[0];
  const fd = new FormData();
  fd.append("name", name);
  fd.append("file", file);
  try {
    await api("/media/upload", { method: "POST", body: fd });
    toast("Arquivo enviado");
    e.target.reset();
    loadMedia();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("content-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const type = document.getElementById("content-type").value;
  const body = document.getElementById("content-body").value;
  const payload = {
    name: document.getElementById("content-name").value,
    type,
    content: type === "url" ? null : body,
    source_url: type === "url" ? body : null,
  };
  try {
    await api("/media", { method: "POST", body: JSON.stringify(payload) });
    toast("Mídia criada");
    e.target.reset();
    loadMedia();
  } catch (err) {
    toast(err.message, true);
  }
});

// --------------------------------------------------------------------------- //
// PLAYLISTS
// --------------------------------------------------------------------------- //
let selectedPlaylistId = null;

/** Carrega a lista de playlists na coluna esquerda. */
async function loadPlaylists() {
  const playlists = await api("/playlists");
  const list = document.getElementById("playlists-list");
  list.innerHTML = "";
  playlists.forEach((p) => {
    const item = document.createElement("div");
    item.className = "item" + (p.id === selectedPlaylistId ? " selected" : "");
    item.innerHTML = `<strong>${esc(p.name)}</strong><div class="meta">${p.items.length} item(ns)</div>`;
    item.addEventListener("click", () => openPlaylist(p.id));
    list.appendChild(item);
  });
  return playlists;
}

/**
 * Abre o editor de uma playlist específica, listando seus itens com controles
 * de duração, ordem e remoção, além do seletor para adicionar novas mídias.
 * @param {number} id - ID da playlist.
 */
async function openPlaylist(id) {
  selectedPlaylistId = id;
  await loadPlaylists();
  const playlist = await api(`/playlists/${id}`);
  const media = await api("/media");
  const editor = document.getElementById("playlist-editor");

  const options = media.map((m) => `<option value="${m.id}">${esc(m.name)} (${m.type})</option>`).join("");
  const itemsHtml = playlist.items
    .sort((a, b) => a.position - b.position)
    .map(
      (it) => `
      <div class="pl-item" data-item="${it.id}">
        <span class="grow">${esc(it.media.name)} <span class="meta">(${it.media.type})</span></span>
        <input type="number" min="1" value="${it.duration}" data-dur="${it.id}" title="Segundos" />
        <button class="small ghost" data-up="${it.id}">↑</button>
        <button class="small ghost" data-down="${it.id}">↓</button>
        <button class="small danger" data-rem="${it.id}">✕</button>
      </div>`
    )
    .join("");

  editor.innerHTML = `
    <h3>${esc(playlist.name)}</h3>
    <div class="inline-form">
      <select id="add-media">${options}</select>
      <input type="number" id="add-dur" min="1" value="10" title="Duração (s)" />
      <button id="add-item-btn">Adicionar item</button>
      <button class="ghost" id="rename-pl">Renomear</button>
      <button class="danger" id="del-pl">Excluir playlist</button>
    </div>
    <div id="pl-items">${itemsHtml || '<p class="muted">Playlist vazia.</p>'}</div>`;

  editor.querySelector("#add-item-btn").addEventListener("click", async () => {
    const mediaId = parseInt(editor.querySelector("#add-media").value, 10);
    const duration = parseInt(editor.querySelector("#add-dur").value, 10);
    await api(`/playlists/${id}/items`, {
      method: "POST",
      body: JSON.stringify({ media_id: mediaId, duration }),
    });
    toast("Item adicionado — telas atualizadas");
    openPlaylist(id);
  });

  editor.querySelector("#rename-pl").addEventListener("click", async () => {
    const name = prompt("Novo nome:", playlist.name);
    if (!name) return;
    await api(`/playlists/${id}`, { method: "PATCH", body: JSON.stringify({ name }) });
    openPlaylist(id);
  });

  editor.querySelector("#del-pl").addEventListener("click", async () => {
    if (!confirm("Excluir esta playlist?")) return;
    await api(`/playlists/${id}`, { method: "DELETE" });
    selectedPlaylistId = null;
    editor.innerHTML = '<p class="muted">Selecione uma playlist para editar.</p>';
    loadPlaylists();
  });

  // Atualiza duração ao alterar o campo numérico.
  editor.querySelectorAll("[data-dur]").forEach((input) => {
    input.addEventListener("change", async () => {
      await api(`/playlists/${id}/items/${input.dataset.dur}`, {
        method: "PATCH",
        body: JSON.stringify({ duration: parseInt(input.value, 10) }),
      });
      toast("Duração atualizada");
    });
  });

  // Remoção de item.
  editor.querySelectorAll("[data-rem]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/playlists/${id}/items/${btn.dataset.rem}`, { method: "DELETE" });
      openPlaylist(id);
    });
  });

  // Reordenação (move um item para cima/baixo).
  const reorder = async (itemId, delta) => {
    const ids = playlist.items.sort((a, b) => a.position - b.position).map((it) => it.id);
    const idx = ids.indexOf(parseInt(itemId, 10));
    const target = idx + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[idx], ids[target]] = [ids[target], ids[idx]];
    await api(`/playlists/${id}/reorder`, { method: "POST", body: JSON.stringify({ item_ids: ids }) });
    openPlaylist(id);
  };
  editor.querySelectorAll("[data-up]").forEach((b) => b.addEventListener("click", () => reorder(b.dataset.up, -1)));
  editor.querySelectorAll("[data-down]").forEach((b) => b.addEventListener("click", () => reorder(b.dataset.down, 1)));
}

document.getElementById("playlist-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("playlist-name").value;
  const pl = await api("/playlists", { method: "POST", body: JSON.stringify({ name }) });
  e.target.reset();
  openPlaylist(pl.id);
});

// --------------------------------------------------------------------------- //
// TELAS
// --------------------------------------------------------------------------- //

/** Carrega telas e popula também o seletor de playlists do formulário. */
async function loadScreens() {
  const [screens, playlists] = await Promise.all([api("/screens"), api("/playlists")]);
  const plById = Object.fromEntries(playlists.map((p) => [p.id, p.name]));

  // Atualiza o <select> de criação de tela.
  const sel = document.getElementById("screen-playlist");
  sel.innerHTML = '<option value="">Sem playlist</option>' +
    playlists.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("");

  const container = document.getElementById("screens-list");
  container.innerHTML = "";
  screens.forEach((s) => {
    const playerUrl = `${location.origin}/player/?screen=${s.slug}`;
    const online = s.last_seen && (Date.now() - new Date(s.last_seen).getTime() < 60000);
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="row">
        <span class="title">${esc(s.name)}</span>
        <span class="badge ${online ? "online" : ""}">${online ? "online" : "offline"}</span>
      </div>
      <label class="meta">Playlist:</label>
      <select data-pl="${s.id}">
        <option value="">Sem playlist</option>
        ${playlists.map((p) => `<option value="${p.id}" ${p.id === s.playlist_id ? "selected" : ""}>${esc(p.name)}</option>`).join("")}
      </select>
      <div class="meta">URL do player:</div>
      <code class="url">${playerUrl}</code>
      <div class="row">
        <a href="${playerUrl}" target="_blank"><button class="small">Abrir TV</button></a>
        <button class="small danger" data-del="${s.id}">Excluir</button>
      </div>`;
    card.querySelector("[data-pl]").addEventListener("change", async (ev) => {
      const value = ev.target.value;
      await api(`/screens/${s.id}`, {
        method: "PATCH",
        body: JSON.stringify({ playlist_id: value ? parseInt(value, 10) : null }),
      });
      toast("Tela atualizada — TV trocou de conteúdo");
    });
    card.querySelector("[data-del]").addEventListener("click", async () => {
      if (!confirm(`Excluir a tela "${s.name}"?`)) return;
      await api(`/screens/${s.id}`, { method: "DELETE" });
      loadScreens();
    });
    container.appendChild(card);
  });
}

document.getElementById("screen-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("screen-name").value;
  const pl = document.getElementById("screen-playlist").value;
  await api("/screens", {
    method: "POST",
    body: JSON.stringify({ name, playlist_id: pl ? parseInt(pl, 10) : null }),
  });
  e.target.reset();
  toast("Tela criada");
  loadScreens();
});

// --------------------------------------------------------------------------- //
// Inicialização + atualização periódica do status das telas
// --------------------------------------------------------------------------- //
loadScreens();
loadPlaylists();
loadMedia();
setInterval(loadScreens, 30000); // atualiza o indicador online/offline
