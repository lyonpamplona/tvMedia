# Live Graphics (tvMedia)

> Evolucao do motor de Overlays/Zones/Widgets para graficos de transmissao ao
> vivo: HUDs fixas, lower-thirds, graficos temporizados, takeovers e
> propaganda durante a exibicao. **Nao e uma reescrita** — estende o que existe.

Estado base: v35 / 1.3.0.

## Fases

| Fase | Tema | Status |
|---|---|---|
| **L1** | Overlays temporizados + posicionamento por ancora + animacoes | **Implementado** |
| L2 | GFX/Lower-third como tipo disparavel (gerador de caracteres) | **Implementado** |
| L3 | Cue points sincronizados ao video (`timeupdate`) | **Implementado** |
| L4 | Mesa de transmissao (disparo ao vivo, takeover, limpar) | **Implementado** |
| L5 | Ad-break / rotacao programada + relatorio de exibicao | **Implementado** |

## L1 — o que foi entregue

O modelo `Overlay` ganhou campos novos, **retrocompativeis** (overlays antigos
continuam validos; os campos legados `position`, `interval_seconds` e
`visible_seconds` seguem funcionando como fallback):

| Campo | Tipo | Funcao |
|---|---|---|
| `anchor` | str | Ancora de posicionamento. Vazio => usa `position`. Valores: `top_left`, `top`, `top_right`, `left`, `center`, `right`, `bottom_left`, `bottom`, `bottom_right`, `lower_third`, `fullscreen`. |
| `margin` | float | Margem de area segura (vmin) ate as bordas. Ignorada em `fullscreen`. |
| `enter_anim` / `exit_anim` | str | Animacao: `none` / `fade` / `slide` / `wipe`. |
| `enter_at` | float | Atraso (s) antes da 1a exibicao (modo `timed`). |
| `duration` | float | Tempo visivel por ciclo (s). 0 => usa `visible_seconds`. |
| `repeat_every` | float | Intervalo de reaparicao (s). 0 => usa `interval_seconds`. |

### Por camada

- **`models.py`** — colunas novas em `Overlay` com docstring atualizada.
- **`schemas.py`** — `OverlayBase`/`OverlayUpdate`/`DisplayOverlay` + tipo
  `AnimKind` (`Literal`) e validacao de limites.
- **`crud.py`** — criacao/atualizacao ja cobrem os campos (via `model_dump`).
- **`database.py`** — `_run_sqlite_migrations` adiciona as colunas de forma
  idempotente em bancos antigos.
- **`services.py`** — `build_overlays_payload` emite os campos novos (com
  `getattr`/fallback para bancos nao migrados).
- **`player.js`** — motor de renderizacao: ancora (incl. `lower_third`/
  `fullscreen`), margem via `--ov-margin`, classes de animacao e janela de
  tempo (`enter_at` / `duration` / `repeat_every`).
- **`index.html` (player)** — CSS das ancoras e das animacoes de entrada/saida.
- **`admin/app.js`** — editor de overlay com ancora, animacoes, margem e janela
  de tempo.
- **`sw.js`** — bump de cache (player v11, studio v20).

## L2 — o que foi entregue

Lower-third virou um **tipo de midia disparavel** (`MediaType.lowerthird`), o
Gerador de Caracteres (CG). Pode ser usado como item de playlist/zona **ou**
empurrado ao vivo pela Mesa de transmissao (L4) — mesmo builder nos dois casos.

### Config do widget (`content` JSON)

| Campo | Funcao |
|---|---|
| `title` | Linha principal (nome). |
| `subtitle` | Linha de apoio (cargo, descricao). Opcional. |
| `color` | Cor de destaque (faixa lateral + subtitulo). |
| `align` | `left` (padrao) ou `right` — inverte logo/texto. |
| `logo` | URL de logo opcional exibido ao lado da faixa. |

### Por camada

- **`models.py`** — novo valor `lowerthird` no enum `MediaType`.
- **`player.js`** — `buildLowerThirdWidget(cfg)` (faixa com acento, titulo,
  subtitulo e logo) + `case "lowerthird"` no `createMediaElement`. Reaproveita
  o motor de animacao/ancora do L1 quando exibido como overlay/GFX ao vivo.
- **`index.html` (player)** — CSS de `.widget-lowerthird` (responsivo via
  `cqmin`, alinhamento esquerda/direita, faixa de destaque).
- **`admin/app.js`** — `lowerthird` em `TYPE_ICON`/`TYPE_LABEL`/`WIDGET_TYPES`;
  formulario "Gerador de caracteres (CG)" (titulo, subtitulo, cor, alinhamento,
  logo) em `widgetFormHtml`/`collectWidgetConfig`. A Mesa de transmissao (L4)
  agora empurra um CG estruturado (`kind: "lowerthird"`) em vez de texto puro.
- **`sw.js`** — bump de cache (player v13, studio v22).

### Observacao

A "entrada de baixo / sai" do roadmap e obtida combinando o CG com as animacoes
da L1 (`enter_anim`/`exit_anim` no overlay ou no disparo ao vivo). Como item de
playlist, o tempo em tela e a duracao do proprio item.

## L3 — o que foi entregue

Cue points: graficos disparados pelo **tempo do proprio video**. Cada midia de
video pode ter uma lista de cues; quando o player reproduz o video, ele escuta
o evento `timeupdate` e dispara/limpa o GFX no instante certo — **reaproveitando
a engine de GFX ao vivo do L4** (`showLiveGfx`/`clearLiveGfx`, camada
`#live-layer`). Como os cues sao relativos ao video, tocam igual em qualquer
tela e nao dependem de rede no momento do disparo.

### Modelo `MediaCue`

| Campo | Funcao |
|---|---|
| `at_seconds` | Instante do video em que o cue dispara. |
| `action` | `show_gfx` (mostra), `clear_gfx` (limpa), `show_overlay` (reservado). |
| `kind` | Tipo do widget do GFX (padrao `lowerthird`). |
| `content` | Config JSON do widget (mesmo formato do lower-third). |
| `slot_id` | Slot na camada ao vivo (para substituir/limpar). |
| `anchor` / `enter_anim` / `exit_anim` | Posicionamento e animacao (vocabulario do L1/L4). |
| `duration` | Tempo visivel (0 = ate `clear_gfx` ou fim do item). |
| `enabled` | Liga/desliga o cue sem apaga-lo. |

### Por camada

- **`models.py`** — nova tabela `media_cues` (1 video : N cues), com `cascade`
  na midia. Criada automaticamente pelo `create_all` no startup.
- **`schemas.py`** — `MediaCueBase/Create/Update/Read` + `DisplayCue` anexado a
  cada `DisplayItem` (campo `cues`).
- **`crud.py`** — `list_media_cues`/`get_media_cue`/`create`/`update`/`delete`.
- **`services.py`** — `build_cues_payload` injeta os cues habilitados (ordenados)
  no item de display nas duas funcoes de zona.
- **`routers/media.py`** — CRUD em `/api/media/{id}/cues` (GET/POST) e
  `/api/media/{id}/cues/{cue_id}` (PATCH/DELETE), com escopo por empresa.
- **`player.js`** — `attachVideoCues(video, cues)`: listener de `timeupdate` que
  dispara cada cue uma vez (com reset ao reiniciar o video) e limpa os GFX ao
  terminar/trocar de item.
- **`admin/app.js`** — botao "Cue points" no card de cada video + modal
  `openCuesModal` (adicionar/listar/excluir cues; tempo, acao, titulo,
  subtitulo, cor, posicao e duracao).
- **`sw.js`** — bump de cache (player v14, studio v23).

### Limitacoes / proximos passos do L3

- A UI usa entrada por **segundos** (campo numerico), nao uma timeline visual
  com scrub sobre o video — fica como melhoria futura.
- `show_overlay` (ativar um `Overlay` existente por `target_id`) esta modelado,
  mas o player ainda trata apenas `show_gfx`/`clear_gfx`.
- Em streams `MediaType.live` (HLS continuo) os cues nao sao anexados (sem linha
  do tempo finita); valem para videos sob demanda.

## L5 — o que foi entregue

Propaganda programada em tres frentes, **reaproveitando** o que ja existia
(campanhas P6, cue points L3 e proof-of-play).

### 1. Rotacao ponderada de campanhas (slots de anuncio)

O campo `weight` foi adicionado a `Campaign`. Quando varias campanhas empatam na
mesma `priority`, a selecao deixa de ser uma alternancia simples e passa a uma
**rotacao ponderada**: cada campanha entra na "roda" `weight` vezes e o ciclo de
10 minutos escolhe a posicao. Pesos maiores aparecem proporcionalmente mais, de
forma **deterministica** (igual em todas as telas, sem aleatoriedade). Peso 0
tira a campanha do rodizio quando ha outras com peso.

- `models.py` / `schemas.py` / `crud.py` — coluna e DTOs de `weight` (0–1000).
- `services.py` — `_choose_campaign` com a roda ponderada.
- `admin/app.js` — campo **Peso** no formulario de campanha + coluna `×N` na lista.

### 2. Ad-break por tempo (reusa L3)

Nova acao de cue **`ad_break`**: no instante `at_seconds` do video, o player
exibe um anuncio (a midia referenciada por `target_id`) em **tela cheia** por
`duration` segundos e depois limpa — reusando a engine de cue points (L3) e a
camada de GFX ao vivo (L4).

- `services.py` (`build_cues_payload`) — resolve a midia do anuncio e injeta
  `url`/`poster`/`kind` no `DisplayCue`.
- `schemas.py` (`DisplayCue`) — campos `url`/`poster`.
- `player.js` — `attachVideoCues` trata `ad_break` (tela cheia + auto-clear) e
  `showLiveGfx` passa `url`/`poster` ao elemento de midia.
- `admin/app.js` — acao "Ad-break (anuncio)" no modal de cue points, escolhendo a
  midia de anuncio e a duracao.

### 3. Relatorio de exibicao de anuncios (proof-of-play)

Ao disparar um `ad_break`, o player registra um `PlayEvent` marcado com
`is_ad = true`. Isso alimenta um relatorio dedicado sem misturar com o
proof-of-play geral.

- `models.py` (`PlayEvent.is_ad`) + `schemas.py` (`PlayEventCreate.is_ad`).
- `crud.py` (`proof_of_play(..., only_ads=True)`) e nova rota
  `GET /api/analytics/proof-of-play/ads`.
- `player.js` — `playReporter` envia `is_ad` no lote de eventos.

### Limitacoes / proximos passos do L5

- O **ad-break interrompe visualmente** (cobre o video em tela cheia) mas **nao
  pausa** o video de fundo; para pausar de fato seria preciso controlar o
  `HTMLMediaElement` principal durante o anuncio.
- A rotacao ponderada vale para campanhas empatadas em prioridade; nao ha ainda
  "pacing" por entregas/dia (so `max_plays_per_hour`).
- O relatorio de anuncios reaproveita a UI de proof-of-play; um painel dedicado
  no admin fica como melhoria futura.

## L4 — o que foi entregue

Mesa de transmissao ao vivo, **reusando** o canal de comandos ja existente
(`WebSocket /ws/display/{slug}` + `PlayerCommand` + `send_player_command`). O
operador empurra/limpa graficos **sem recarregar a playlist**.

### Comandos novos (`command_type`)

| Comando | Payload | Efeito no player |
|---|---|---|
| `live_gfx` | `LiveGfxTrigger` (kind, content, name, slot_id, anchor, enter_anim/exit_anim, margin, duration, width, height, opacity, z_index) | Exibe um GFX (lower-third/banner/HUD) na camada ao vivo. `duration=0` mantem ate limpar. |
| `live_clear` | `LiveClear` (slot_id opcional) | Remove um slot especifico ou todos os GFX ao vivo. |
| `takeover` | `LiveTakeover` (title, subtitle, color, enter_anim/exit_anim, duration) | Tomada de tela full-screen (ex.: "ULTIMA HORA"). |
| `takeover_clear` | — | Encerra a tomada de tela. |

### Por camada

- **`schemas.py`** — regex de `PlayerCommandCreate.command_type` estendida para
  `live_gfx|live_clear|takeover|takeover_clear`; schemas `LiveGfxTrigger`,
  `LiveClear` e `LiveTakeover`.
- **`routers/live.py`** (novo) — prefixo `/api/live`, protegido por
  `require_auth` + escopo da tela. Rotas: `POST /{screen_id}/trigger`,
  `POST /{screen_id}/clear`, `POST /{screen_id}/takeover`,
  `POST /{screen_id}/takeover/clear`. Cada rota cria um `PlayerCommand`,
  despacha via WebSocket e marca como enviado quando ha player conectado.
- **`main.py`** — registro do router `live`.
- **`player.js`** — camada fixa `#live-layer` (acima dos overlays, persistente
  entre refreshes) + `showLiveGfx`/`clearLiveGfx`/`showTakeover`/`clearTakeover`
  reusando `normalizeAnchor`/`applyDefaultOverlaySize`/`createMediaElement` do
  L1; novos casos em `handleCommand`.
- **`index.html` (player)** — CSS de `#live-layer` e do cartao `.takeover-card`.
- **`admin/app.js`** — secao "Mesa de transmissao" no inspetor da tela, abrindo
  um modal com lower-third/banner (titulo, subtitulo, posicao, animacao,
  duracao), takeover ("ULTIMA HORA") e botoes de limpar.
- **`sw.js`** — bump de cache (player v12, studio v21).

### Latencia

O disparo e instantaneo quando o player esta com o WebSocket conectado. Se a
tela estiver offline, o comando fica na fila (`PlayerCommand`) e e aplicado na
reconexao. Nao foi necessario SSE — o canal de comandos ja resolvia o L4.

### Limitacao conhecida do L1

A animacao de **saida** atualmente espelha a de entrada (a transicao CSS
reverte). `exit_anim = none` remove o efeito de saida. Animacoes de saida
totalmente independentes entram no L2, junto do builder de lower-third.

## Decisoes (resposta da auditoria)

1. **Disparo instantaneo?** Ja e viavel: existe `WebSocket /ws/display/{slug}`
   com canal de **comandos** (`PlayerCommand` + `send_player_command` +
   `handleCommand` no player). Nao e preciso SSE; o L4 reusa esse canal.
2. **L1 vs L4?** L1 foi feito primeiro por ser a fundacao: o L4 (mesa) e o L2
   (lower-third) dependem do motor de GFX (ancora + animacao + janela) criado
   aqui.
3. **Proxima fase:** sugestao L4 (mesa de transmissao) reusando o canal de
   comandos existente — maior valor operacional com menor custo. A confirmar.
