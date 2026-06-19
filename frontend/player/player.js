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
  const overlayRoot = document.getElementById("overlays");
  /** Timers ativos dos overlays temporizados. @type {number[]} */
  let overlayTimers = [];
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
      const unit = html + '<span class="t-sep">\u2022</span>';
      move.innerHTML = unit + unit;
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

  // ---- v34: widgets contagem regressiva, QR e cotacoes ---- //
  function buildCountdownWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-countdown";
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    wrap.innerHTML = title +
      '<div class="cd-grid">' +
      '<div class="cd-cell"><span class="cd-num cd-d">0</span><span class="cd-lbl">dias</span></div>' +
      '<div class="cd-cell"><span class="cd-num cd-h">00</span><span class="cd-lbl">horas</span></div>' +
      '<div class="cd-cell"><span class="cd-num cd-m">00</span><span class="cd-lbl">min</span></div>' +
      '<div class="cd-cell"><span class="cd-num cd-s">00</span><span class="cd-lbl">seg</span></div>' +
      '</div><div class="cd-done"></div>';
    const target = cfg.target ? new Date(cfg.target).getTime() : NaN;
    const dn = wrap.querySelector(".cd-d"), hn = wrap.querySelector(".cd-h");
    const mn = wrap.querySelector(".cd-m"), sn = wrap.querySelector(".cd-s");
    const done = wrap.querySelector(".cd-done"), grid = wrap.querySelector(".cd-grid");
    keepWhileConnected(wrap, () => {
      if (isNaN(target)) { grid.style.display = "none"; done.textContent = "Configure a data-alvo."; return; }
      let diff = Math.floor((target - Date.now()) / 1000);
      if (diff <= 0) { grid.style.display = "none"; done.textContent = cfg.doneText || "Chegou o grande dia!"; return; }
      grid.style.display = ""; done.textContent = "";
      const d = Math.floor(diff / 86400); diff -= d * 86400;
      const h = Math.floor(diff / 3600); diff -= h * 3600;
      const mm = Math.floor(diff / 60); const ss = diff - mm * 60;
      dn.textContent = String(d);
      hn.textContent = String(h).padStart(2, "0");
      mn.textContent = String(mm).padStart(2, "0");
      sn.textContent = String(ss).padStart(2, "0");
    }, 1000);
    return wrap;
  }

  function buildQrWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-qr";
    const data = (cfg.data || cfg.url || "").trim();
    if (!data) { wrap.innerHTML = '<div class="qr-cap">QR sem conteudo</div>'; return wrap; }
    const px = Math.max(120, Number(cfg.size) || 320);
    if (cfg.title) {
      const cap = document.createElement("div");
      cap.className = "qr-cap"; cap.textContent = cfg.title; wrap.appendChild(cap);
    }
    const img = document.createElement("img");
    img.className = "qr-img"; img.alt = "QR code";
    img.src = "https://api.qrserver.com/v1/create-qr-code/?margin=10&size=" + px + "x" + px + "&data=" + encodeURIComponent(data);
    wrap.appendChild(img);
    return wrap;
  }

  function buildRatesWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-rates";
    const pairs = Array.isArray(cfg.pairs) ? cfg.pairs.filter(Boolean) : [];
    const symbols = cfg.symbols || {};
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    wrap.innerHTML = title + '<div class="rt-list">Carregando cotacoes\u2026</div>';
    const list = wrap.querySelector(".rt-list");
    const fmt = (n) => { const v = Number(n); if (!isFinite(v)) return "--"; return v >= 100 ? v.toFixed(2) : v.toFixed(4); };
    const load = async () => {
      if (!pairs.length) { list.textContent = "Configure os pares de moedas."; return; }
      try {
        const res = await fetch("/api/widgets/rates?pairs=" + encodeURIComponent(pairs.join(","))).then((r) => r.json());
        const items = (res && res.items) ? res.items : [];
        if (!items.length) { list.textContent = "Cotacoes indisponiveis."; return; }
        list.innerHTML = items.map((it) => '<div class="rt-row"><span class="rt-pair">' + escapeText(symbols[it.pair] || it.pair) + '</span><span class="rt-val">' + escapeText(fmt(it.rate)) + '</span></div>').join("");
      } catch (e) { list.textContent = "Cotacoes indisponiveis."; }
    };
    keepWhileConnected(wrap, load, 600000);
    return wrap;
  }

  // ---- P5: widgets avancados (PDF/web, relogio mundial, agenda, acoes, menu, dataset) ---- //
  function buildWorldClockWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-worldclock";
    const zones = Array.isArray(cfg.zones) && cfg.zones.length
      ? cfg.zones
      : [{ label: "Local", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }];
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    wrap.innerHTML = title + '<div class="wc-grid"></div>';
    const grid = wrap.querySelector(".wc-grid");
    keepWhileConnected(wrap, () => {
      grid.innerHTML = zones.map((zone) => {
        const tz = zone.timezone || zone.tz || "UTC";
        let time = "--:--";
        try {
          time = new Date().toLocaleTimeString("pt-BR", {
            hour: "2-digit", minute: "2-digit", second: cfg.seconds === false ? undefined : "2-digit",
            timeZone: tz,
          });
        } catch (e) { time = "--:--"; }
        return '<div class="wc-row"><span class="wc-city">' + escapeText(zone.label || tz) +
          '</span><span class="wc-time">' + escapeText(time) + '</span></div>';
      }).join("");
    }, 1000);
    return wrap;
  }

  function buildCalendarWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-calendar";
    const events = Array.isArray(cfg.events) ? cfg.events : [];
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    const sorted = events.slice().sort((a, b) => String(a.date || "").localeCompare(String(b.date || ""))).slice(0, 12);
    wrap.innerHTML = title + '<div class="cal-list">' + (sorted.length ? sorted.map((ev) => {
      const date = ev.date ? new Date(ev.date) : null;
      const when = date && !isNaN(date.getTime())
        ? date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) + (ev.time ? " " + ev.time : "")
        : (ev.when || "");
      return '<div class="cal-row"><span class="cal-date">' + escapeText(when) +
        '</span><span class="cal-title">' + escapeText(ev.title || ev.name || "") +
        '</span></div>';
    }).join("") : '<div class="cal-empty">Sem eventos.</div>') + '</div>';
    return wrap;
  }

  function buildStocksWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-stocks";
    const symbols = Array.isArray(cfg.symbols) ? cfg.symbols.filter(Boolean) : [];
    const fallback = Array.isArray(cfg.fallback) ? cfg.fallback : [];
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    wrap.innerHTML = title + '<div class="st-list">Carregando mercado...</div>';
    const list = wrap.querySelector(".st-list");
    const render = (items) => {
      if (!items.length) { list.textContent = "Cotações indisponíveis."; return; }
      list.innerHTML = items.map((it) => '<div class="st-row"><span class="st-symbol">' +
        escapeText(it.symbol || it.name || "") + '</span><span class="st-price">' +
        escapeText(it.close || it.price || "--") + '</span></div>').join("");
    };
    const load = async () => {
      if (!symbols.length) { render(fallback); return; }
      try {
        const res = await fetch("/api/widgets/stocks?symbols=" + encodeURIComponent(symbols.join(","))).then((r) => r.json());
        const items = (res && res.items) ? res.items : [];
        render(items.length ? items : fallback);
      } catch (e) { render(fallback); }
    };
    keepWhileConnected(wrap, load, 600000);
    return wrap;
  }

  function buildMenuBoardWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-menuboard";
    const groups = Array.isArray(cfg.categories) ? cfg.categories : [];
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    wrap.innerHTML = title + '<div class="mb-grid">' + groups.map((cat) => {
      const items = Array.isArray(cat.items) ? cat.items : [];
      return '<section class="mb-cat"><h3>' + escapeText(cat.name || "Menu") + '</h3>' +
        items.map((it) => '<div class="mb-item"><span><b>' + escapeText(it.name || "") +
        '</b>' + (it.note ? '<small>' + escapeText(it.note) + '</small>' : "") +
        '</span><strong>' + escapeText(it.price || "") + '</strong></div>').join("") +
        '</section>';
    }).join("") + '</div>';
    return wrap;
  }

  function buildDatasetWidget(cfg) {
    const wrap = document.createElement("div");
    wrap.className = "widget widget-dataset";
    const title = cfg.title ? '<div class="w-title">' + escapeText(cfg.title) + '</div>' : "";
    wrap.innerHTML = title + '<div class="ds-table">Carregando dados...</div>';
    const target = wrap.querySelector(".ds-table");
    const fallback = Array.isArray(cfg.rows) ? cfg.rows : [];
    const render = (rows, columns) => {
      rows = Array.isArray(rows) ? rows.slice(0, Number(cfg.limit) || 12) : [];
      columns = Array.isArray(columns) && columns.length
        ? columns
        : Object.keys(rows[0] || {}).map((key) => ({ key: key, label: key }));
      if (!rows.length || !columns.length) { target.textContent = "Sem dados."; return; }
      target.innerHTML = '<table><thead><tr>' + columns.map((c) =>
        '<th>' + escapeText(c.label || c.key) + '</th>').join("") + '</tr></thead><tbody>' +
        rows.map((row) => '<tr>' + columns.map((c) =>
          '<td>' + escapeText(row[c.key] == null ? "" : row[c.key]) + '</td>').join("") + '</tr>').join("") +
        '</tbody></table>';
    };
    const load = async () => {
      if (!cfg.dataset_id) { render(fallback, cfg.columns || []); return; }
      try {
        const res = await fetch("/api/widgets/datasets/" + encodeURIComponent(cfg.dataset_id)).then((r) => r.json());
        render((res && res.rows && res.rows.length) ? res.rows : fallback, (res && res.columns) || cfg.columns || []);
      } catch (e) { render(fallback, cfg.columns || []); }
    };
    keepWhileConnected(wrap, load, Math.max(30000, Number(cfg.refreshMs) || 300000));
    return wrap;
  }

  // ---- v34: video ao vivo HLS (.m3u8), nativo + fallback hls.js ---- //
  let __hlsPromise = null;
  function loadHlsLib() {
    if (window.Hls) return Promise.resolve();
    if (__hlsPromise) return __hlsPromise;
    __hlsPromise = new Promise((resolve, reject) => {
      const tag = document.createElement("script");
      tag.src = "https://cdn.jsdelivr.net/npm/hls.js@1.5.13/dist/hls.min.js";
      tag.onload = () => resolve();
      tag.onerror = () => reject(new Error("hls.js indisponivel"));
      document.head.appendChild(tag);
    });
    return __hlsPromise;
  }
  function attachHls(video, src) {
    if (!src) return;
    if (video.canPlayType("application/vnd.apple.mpegurl")) { video.src = src; return; }
    loadHlsLib().then(() => {
      if (window.Hls && window.Hls.isSupported()) {
        const hls = new window.Hls({ lowLatencyMode: true });
        hls.loadSource(src);
        hls.attachMedia(video);
        video.addEventListener("emptied", () => { try { hls.destroy(); } catch (e) {} }, { once: true });
      } else { video.src = src; }
    }).catch(() => { video.src = src; });
  }

  const FOCAL_POS = { center: "center", top: "top center", bottom: "bottom center", left: "center left", right: "center right" };
  let __ytApiPromise = null;
  function loadYouTubeApi() {
    if (window.YT && window.YT.Player) return Promise.resolve();
    if (__ytApiPromise) return __ytApiPromise;
    __ytApiPromise = new Promise((resolve) => {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (typeof prev === "function") { try { prev(); } catch (e) {} }
        resolve();
      };
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    });
    return __ytApiPromise;
  }
  let __ytSeq = 0;
  function setupYouTubeEnd(iframe, onEnded) {
    if (!iframe.id) iframe.id = "yt-frame-" + (++__ytSeq);
    loadYouTubeApi().then(() => {
      try {
        new window.YT.Player(iframe.id, {
          events: {
            onStateChange: (e) => { if (e.data === window.YT.PlayerState.ENDED) onEnded(); },
          },
        });
      } catch (e) { /* sem deteccao de fim: mantem comportamento atual */ }
    });
  }

  // ---- v30: ajuste de iframe (YouTube/embed) ao tamanho da zona ---- //
  function youtubeEmbedUrl(url, item) {
    if (!url) return url;
    var id = null, m;
    m = url.match(/(?:youtu\.be\/|\/embed\/|\/shorts\/|\/v\/)([A-Za-z0-9_-]{11})/);
    if (m) id = m[1];
    if (!id) { m = url.match(/[?&]v=([A-Za-z0-9_-]{11})/); if (m) id = m[1]; }
    if (!id && /^[A-Za-z0-9_-]{11}$/.test(String(url).trim())) id = String(url).trim();
    if (!id) return url; // nao reconhecido: usa a URL original
    var p = new URLSearchParams();
    p.set("autoplay", "1");
    p.set("mute", item && item.muted === false ? "0" : "1");
    p.set("controls", "0");
    p.set("rel", "0");
    p.set("modestbranding", "1");
    p.set("playsinline", "1");
    p.set("iv_load_policy", "3");
    if (item && item.play_full) { p.set("enablejsapi", "1"); }
    else { p.set("loop", "1"); p.set("playlist", id); }
    return "https://www.youtube.com/embed/" + id + "?" + p.toString();
  }

  function fitIframeToContainer(wrap, iframe, fit) {
    var ratio = 16 / 9;
    var apply = function () {
      var w = wrap.clientWidth || wrap.offsetWidth;
      var h = wrap.clientHeight || wrap.offsetHeight;
      if (!w || !h) return;
      if (fit === "fill") { iframe.style.width = "100%"; iframe.style.height = "100%"; return; }
      var contRatio = w / h, iw, ih;
      var matchWidth = (fit === "cover") ? (contRatio >= ratio) : (contRatio <= ratio);
      if (matchWidth) { iw = w; ih = w / ratio; } else { ih = h; iw = h * ratio; }
      iframe.style.width = Math.ceil(iw) + "px";
      iframe.style.height = Math.ceil(ih) + "px";
    };
    if (window.ResizeObserver) { try { new ResizeObserver(apply).observe(wrap); } catch (e) {} }
    window.addEventListener("resize", apply);
    requestAnimationFrame(apply);
    setTimeout(apply, 60);
    setTimeout(apply, 400);
  }

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
        if (/\.m3u8(\?|$)/i.test(item.url || "")) { attachHls(video, item.url); } else { video.src = item.url; }
        if (item.poster) video.poster = item.poster;
        video.autoplay = true;
        video.muted = item.muted !== false;  // som conforme configuração do item
        video.playsInline = true;
        video.controls = false;
        video.addEventListener("ended", onVideoEnded);
        return video;
      }
      case "audio": {
        const wrap = document.createElement("div");
        wrap.className = "text-slide audio-card";
        const label = document.createElement("div");
        label.className = "audio-label";
        label.textContent = "\u266A " + (item.name || "\u00c1udio");
        const audio = document.createElement("audio");
        audio.src = item.url;
        audio.autoplay = true;
        audio.controls = false;
        audio.muted = item.muted === true;
        if (item.play_full) audio.addEventListener("ended", onVideoEnded);
        wrap.appendChild(label);
        wrap.appendChild(audio);
        return wrap;
      }
      case "youtube":
      case "embed":
      case "url":
      case "pdf":
      case "webpage": {
        const iframe = document.createElement("iframe");
        iframe.src = item.type === "youtube" ? youtubeEmbedUrl(item.url, item) : item.url;
        iframe.setAttribute("frameborder", "0");
        iframe.setAttribute(
          "allow",
          "autoplay; encrypted-media; picture-in-picture; fullscreen"
        );
        iframe.allowFullscreen = true;
        if (item.type === "youtube" && item.play_full) {
          setupYouTubeEnd(iframe, onVideoEnded);
        }
        if (item.type === "youtube") {
          const wrap = document.createElement("div");
          wrap.className = "iframe-fit";
          wrap.appendChild(iframe);
          fitIframeToContainer(wrap, iframe, item.fit || "cover");
          return wrap;
        }
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
      case "countdown":
        return buildCountdownWidget(parseConfig(item));
      case "qrcode":
        return buildQrWidget(parseConfig(item));
      case "rates":
        return buildRatesWidget(parseConfig(item));
      case "worldclock":
        return buildWorldClockWidget(parseConfig(item));
      case "calendar":
        return buildCalendarWidget(parseConfig(item));
      case "stocks":
        return buildStocksWidget(parseConfig(item));
      case "menuboard":
        return buildMenuBoardWidget(parseConfig(item));
      case "dataset":
        return buildDatasetWidget(parseConfig(item));
      case "live": {
        const video = document.createElement("video");
        video.autoplay = true;
        video.muted = item.muted !== false;
        video.playsInline = true;
        video.controls = false;
        if (item.poster) video.poster = item.poster;
        attachHls(video, item.url);
        return video;
      }
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

  /** Pré-carrega a mídia (imagem/vídeo) do próximo item para evitar flicker. */
  const __preloadCache = new Set();
  function preloadMedia(item) {
    if (!item || !item.url) return;
    const key = (item.type || "") + "|" + item.url;
    if (__preloadCache.has(key)) return;
    __preloadCache.add(key);
    try {
      if (item.type === "image") { const im = new Image(); im.decoding = "async"; im.src = item.url; }
      else if (item.type === "video" && !/\.m3u8(\?|$)/i.test(item.url)) { const v = document.createElement("video"); v.preload = "auto"; v.muted = true; v.src = item.url; try { v.load(); } catch (e) {} }
    } catch (e) { /* best-effort */ }
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
        empty.className = "text-slide zone-empty";
        empty.innerHTML = '<div class="ze-ico">\u25A6</div><div class="ze-msg">Sem conteúdo</div><div class="ze-sub">Adicione mídia a esta zona no painel</div>';
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

      // Pré-carrega o próximo item para evitar "piscar" na transição.
      if (items.length > 1) preloadMedia(items[(idx + 1) % items.length]);

      // Vídeos e itens "tocar completo" avançam no fim; demais usam timer.
      const playsToEnd = item.type === "video"
        || (item.play_full && (item.type === "audio" || item.type === "youtube"));
      if (!playsToEnd && items.length > 1) {
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

  /**
   * Aplica o tema de cores da tela como CSS vars no documento.
   * @param {Object|null} theme
   */
  function applyTheme(theme) {
    const root = document.documentElement.style;
    const set = (k, v) => { if (v) root.setProperty(k, v); else root.removeProperty(k); };
    theme = theme || {};
    set("--tv-bg", theme.bg);
    set("--tv-text", theme.text);
    set("--tv-accent", theme.accent);
    set("--tv-ticker-bg", theme.tickerBg);
    set("--tv-ticker-text", theme.tickerText);
    set("--tv-slide-bg", theme.bg ? `radial-gradient(circle at 50% 30%, ${theme.bg}, #000)` : null);
  }

  /** Remove todos os overlays e cancela seus timers. */
  function clearOverlays() {
    overlayTimers.forEach((t) => clearInterval(t));
    overlayTimers = [];
    if (overlayRoot) overlayRoot.innerHTML = "";
  }

  /** Define um tamanho padrao para o overlay conforme a posicao. */
  function applyDefaultOverlaySize(box, position, width, height) {
    const w = width > 0 ? `${width}vw` : null;
    const hh = height > 0 ? `${height}vh` : null;
    if (position === "bottom" || position === "top") {
      box.style.width = w || "100%";
      box.style.height = hh || "14vmin";
    } else if (position === "left" || position === "right") {
      box.style.width = w || "24vmin";
      box.style.height = hh || "60vmin";
    } else {
      box.style.width = w || "28vmin";
      box.style.height = hh || "20vmin";
    }
  }

  /**
   * Renderiza a camada de overlays (HUD) por cima das zonas.
   * @param {Array} list
   */
  function renderOverlays(list) {
    clearOverlays();
    if (!overlayRoot) return;
    (list || []).forEach((ov) => {
      const box = document.createElement("div");
      box.className = "ov ov-pos-" + (ov.position || "bottom") + (ov.mode === "timed" ? " timed" : "");
      applyDefaultOverlaySize(box, ov.position || "bottom", ov.width || 0, ov.height || 0);
      box.style.zIndex = String(ov.z_index || 50);
      const inner = document.createElement("div");
      inner.className = "ov-inner";
      if (ov.opacity != null) inner.style.opacity = String(ov.opacity);
      inner.appendChild(createMediaElement({ type: ov.kind, content: ov.content, name: ov.name || "", fit: "contain" }, () => {}));
      box.appendChild(inner);
      overlayRoot.appendChild(box);
      if (ov.mode === "timed") {
        const showMs = Math.max(1, ov.visible_seconds || 15) * 1000;
        const everyMs = Math.max((ov.interval_seconds || 300), Math.ceil(showMs / 1000) + 1) * 1000;
        const cycle = () => {
          box.classList.add("show");
          setTimeout(() => { if (box.isConnected) box.classList.remove("show"); }, showMs);
        };
        cycle();
        const id = setInterval(() => {
          if (!box.isConnected) { clearInterval(id); return; }
          cycle();
        }, everyMs);
        overlayTimers.push(id);
      }
    });
  }

  /** Envia ao Service Worker as URLs de midia do payload para pre-cache offline. */
  function precachePayload(payload) {
    try {
      if (!("serviceWorker" in navigator) || !navigator.serviceWorker.controller) return;
      const urls = [];
      (payload.zones || []).forEach((z) => (z.items || []).forEach((it) => {
        if (it.url && it.url.indexOf("/media/") !== -1) urls.push(it.url);
        if (it.poster && it.poster.indexOf("/media/") !== -1) urls.push(it.poster);
      }));
      if (payload.background_audio && payload.background_audio.indexOf("/media/") !== -1) urls.push(payload.background_audio);
      if (urls.length) navigator.serviceWorker.controller.postMessage({ type: "precache", urls: urls });
    } catch (e) { /* best-effort */ }
  }

  function render(payload) {
    applyEmergency(payload.emergency_message);
    // Para as zonas anteriores.
    zoneControllers.forEach((z) => z.stop());
    zoneControllers = [];
    stage.innerHTML = "";
    applyTheme(payload.theme);
    renderOverlays(payload.overlays || []);
    precachePayload(payload);

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

  async function reportCommandResult(commandId, body) {
    try {
      await fetch(`/api/display/${encodeURIComponent(screenSlug)}/commands/${commandId}/result`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || { status: "done" }),
      });
    } catch (err) {
      console.warn("Falha ao reportar comando:", err);
    }
  }

  function identifyScreen() {
    const el = document.createElement("div");
    el.style.cssText = "position:fixed;inset:3vmin;z-index:99999;border:1vmin solid #7aa2f7;border-radius:2vmin;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.72);color:#fff;font:700 8vmin system-ui;text-align:center;pointer-events:none";
    el.textContent = "tvMedia - " + screenSlug;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 8000);
  }

  async function captureScreenshotDataUrl() {
    const w = Math.max(320, window.innerWidth || document.documentElement.clientWidth || 1280);
    const h = Math.max(240, window.innerHeight || document.documentElement.clientHeight || 720);
    const clone = document.documentElement.cloneNode(true);
    clone.querySelectorAll("script").forEach((node) => node.remove());
    const html = new XMLSerializer().serializeToString(clone);
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><foreignObject width="100%" height="100%">' + html + '</foreignObject></svg>';
    const img = new Image();
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    try {
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = url;
      });
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      return canvas.toDataURL("image/png");
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function handleCommand(data) {
    const id = data.command_id;
    const command = data.command;
    if (!id || !command) return;
    try {
      if (command === "reload") {
        await refresh(true);
        await reportCommandResult(id, { status: "done", result: "Conteudo recarregado." });
      } else if (command === "identify") {
        identifyScreen();
        await reportCommandResult(id, { status: "done", result: "Identificacao exibida no player." });
      } else if (command === "screenshot") {
        try {
          const dataUrl = await captureScreenshotDataUrl();
          await reportCommandResult(id, { status: "done", result: "Screenshot capturado pelo navegador.", data_url: dataUrl });
        } catch (err) {
          await reportCommandResult(id, { status: "failed", result: "Screenshot indisponivel neste navegador: " + (err && err.message ? err.message : String(err)) });
        }
      } else {
        await reportCommandResult(id, { status: "unsupported", result: "Comando requer hardware/agente externo: " + command });
      }
    } catch (err) {
      await reportCommandResult(id, { status: "failed", result: err && err.message ? err.message : String(err) });
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
      else if (data.type === "command") handleCommand(data);
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
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").then((reg) => { reg.update(); setInterval(() => reg.update(), 60 * 60 * 1000); }).catch(() => {});
      let swReloaded = false;
      navigator.serviceWorker.addEventListener("controllerchange", () => { if (swReloaded) return; swReloaded = true; location.reload(); });
    }
  }

  init();
})();
