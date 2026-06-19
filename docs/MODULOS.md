# Modulos do Codigo

## Raiz

| Arquivo | Funcao |
|---|---|
| `README.md` | Capa tecnica e instrucoes rapidas |
| `ROADMAP.md` | Plano evolutivo P3-P8 e estado aplicado |
| `RELATORIO_TECNICO.md` | Resultado consolidado da auditoria |
| `.env.example` | Variaveis de ambiente documentadas |
| `docker-compose.yml` | Orquestracao do container unico |
| `pytest.ini` | Configuracao de testes sem cache ruidoso |

## Backend `backend/app`

| Modulo | Responsabilidade |
|---|---|
| `main.py` | App FastAPI, routers, CORS, HTTPS, headers, static files e lifespan |
| `config.py` | Settings por ambiente, seguranca, CORS, SMTP, backup, BI |
| `database.py` | Engine, sessao, PRAGMAs SQLite e migracao leve |
| `models.py` | ORM: Company, User, ApiToken, Media, Playlist, Screen, Zone, Campaign, DataSet, BI |
| `schemas.py` | Contratos Pydantic de API, player e admin |
| `crud.py` | Operacoes de persistencia e regras de negocio persistentes |
| `services.py` | Montagem do payload final do player |
| `auth.py` | Token HMAC, API token, escopo multiempresa e guardas de papel |
| `security.py` | Hash de senha PBKDF2 e rate limiter |
| `totp.py` | TOTP RFC 6238 minimalista para 2FA |
| `realtime.py` | Notificacao seletiva de telas via WebSocket |
| `websocket_manager.py` | Registro e envio por conexao WebSocket |
| `media_processing.py` | Otimizacao opcional com Pillow/ffmpeg |
| `embeds.py` | Normalizacao de YouTube/Spotify/embeds |
| `alerts.py` | Monitoramento de telas offline |
| `reports.py` | CSV/PDF textual e envio de relatorios agendados |
| `backup.py` | Backup SQLite com rotacao |

## Routers

| Router | Prefixo | Papel |
|---|---|---|
| `auth.py` | `/api/auth` | Login, logout, senha, 2FA, tokens de API |
| `companies.py` | `/api/companies`, `/api/branding`, `/api/templates` | Multiempresa, branding e templates |
| `users.py` | `/api/users` | Usuarios por escopo |
| `media.py` | `/api/media` | CRUD, upload, URL remota, processamento e limpeza |
| `folders.py` | `/api/folders` | Pastas de midia |
| `playlists.py` | `/api/playlists` | Playlists, itens, reorder, import/export e pastas |
| `screens.py` | `/api/screens` | Telas, publish, lock, comandos, mapa e layout import/export |
| `zones.py` | `/api/screens/{screen_id}/zones` | Zonas e respeito a layout lock |
| `schedules.py` | `/api/zones/{zone_id}/schedules` | Agendamentos |
| `overlays.py` | `/api/screens/{screen_id}/overlays` | Overlays por tela |
| `screen_groups.py` | `/api/screen-groups` | Grupos estaticos/dinamicos |
| `campaigns.py` | `/api/campaigns` | Campanhas e alvos |
| `datasets.py` | `/api/datasets` | DataSets internos/remotos |
| `widgets.py` | `/api/widgets` | Proxies de news, rates, stocks e dataset publico |
| `display.py` | `/api/display`, `/ws/display` | Payload publico do player, pairing, events e comandos |
| `analytics.py` | `/api/analytics` | Proof-of-play, BI, relatorios e saude |
| `audit.py` | `/api/audit` | Logs de auditoria |
| `system.py` | `/api/system` | Backup manual/listagem/download |

## Frontend Admin

| Arquivo | Papel |
|---|---|
| `frontend/admin/index.html` | Estrutura base, login, Studio e overlays |
| `frontend/admin/styles.css` | Visual do Studio, modais, tabelas, canvas e PWA |
| `frontend/admin/app.js` | Estado, API client, renderizacao e interacoes |
| `frontend/admin/sw.js` | Cache PWA versionado |
| `frontend/admin/manifest.webmanifest` | Instalacao PWA |

## Player

| Arquivo | Papel |
|---|---|
| `frontend/player/index.html` | Stage fullscreen |
| `frontend/player/player.js` | Motor de reproducao, widgets, eventos, comandos e WebSocket |
| `frontend/player/sw.js` | Cache PWA do player |
