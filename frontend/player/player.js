/**
 * AdSignage — Player de TV (v2, multi-zona).
 *
 * Responsabilidades:
 *  - Ler o slug da tela a partir de `?screen=<slug>` na URL.
 *  - Buscar o payload de exibição em `GET /api/display/{slug}`.
 *  - Renderizar cada zona como uma região absoluta (em %) com seu próprio
 *    slideshow, respeitando duração, modo de ajuste (fit) e transição.
 *  - Manter um WebSocket `/ws/display/{slug}` que recebe `{type:"reload"}` e
 *    revalida o conteúdo; reinicia a reprodução apenas se a `revision` mudou.
 *  - Revalidar periodicamente (rede de segurança para agendamentos) e
 *    reconectar o WebSocket automaticamente.
 */

(() => {
  "use strict";

  /** Slug da tela, extraído da query string. @type {string|null} */
  const screenSlug = new URLSearchParams(location.search).get("screen");

  const stage = document.getElementById("stage");
  const statusDot = document.getElementById("status");
  const messageBox = document.getElementById("message");

  /** Revisão atual em reprodução. @type {string|null} */
  let currentRevision = null;
  /** Controladores de zona ativos (para parar timers ao recarregar). */
  let zoneControllers = [];
  /** Instância atual do WebSocket. @type {WebSocket|null} */
  let socket = null;
  /** Handle do timer de revalidação periódica. */
  let pollTimer = null;

  /**
   * Exibe uma mensagem em tela cheia (ex.: erros ou estado vazio).
   * @param {string|null} text Texto a exibir; `null` esconde a mensagem.
   */
  function showMessage(text) {
    if (!text) {
      messageBox.classList.remove("show");
      messageBox.textContent = "";
      return;
    }
    messageBox.textContent = text;
    messageBox.classList.add("show");
  }

  /**
   * Atualiza o indicador visual de conexão em tempo real.
   * @param {boolean} online Verdadeiro se o WebSocket estiver conectado.
   */
  function setOnline(online) {
    statusDot.classList.toggle("online", online);
  }

  /**
   * Cria o elemento DOM correspondente a um item de mídia.
   * @param {Object} item Item de exibição resolvido pelo backend.
   * @param {() => void} onVideoEnded Callback chamado quando um vídeo termina.
   * @returns {HTMLElement} Elemento pronto para inserção na camada.
   */
  function createMediaElement(item, onVideoEnded) {
    switch (item.type) {
      case "image": {
        const img = document.createElement("img");
        img.src = item.url;
        img.alt = item.name || "";
        return img;
      }
      case "video": {
        const video = document.createElement("video");
        video.src = item.url;
        video.autoplay = true;
        video.muted = item.muted !== false;  // som conforme configuração do item
        video.playsInline = true;
        video.controls = false;
        video.addEventListener("ended", onVideoEnded);
        return video;
      }
      case "youtube":
      case "embed":
      case "url": {
        const iframe = document.createElement("iframe");
        iframe.src = item.url;
        iframe.setAttribute("frameborder", "0");
        iframe.setAttribute(
          "allow",
          "autoplay; encrypted-media; picture-in-picture; fullscreen"
        );
        iframe.allowFullscreen = true;
        return iframe;
      }
      case "html": {
        const div = document.createElement("div");
        div.className = "text-slide";
        div.innerHTML = item.content || "";
        return div;
      }
      case "text":
      default: {
        const div = document.createElement("div");
        div.className = "text-slide";
        div.textContent = item.content || item.name || "";
        return div;
      }
    }
  }

  /**
   * Controla a reprodução de uma única zona (slideshow independente).
   *
   * Usa duas camadas sobrepostas para realizar crossfade/slide entre itens.
   */
  class ZoneController {
    /**
     * @param {Object} zone Zona resolvida (geometria + itens).
     */
    constructor(zone) {
      this.zone = zone;
      this.index = 0;
      this.timer = null;
      this.stopped = false;

      // Cria o container posicionado da zona.
      this.el = document.createElement("div");
      this.el.className = "zone";
      this.el.style.left = `${zone.x}%`;
      this.el.style.top = `${zone.y}%`;
      this.el.style.width = `${zone.width}%`;
      this.el.style.height = `${zone.height}%`;
      this.el.style.zIndex = String(zone.z_index || 0);
    }

    /** Inicia a reprodução do primeiro item da zona. */
    start() {
      if (!this.zone.items || this.zone.items.length === 0) {
        const empty = document.createElement("div");
        empty.className = "text-slide";
        empty.textContent = "Sem conteúdo";
        this.el.appendChild(empty);
        return;
      }
      this.show(0);
    }

    /**
     * Exibe o item de índice informado com a transição configurada.
     * @param {number} idx Índice do item na playlist da zona.
     */
    show(idx) {
      if (this.stopped) return;
      const items = this.zone.items;
      const item = items[idx];
      this.index = idx;

      // Monta a nova camada.
      const layer = document.createElement("div");
      layer.className = `layer fit-${item.fit || "contain"}`;
      if (item.transition === "slide") layer.classList.add("slide");
      else if (item.transition !== "none") layer.classList.add("fade");

      const advance = () => this.next();
      layer.appendChild(createMediaElement(item, advance));
      this.el.appendChild(layer);

      // Força reflow e ativa a transição de entrada.
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          layer.classList.remove("fade", "slide");
          layer.classList.add("visible");
        });
      });

      // Remove camadas antigas após a transição.
      const layers = this.el.querySelectorAll(".layer");
      if (layers.length > 1) {
        for (let i = 0; i < layers.length - 1; i++) {
          const old = layers[i];
          old.classList.remove("visible");
          setTimeout(() => old.remove(), 650);
        }
      }

      // Vídeos avançam no evento `ended`; demais usam timer por duração.
      if (item.type !== "video") {
        const ms = Math.max(1, item.duration || 10) * 1000;
        this.timer = setTimeout(advance, ms);
      }
    }

    /** Avança para o próximo item (em loop). */
    next() {
      if (this.stopped) return;
      if (this.timer) { clearTimeout(this.timer); this.timer = null; }
      const total = this.zone.items.length;
      if (total === 0) return;
      this.show((this.index + 1) % total);
    }

    /** Interrompe a zona e libera recursos. */
    stop() {
      this.stopped = true;
      if (this.timer) { clearTimeout(this.timer); this.timer = null; }
      this.el.remove();
    }
  }

  /**
   * (Re)inicia a reprodução de todas as zonas do payload.
   * @param {Object} payload Payload de exibição retornado pelo backend.
   */
  function render(payload) {
    // Para as zonas anteriores.
    zoneControllers.forEach((z) => z.stop());
    zoneControllers = [];
    stage.innerHTML = "";

    const zones = payload.zones || [];
    const hasContent = zones.some((z) => (z.items || []).length > 0);
    if (!hasContent) {
      showMessage("Nenhuma playlist atribuída a esta tela.");
      return;
    }
    showMessage(null);

    zones.forEach((zone) => {
      const controller = new ZoneController(zone);
      stage.appendChild(controller.el);
      controller.start();
      zoneControllers.push(controller);
    });
  }

  /**
   * Busca o payload de exibição e reinicia a reprodução se a revisão mudou.
   * @param {boolean} [force=false] Força o re-render mesmo sem mudança.
   * @returns {Promise<void>}
   */
  async function refresh(force = false) {
    try {
      const resp = await fetch(`/api/display/${encodeURIComponent(screenSlug)}`);
      if (resp.status === 404) {
        showMessage("Tela não encontrada. Verifique o endereço (slug).");
        return;
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const payload = await resp.json();
      if (force || payload.revision !== currentRevision) {
        currentRevision = payload.revision;
        render(payload);
      }
    } catch (err) {
      console.error("Falha ao buscar conteúdo:", err);
    }
  }

  /** Abre (ou reabre) o WebSocket de tempo real, com reconexão automática. */
  function connectSocket() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/display/${encodeURIComponent(screenSlug)}`;
    socket = new WebSocket(url);

    socket.addEventListener("open", () => {
      setOnline(true);
      // Keep-alive periódico.
      socket._ping = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send("ping");
      }, 25000);
    });

    socket.addEventListener("message", (event) => {
      let data;
      try { data = JSON.parse(event.data); } catch { return; }
      if (data.type === "reload") refresh(false);
    });

    socket.addEventListener("close", () => {
      setOnline(false);
      if (socket && socket._ping) clearInterval(socket._ping);
      // Reconecta após um curto intervalo.
      setTimeout(connectSocket, 3000);
    });

    socket.addEventListener("error", () => socket && socket.close());
  }

  /** Bootstrap do player. */
  function init() {
    if (!screenSlug) {
      showMessage("Informe a tela na URL: /player/?screen=SLUG");
      return;
    }
    refresh(true);
    connectSocket();
    // Revalida a cada 60s (cobre trocas por agendamento sem evento explícito).
    pollTimer = setInterval(() => refresh(false), 60000);
  }

  init();
})();
