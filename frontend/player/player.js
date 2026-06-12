/**
 * Player do AdSignage (exibido nas TVs).
 *
 * Fluxo geral:
 *   1. Lê o ``slug`` da tela a partir da query string (?screen=...).
 *   2. Busca o conteúdo em /api/display/{slug} e reproduz os itens em loop.
 *   3. Abre um WebSocket em /ws/display/{slug}; ao receber "reload", recarrega
 *      o conteúdo — é isso que torna a edição no painel "instantânea" na TV.
 *   4. Reconecta automaticamente em caso de queda e envia pings periódicos.
 */

/** Slug da tela atual, extraído da URL. */
const params = new URLSearchParams(location.search);
const SLUG = params.get("screen");

const stage = document.getElementById("stage");
const statusEl = document.getElementById("status");

/** Estado de reprodução atual. */
const state = {
  items: [],        // itens da playlist
  index: 0,         // índice do item em exibição
  revision: null,   // hash da revisão atual (evita reiniciar à toa)
  timer: null,      // timeout do próximo avanço
  ws: null,         // conexão WebSocket
};

/**
 * Exibe uma mensagem central (estado vazio / erro) na tela.
 * @param {string} text - Texto a exibir.
 */
function showMessage(text) {
  stage.innerHTML = `<div id="message">${text}</div>`;
}

/** Atualiza o pequeno indicador de status no rodapé. */
function setStatus(text) {
  statusEl.textContent = text;
}

/**
 * Busca o payload de exibição no backend.
 * @returns {Promise<object|null>} Payload de display ou null em caso de erro.
 */
async function fetchDisplay() {
  try {
    const res = await fetch(`/api/display/${SLUG}`);
    if (!res.ok) {
      showMessage(res.status === 404 ? "Tela não encontrada." : "Erro ao carregar.");
      return null;
    }
    return await res.json();
  } catch (err) {
    setStatus("sem conexão");
    return null;
  }
}

/**
 * Renderiza o item atual e agenda o avanço para o próximo.
 *
 * Imagens, textos, HTML e URLs avançam após ``duration`` segundos. Vídeos
 * avançam ao terminar (evento ``ended``), com a duração servindo de limite
 * máximo de segurança.
 */
function renderCurrent() {
  clearTimeout(state.timer);
  if (state.items.length === 0) {
    showMessage("Nenhum conteúdo configurado para esta tela.");
    return;
  }

  const item = state.items[state.index % state.items.length];
  const advance = () => {
    state.index = (state.index + 1) % state.items.length;
    renderCurrent();
  };

  stage.innerHTML = "";
  let element;

  switch (item.type) {
    case "image":
      element = document.createElement("img");
      element.src = item.url;
      state.timer = setTimeout(advance, item.duration * 1000);
      break;

    case "video":
      element = document.createElement("video");
      element.src = item.url;
      element.autoplay = true;
      element.muted = true;
      element.playsInline = true;
      element.addEventListener("ended", advance);
      // Limite de segurança caso o evento 'ended' não dispare.
      state.timer = setTimeout(advance, (item.duration + 1) * 1000);
      break;

    case "url":
      element = document.createElement("iframe");
      element.src = item.url;
      state.timer = setTimeout(advance, item.duration * 1000);
      break;

    case "html":
      element = document.createElement("div");
      element.className = "text-slide";
      element.innerHTML = item.content || "";
      state.timer = setTimeout(advance, item.duration * 1000);
      break;

    case "text":
    default:
      element = document.createElement("div");
      element.className = "text-slide";
      element.textContent = item.content || "";
      state.timer = setTimeout(advance, item.duration * 1000);
      break;
  }

  stage.appendChild(element);
  if (item.type === "video") {
    element.play().catch(() => {}); // alguns navegadores exigem muted (já está)
  }
  setStatus(`${(state.index % state.items.length) + 1}/${state.items.length}`);
}

/**
 * Recarrega o conteúdo a partir do backend. Reinicia a reprodução apenas se
 * a revisão mudou, evitando "piscar" a tela em atualizações irrelevantes.
 */
async function reload() {
  const data = await fetchDisplay();
  if (!data) return;
  const changed = data.revision !== state.revision;
  state.items = data.items;
  state.revision = data.revision;
  if (changed) {
    state.index = 0;
    renderCurrent();
  }
}

/**
 * Abre (ou reabre) o WebSocket de sincronização em tempo real.
 * Implementa reconexão automática e ping periódico para manter a conexão.
 */
function connectSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/display/${SLUG}`);
  state.ws = ws;

  ws.onopen = () => setStatus("online");
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "reload") reload();
    } catch (_) {
      /* ignora mensagens malformadas */
    }
  };
  ws.onclose = () => {
    setStatus("reconectando…");
    setTimeout(connectSocket, 3000); // tenta reconectar
  };
  ws.onerror = () => ws.close();
}

// Ping periódico para manter a conexão viva através de proxies.
setInterval(() => {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send("ping");
  }
}, 25000);

// Revalidação periódica como rede de segurança (caso uma mensagem se perca).
setInterval(reload, 60000);

// --------------------------------------------------------------------------- //
// Inicialização
// --------------------------------------------------------------------------- //
if (!SLUG) {
  showMessage("Informe a tela na URL: /player/?screen=SEU_SLUG");
} else {
  reload();
  connectSocket();
}
