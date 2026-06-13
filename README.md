# 📺 tvMedia — Sinalização digital autohospedada

Sistema completo para exibir propagandas em TVs de lojas e comércios. Edite o
conteúdo no painel e ele aparece **na hora** nas telas, via WebSocket.

- **Backend:** Python + FastAPI + SQLAlchemy (SQLite por padrão)
- **Frontend:** painel administrativo e player em HTML/CSS/JS puro (sem build)
- **Tempo real:** WebSocket avisa as TVs para recarregar quando algo muda
- **Autohospedado:** Docker + Docker Compose, um único container

---

## Arquitetura

```
tvMedia/
├── backend/
│   ├── app/
│   │   ├── __init__.py            # versão do pacote
│   │   ├── config.py              # configurações via variáveis de ambiente
│   │   ├── database.py            # engine, sessão e init do banco
│   │   ├── models.py              # modelos ORM (Media, Playlist, Item, Screen)
│   │   ├── schemas.py             # DTOs Pydantic (entrada/saída)
│   │   ├── crud.py                # operações de acesso a dados
│   │   ├── websocket_manager.py   # registro de conexões WebSocket por tela
│   │   ├── realtime.py            # notificações "reload" para as telas
│   │   ├── main.py                # app FastAPI + arquivos estáticos
│   │   └── routers/
│   │       ├── media.py           # CRUD + upload de mídias
│   │       ├── playlists.py       # CRUD de playlists e itens
│   │       ├── screens.py         # CRUD de telas (TVs)
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

- **Media** — conteúdo exibível: `image`, `video`, `text`, `html` ou `url`.
- **Playlist** — sequência ordenada de itens, reproduzida em loop.
- **PlaylistItem** — liga uma mídia a uma playlist, com `position` e `duration`.
- **Screen** — uma TV, identificada por um `slug` público, vinculada a uma playlist.

### Como o "tempo real" funciona

1. O player na TV abre `WS /ws/display/{slug}` e fica conectado.
2. Qualquer alteração no painel (mídia, playlist ou tela) chama os helpers em
   `realtime.py`, que enviam `{"type": "reload"}` às telas afetadas.
3. O player recebe a mensagem e busca novamente `GET /api/display/{slug}`.
4. Se a `revision` mudou, ele reinicia a reprodução com o novo conteúdo.

Esse desenho mantém o backend como fonte única da verdade e o player simples e
resiliente (reconexão automática + revalidação periódica de segurança).

---

## Como rodar

### Opção A — Docker (recomendado, autohospedado)

```bash
docker compose up --build -d
```

Depois acesse:

- **Painel:** http://SEU_SERVIDOR:8000/admin/
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

1. Abra o **painel** em `/admin/`.
2. Aba **Mídias**: envie imagens/vídeos ou crie blocos de texto/HTML/URL.
3. Aba **Playlists**: crie uma playlist e adicione itens (defina a duração de cada um).
4. Aba **Telas**: crie uma tela e vincule a playlist. Copie a **URL do player**.
5. Na TV, abra a URL `http://SEU_SERVIDOR:8000/player/?screen=SLUG` em tela cheia.
6. Volte ao painel e edite — a TV atualiza **instantaneamente**. ✅

> Dica para TVs: use o navegador em modo quiosque (fullscreen). Em mídia de
> vídeo o player usa `muted` para permitir autoplay sem interação.

---

## Endpoints principais

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Healthcheck |
| GET/POST | `/api/media` | Listar / criar mídia (texto/html/url) |
| POST | `/api/media/upload` | Upload de imagem/vídeo (multipart) |
| PATCH/DELETE | `/api/media/{id}` | Atualizar / excluir mídia |
| GET/POST | `/api/playlists` | Listar / criar playlists |
| POST | `/api/playlists/{id}/items` | Adicionar item |
| POST | `/api/playlists/{id}/reorder` | Reordenar itens |
| GET/POST | `/api/screens` | Listar / criar telas |
| PATCH | `/api/screens/{id}` | Trocar playlist / renomear |
| GET | `/api/display/{slug}` | Conteúdo resolvido para o player |
| WS | `/ws/display/{slug}` | Canal de atualização em tempo real |

---

## Próximos passos sugeridos

- **Autenticação** no painel (ex.: OAuth ou token simples) antes de expor à internet.
- **PostgreSQL** em produção (basta trocar `DATABASE_URL`).
- **Agendamento** (exibir playlists por horário/dia da semana).
- **Transições** e *fit modes* (cover/contain) configuráveis por item.
- **Múltiplas zonas** na tela (faixa de notícias + conteúdo principal).
