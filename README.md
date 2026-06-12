# 📺 AdSignage — Sinalização digital autohospedada

Sistema completo para exibir propagandas em TVs de lojas e comércios. Edite o
conteúdo no painel e ele aparece **na hora** nas telas, via WebSocket.

- **Backend:** Python + FastAPI + SQLAlchemy (SQLite por padrão)
- **Frontend:** painel administrativo e player em HTML/CSS/JS puro (sem build)
- **Tempo real:** WebSocket avisa as TVs para recarregar quando algo muda
- **Autohospedado:** Docker + Docker Compose, um único container

### Recursos (v2)

- 🔐 **Login no painel** (senha única + token de sessão assinado)
- 🗂️ **Múltiplas zonas por tela** (ex.: conteúdo principal + faixa de notícias)
- ⏰ **Agendamento** de playlists por dia da semana e faixa de horário
- 🎬 **Transições** (fade/slide/none) e **modo de ajuste** (contain/cover/fill)
- ▶️ **YouTube e música**: vídeos/playlists do YouTube e embeds do Spotify,
  com **controle de som por item** (mudo por padrão)

### Reprodução de vídeo e áudio (autoplay)

- Vídeos enviados (`video`) e do YouTube reproduzem em loop automaticamente.
- Por padrão os itens iniciam **sem som** (`mudo`), pois a maioria dos navegadores
  bloqueia autoplay com áudio. Para tocar música/vídeo **com som** na TV:
  1. Desmarque "mudo" no item (no painel), e
  2. Inicie o navegador da TV em modo quiosque permitindo autoplay, ex.:
     `chromium --kiosk --autoplay-policy=no-user-gesture-required "http://SERVIDOR:8000/player/?screen=SLUG"`
- Para YouTube, cole o link normal (`watch?v=`, `youtu.be/...` ou `playlist?list=...`);
  o sistema converte para o embed correto. Para Spotify, cole o link de
  compartilhamento da faixa/álbum/playlist.

---

## Arquitetura

```
adsignage/
├── backend/
│   ├── app/
│   │   ├── __init__.py            # versão do pacote
│   │   ├── config.py              # configurações via variáveis de ambiente
│   │   ├── database.py            # engine, sessão e init do banco
│   │   ├── models.py              # ORM: Media, Playlist, Item, Screen, Zone, Schedule
│   │   ├── schemas.py             # DTOs Pydantic (entrada/saída)
│   │   ├── crud.py                # acesso a dados + resolução de agendamento
│   │   ├── auth.py                # login por senha + token HMAC
│   │   ├── websocket_manager.py   # registro de conexões WebSocket por tela
│   │   ├── realtime.py            # notificações "reload" para as telas
│   │   ├── main.py                # app FastAPI + arquivos estáticos
│   │   └── routers/
│   │       ├── auth.py            # login
│   │       ├── media.py           # CRUD + upload de mídias
│   │       ├── playlists.py       # CRUD de playlists e itens
│   │       ├── screens.py         # CRUD de telas (TVs)
│   │       ├── zones.py           # CRUD de zonas
│   │       ├── schedules.py       # CRUD de agendamentos
│   │       └── display.py         # payload do player + WebSocket
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── admin/                     # painel de administração
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   └── player/                    # player exibido na TV
│       ├── index.html
│       └── player.js
├── docker-compose.yml
├── .env.example
└── README.md
```

### Modelo de dados

- **Media** — conteúdo exibível: `image`, `video`, `text`, `html`, `url`,
  `youtube` (vídeo ou playlist) ou `embed` (Spotify e outros players).
- **Playlist** — sequência ordenada de itens, reproduzida em loop.
- **PlaylistItem** — liga uma mídia a uma playlist, com `position`, `duration`,
  `fit` (contain/cover/fill) e `transition` (fade/slide/none).
- **Screen** — uma TV, identificada por um `slug` público, com seu `timezone`.
- **Zone** — região retangular (em %) dentro de uma tela, com playlist padrão.
  Uma tela simples tem uma única zona cobrindo 100%.
- **Schedule** — regra que troca a playlist de uma zona por dia/horário.

### Como o "tempo real" funciona

1. O player na TV abre `WS /ws/display/{slug}` e fica conectado.
2. Qualquer alteração no painel chama os helpers em `realtime.py`, que enviam
   `{"type": "reload"}` às telas afetadas.
3. O player recebe a mensagem e busca novamente `GET /api/display/{slug}`.
4. Se a `revision` mudou, ele reinicia a reprodução com o novo conteúdo.

Para agendamentos, o player também revalida sozinho a cada 60s, garantindo a
troca de playlist no horário mesmo sem um evento explícito.

### Como o agendamento é resolvido

A cada requisição de exibição, para cada zona o backend avalia os agendamentos
no fuso da tela: dentre os que casam com o dia da semana e a faixa de horário
atual, vence o de **maior prioridade**. Sem agendamento ativo, usa-se a
**playlist padrão** da zona.

---

## Como rodar

### Opção A — Docker (recomendado, autohospedado)

```bash
cp .env.example .env   # ajuste ADMIN_PASSWORD e SECRET_KEY!
docker compose up --build -d
```

Depois acesse:

- **Painel:** http://SEU_SERVIDOR:8000/admin/  (senha = `ADMIN_PASSWORD`)
- **API docs:** http://SEU_SERVIDOR:8000/docs

### Opção B — Local (desenvolvimento)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Passo a passo de uso

1. Acesse `/admin/` e entre com a senha (`ADMIN_PASSWORD`).
2. Aba **Mídias**: envie imagens/vídeos ou crie blocos de texto/HTML/URL.
3. Aba **Playlists**: crie uma playlist e adicione itens (defina duração, ajuste
   e transição de cada um).
4. Aba **Telas**: crie uma tela, defina a playlist padrão da zona principal e,
   se quiser, adicione **zonas** e **agendamentos**. Copie a **URL do player**.
5. Na TV, abra `http://SEU_SERVIDOR:8000/player/?screen=SLUG` em tela cheia.
6. Volte ao painel e edite — a TV atualiza **instantaneamente**. ✅

> Dica para TVs: use o navegador em modo quiosque (fullscreen). Em vídeo o
> player usa `muted` para permitir autoplay sem interação.

---

## Endpoints principais

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/api/auth/login` | — | Login (retorna token) |
| GET | `/api/health` | — | Healthcheck |
| GET/POST | `/api/media` | ✅ | Listar / criar mídia (texto/html/url) |
| POST | `/api/media/upload` | ✅ | Upload de imagem/vídeo (multipart) |
| PATCH/DELETE | `/api/media/{id}` | ✅ | Atualizar / excluir mídia |
| GET/POST | `/api/playlists` | ✅ | Listar / criar playlists |
| POST | `/api/playlists/{id}/items` | ✅ | Adicionar item (fit/transição) |
| POST | `/api/playlists/{id}/reorder` | ✅ | Reordenar itens |
| GET/POST | `/api/screens` | ✅ | Listar / criar telas |
| POST | `/api/screens/{id}/zones` | ✅ | Criar zona |
| PATCH/DELETE | `/api/screens/{id}/zones/{zid}` | ✅ | Atualizar / remover zona |
| POST | `/api/zones/{zid}/schedules` | ✅ | Criar agendamento |
| DELETE | `/api/zones/{zid}/schedules/{sid}` | ✅ | Remover agendamento |
| GET | `/api/display/{slug}` | — | Conteúdo resolvido para o player |
| WS | `/ws/display/{slug}` | — | Canal de atualização em tempo real |

---

## Segurança

- **Troque** `ADMIN_PASSWORD` e `SECRET_KEY` antes de expor à internet.
- O player e o WebSocket são públicos por design (a TV só conhece o `slug`);
  trate o `slug` como um segredo de baixa sensibilidade.
- Para produção, coloque atrás de um proxy HTTPS (Caddy, Nginx, Cloudflare).

## Próximos passos sugeridos

- **PostgreSQL** em produção (basta trocar `DATABASE_URL`).
- **Arrastar para reordenar** itens da playlist no painel.
- **Pré-visualização** ao vivo das zonas no editor.
- **Múltiplos usuários** e papéis (admin/operador).
