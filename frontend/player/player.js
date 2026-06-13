/**
 * tvMedia — Player de TV (v2, multi-zona).
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
  const bgAudio = document.getElementById("bg-audio");
  const soundBtn = document.getElementById("sound-enable");
  /** URL da musica de fundo atualmente carregada. @type {string|null} */
  let currentAudioUrl = null;

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
   * Sincroniza a musica de fundo da tela (nivel de tela inteira). Toca em loop
   * e nao reinicia quando apenas o conteudo das zonas muda.
   * @param {string|null} url URL do audio, ou null para silenciar.
   */
  function updateBackgroundAudio(url) {
    if (url === currentAudioUrl) return;
    currentAudioUrl = url;
    if (!url) {
      bgAudio.pause();
      bgAudio.removeAttribute("src");
      try { bgAudio.load(); } catch (e) { /* noop */ }
      if (soundBtn) soundBtn.hidden = true;
      return;
    }
    bgAudio.src = url;
    const attempt = bgAudio.play();
    if (attempt && typeof attempt.then === "function") {
      attempt
        .then(() => { if (soundBtn) soundBtn.hidden = true; })
        .catch(() => { if (soundBtn) soundBtn.hidden = false; });
    }
  }

  // Conjunto de tags/atributos permitidos ao renderizar HTML de uma mídia.
  // Defesa contra XSS: o conteúdo HTML é cadastrado no painel, mas ainda
  // assim é higienizado antes de ir ao DOM (remove scripts, iframes, handlers
  // de evento e URLs javascript:).
  const ALLOWED_TAGS = new Set([
    "B", "STRONG", "I", "EM", "U", "S", "P", "BR", "SPAN", "DIV",
    "H1", "H2", "H3", "H4", "H5", "H6", "UL", "OL", "LI", "BLOCKQUOTE",
    "HR", "IMG", "A", "SMALL", "SUB", "SUP", "TABLE", "THEAD", "TBODY",
    "TR", "TD", "TH", "FONT", "CENTER",
  ]);
  const ALLOWED_ATTRS = new Set([
    "style", "class", "src", "alt", "href", "title", "width", "height",
    "align", "color",
  ]);

  /**
   * Higieniza uma string HTML mantendo apenas tags/atributos seguros.
   * @param {string} html HTML de origem (conteúdo da mídia).
   * @returns {string} HTML seguro para atribuir via innerHTML.
   */
  function sanitizeHtml(html) {
    const doc = new DOMParser().parseFromString(String(html || ""), "text/html");
    const walk = (node) => {
      for (const child of Array.from(node.childNodes)) {
        if (child.nodeType === 1) {
          if (!ALLOWED_TAGS.has(child.tagName)) {
            child.remove();
            continue;
          }
          for (const attr of Array.from(child.attributes)) {
            const name = attr.name.toLowerCase();
            const value = String(attr.value).trim().toLowerCase();
            const unsafeUrl =
              (name === "href" || name === "src") &&
              value.startsWith("javascript:");
            if (!ALLOWED_ATTRS.has(name) || name.startsWith("on") || unsafeUrl) {
              child.removeAttribute(attr.name);
            }
          }
          walk(child);
        } else if (child.nodeType === 8) {
          child.remove();
        }
      }
    };
    walk(doc.body);
    return doc.body.innerHTML;
  }

  /**
   * Acumula e envia eventos de reprodução (proof-of-play) em lotes.
   *
   * Cada item exibido gera um evento; os eventos são enviados periodicamente
   * e ao sair/ocultar a página (via sendBeacon) para reduzir requisições.
   */
  const playReporter = {
    queue: [],
    register(zone, item) {
      this.queue.push({
        media_id: item.media_id == null ? null : item.media_id,
        zone_id: zone.id == null ? null : zone.id,
        media_name: item.name || "",
        media_type: item.type || "",
        duration_seconds: Math.round(item.duration || 0),
      });
      if (this.queue.length >= 50) this.flush();
    },
    flush(useBeacon = false) {
      if (!this.queue.length || !screenSlug) return;
      const events = this.queue.splice(0, this.queue.length);
      const body = JSON.stringify({ events });
      const url = `/api/display/${encodeURIComponent(screenSlug)}/events`;
      try {
        if (useBeacon && navigator.sendBeacon) {
          navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
        } else {
          fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
            keepalive: true,
          }).catch(() => {});
        }
      } catch (err) {
        // Telemetria é best-effort; nunca deve interromper a reprodução.
      }
    },
  };

  /**
   * Cria o elemento DOM correspondente a um item de mídia.
   * @param {Object} item Item de exibição resolvido pelo backend.
   * @param {() => void} onVideoEnded Callback chamado quando um vídeo termina.
   * @returns {HTMLElement} Elemento pronto para inserção na camada.
   */
  // ---- v18: widgets dinamicos (relogio, clima, tickers) ---- //

  /** Faz o parse seguro da config JSON de um widget (campo content). */
  function parseConfig(item) {
    try { return item && item.content ? JSON.parse(item.content) : {}; }
    catch (e) { return {}; }
  }

  /** Escapa texto para insercao segura como HTML. */
  function escapeText(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  /** Executa fn imediatamente e a cada ms, enquanto o elemento estiver no DOM. */
  function keepWhileConnected(el, fn, ms) {
    const id = setInterval(() => { if (!el.isConnected) { clearInterval(id); return; } fn(); }, ms);
    fn();
    return id;
  }

  const WEATHER_CODES = { 0: "Ceu limpo", 1: "Predom. limpo", 2: "Parc. nublado", 3: "Nublado", 45: "Nevoa", 48: "Nevoa", 51: "Garoa", 53: "Garoa", 55: "Garoa", 61: "Chuva fraca", 63: "Chuva", 65: "Chuva forte", 66: "Chuva gelada", 67: "Chuva gelada", 71: "Neve", 73: "Neve", 75: "Neve forte", 77: "Neve", 80: "Pancadas", 81: "Pancadas", 82: "Pancadas fortes", 85: "Neve", 86: "Neve", 95: "Tempestade", 96: "Tempestade", 99: "Tempestade" };
  function weatherIcon(code) {
    if (code === 0) return "\u2600\uFE0F";
    if (code <= 2) return "\uD83C\uDF24\uFE0F";
    if (code === 3) return "\u2601\uFE0F";
    if (code <= 48) return "\uD83C\uDF2B\uFE0F";
    if (code <= 67) return "\uD83C\uDF27\uFE0F";
    if (code <= 77) return "\u2744\uFE0F";
    if (code <= 86) return "\uD83C\uDF26\uFE0F";
    return "\u26C8\uFE0F";
  }

  function buildClockWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-clock";
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    wrap.innerHTML = title + '<div class="w-time"></div><div class="w-date"></div>';
    const t = wrap.querySelector(".w-time");
    const d = wrap.querySelector(".w-date");
    const use12 = cfg.format === "12h";
    keepWhileConnected(wrap, () => {
      const now = new Date();
      let h = now.getHours();
      const m = String(now.getMinutes()).padStart(2, "0");
      const s = String(now.getSeconds()).padStart(2, "0");
      let suffix = "";
      if (use12) { suffix = h >= 12 ? " PM" : " AM"; h = h % 12 || 12; }
      t.textContent = String(h).padStart(2, "0") + ":" + m + ":" + s + suffix;
      if (cfg.showDate !== false) { d.textContent = now.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" }); }
    }, 1000);
    return wrap;
  }

  function buildWeatherWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-weather";
    const city = cfg.city || "Sao Paulo";
    wrap.innerHTML = '<div class="w-title">' + escapeText(cfg.title || city) + '</div><div class="w-wx"><div class="w-ico">\u2026</div><div class="w-temp">--\u00b0</div></div><div class="w-cond">Carregando\u2026</div>';
    const load = async () => {
      try {
        let lat = cfg.lat, lon = cfg.lon;
        if (lat == null || lon == null) {
          const g = await fetch("https://geocoding-api.open-meteo.com/v1/search?count=1&language=pt&name=" + encodeURIComponent(city)).then((r) => r.json());
          if (g && g.results && g.results[0]) { lat = g.results[0].latitude; lon = g.results[0].longitude; }
        }
        if (lat == null) { wrap.querySelector(".w-cond").textContent = "Cidade nao encontrada"; return; }
        const w = await fetch("https://api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code&timezone=auto&latitude=" + lat + "&longitude=" + lon).then((r) => r.json());
        const cur = w && w.current ? w.current : null;
        if (!cur) return;
        wrap.querySelector(".w-ico").textContent = weatherIcon(cur.weather_code);
        wrap.querySelector(".w-temp").textContent = Math.round(cur.temperature_2m) + "\u00b0";
        wrap.querySelector(".w-cond").textContent = WEATHER_CODES[cur.weather_code] || "";
      } catch (e) { wrap.querySelector(".w-cond").textContent = "Clima indisponivel"; }
    };
    keepWhileConnected(wrap, load, 600000);
    return wrap;
  }

  function buildTickerEl(label, cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-ticker";
    const speed = Math.max(20, Number(cfg.speed) || 60);
    wrap.innerHTML = (label ? '<div class="t-label">' + escapeText(label) + '</div>' : "") + '<div class="t-track"><div class="t-move"></div></div>';
    const move = wrap.querySelector(".t-move");
    const render = (list) => {
      const text = (list || []).filter(Boolean);
      if (!text.length) { move.innerHTML = '<span class="t-item">Sem itens para exibir.</span>'; return; }
      const html = text.map((s) => '<span class="t-item">' + s + '</span>').join('<span class="t-sep">\u2022</span>');
      move.innerHTML = html + '<span class="t-sep">\u2022</span>' + html;
      move.style.animationDuration = speed + "s";
    };
    return { wrap: wrap, render: render };
  }

  function buildNewsTicker(cfg) {
    const manual = Array.isArray(cfg.messages) ? cfg.messages.map(escapeText) : [];
    const built = buildTickerEl(cfg.title || "Noticias", cfg);
    built.render(manual);
    const feeds = Array.isArray(cfg.feeds) ? cfg.feeds.filter(Boolean) : [];
    if (feeds.length) {
      const load = async () => {
        try {
          const res = await fetch("/api/widgets/news?limit=25&feeds=" + encodeURIComponent(feeds.join(","))).then((r) => r.json());
          const heads = (res && res.items ? res.items : []).map((it) => escapeText(it.title) + (it.source ? ' <em>(' + escapeText(it.source) + ')</em>' : ''));
          built.render(manual.concat(heads));
        } catch (e) { /* mantem mensagens manuais */ }
      };
      keepWhileConnected(built.wrap, load, 300000);
    }
    return built.wrap;
  }

  function buildPromoTicker(cfg) {
    const products = Array.isArray(cfg.products) ? cfg.products : [];
    const items = products.map((p) => {
      const name = escapeText(p.name || "");
      const price = (p.price != null && p.price !== "") ? ' <b>' + escapeText(p.price) + '</b>' : '';
      const note = p.note ? ' <em>' + escapeText(p.note) + '</em>' : '';
      return name + price + note;
    });
    const built = buildTickerEl(cfg.title || "Promocoes", cfg);
    built.wrap.classList.add("widget-promo");
    built.render(items);
    return built.wrap;
  }

  const FOCAL_POS = { center: "center", top: "top center", bottom: "bottom center", left: "center left", right: "center right" };
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
        if (item.poster) video.poster = item.poster;
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
      case "clock":
        return buildClockWidget(parseConfig(item));
      case "weather":
        return buildWeatherWidget(parseConfig(item));
      case "news":
        return buildNewsTicker(parseConfig(item));
      case "promo":
        return buildPromoTicker(parseConfig(item));
      case "html": {
        const div = document.createElement("div");
        div.className = "text-slide";
        div.innerHTML = sanitizeHtml(item.content || "");
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
      playReporter.register(this.zone, item);

      // Monta a nova camada.
      const layer = document.createElement("div");
      layer.className = `layer fit-${item.fit || "contain"}`;
      layer.style.setProperty("--focal", FOCAL_POS[item.focal] || "center");
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
      if (item.type !== "video" && items.length > 1) {
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
  function applyEmergency(msg) {
    const el = document.getElementById("emergency");
    if (!el) return;
    if (msg && String(msg).trim()) { el.textContent = String(msg); el.classList.add("show"); }
    else { el.classList.remove("show"); el.textContent = ""; }
  }

  function render(payload) {
    applyEmergency(payload.emergency_message);
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
      updateBackgroundAudio(payload.background_audio || null);
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
  /**
   * Tela de emparelhamento: solicita o codigo de 6 digitos exibido no painel
   * e, ao validar, redireciona para o player da tela correspondente.
   */
  function showPairing() {
    const wrap = document.createElement("div");
    wrap.id = "pairing";
    wrap.style.cssText = "position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle at 50% 30%,#1f2937,#000);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#fff";
    wrap.innerHTML = '<div style="text-align:center;max-width:90vw">' +
      '<div style="font-size:3vmin;color:#93c5fd;letter-spacing:.06em;text-transform:uppercase;margin-bottom:1.5vmin">tvMedia Player</div>' +
      '<div style="font-size:5vmin;font-weight:700;margin-bottom:2vmin">Emparelhar esta TV</div>' +
      '<p style="font-size:2.6vmin;color:#cbd5e1;margin-bottom:3vmin">Digite o codigo de emparelhamento que aparece no painel, na tela desejada.</p>' +
      '<input id="pair-code" inputmode="numeric" autocomplete="off" placeholder="------" maxlength="12" style="font-size:8vmin;letter-spacing:1vmin;text-align:center;width:9em;max-width:90vw;padding:2vmin;border-radius:12px;border:2px solid #334155;background:#0b1220;color:#fff;font-variant-numeric:tabular-nums"/>' +
      '<div><button id="pair-go" style="margin-top:3vmin;padding:2vmin 5vmin;font-size:3.2vmin;font-weight:700;border:0;border-radius:10px;background:#7aa2f7;color:#0b0d16;cursor:pointer">Conectar</button></div>' +
      '<p id="pair-err" style="margin-top:2vmin;font-size:2.4vmin;color:#f87171;min-height:1em"></p>' +
      '</div>';
    document.body.appendChild(wrap);
    const input = wrap.querySelector("#pair-code");
    const errEl = wrap.querySelector("#pair-err");
    const submit = async () => {
      const code = (input.value || "").trim();
      if (code.length < 4) { errEl.textContent = "Informe o codigo completo."; return; }
      errEl.textContent = "Conectando...";
      try {
        const resp = await fetch("/api/display/pair", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: code }) });
        if (!resp.ok) throw new Error("Codigo invalido ou expirado.");
        const data = await resp.json();
        location.href = "/player/?screen=" + encodeURIComponent(data.slug);
      } catch (err) { errEl.textContent = err.message; }
    };
    wrap.querySelector("#pair-go").addEventListener("click", submit);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    input.focus();
  }

  function init() {
    if (!screenSlug) {
      showPairing();
      return;
    }
    if (soundBtn) {
      soundBtn.addEventListener("click", () => {
        bgAudio.play().then(() => { soundBtn.hidden = true; }).catch(() => {});
      });
    }
    refresh(true);
    connectSocket();
    // Revalida a cada 60s (cobre trocas por agendamento sem evento explícito).
    pollTimer = setInterval(() => refresh(false), 60000);
    // Envia a telemetria de reprodução periodicamente e ao sair da página.
    setInterval(() => playReporter.flush(false), 30000);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) playReporter.flush(true);
    });
    window.addEventListener("pagehide", () => playReporter.flush(true));
    if ("serviceWorker" in navigator) { navigator.serviceWorker.register("sw.js").catch(() => {}); }
  }

  init();
})();
