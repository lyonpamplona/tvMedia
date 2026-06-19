# Arquitetura

<img src="assets/tvmedia-signal.svg" width="76" alt="tvMedia signal" />

O tvMedia Studio e uma aplicacao FastAPI autohospedada. O backend serve a API,
os arquivos estaticos do painel, o player de TV e a pasta publica de midias. O
player e um cliente leve que busca um payload resolvido por tela e reage a
notificacoes WebSocket.

## Diagrama Logico

```text
Admin Web
  |  REST autenticado + Bearer
  v
FastAPI /api
  |-- Auth, Users, Companies, Audit
  |-- Media, Folders, Playlists
  |-- Screens, Zones, Schedules, Groups
  |-- Campaigns, DataSets, Widgets
  |-- Analytics, Reports, System Backups
  |
  | SQLAlchemy
  v
SQLite/PostgreSQL

Player TV
  | GET /api/display/{slug}
  | WS /ws/display/{slug}
  v
Payload resolvido: tela -> zonas -> campanha/agendamento -> playlist -> midias
```

## Camadas

### Backend

- `main.py`: instancia FastAPI, CORS, HTTPS opcional, headers de seguranca,
  routers, healthcheck, arquivos estaticos e tarefas no lifespan.
- `config.py`: variaveis de ambiente, validacao de seguranca e defaults.
- `database.py`: engine SQLAlchemy, sessao por request e migracoes leves SQLite.
- `models.py`: entidades persistidas.
- `schemas.py`: contratos Pydantic de entrada/saida.
- `crud.py`: operacoes de persistencia e regras de consulta.
- `services.py`: montagem do payload do player.
- `realtime.py` e `websocket_manager.py`: notificacoes ao player.
- `alerts.py`, `backup.py`, `reports.py`: tarefas em background.

### Frontend Admin

`frontend/admin` e uma PWA estatica sem build. O arquivo principal e
`app.js`, que mantem estado em memoria, chama a API, renderiza o Studio e abre
modais para DataSets, BI, campanhas, seguranca, backups e operacao de telas.

### Player

`frontend/player/player.js` renderiza o payload de display em tela cheia. Ele
aplica zonas, transicoes, widgets, YouTube/HLS, overlays, background audio,
registro de proof-of-play e comandos enviados pelo CMS.

### Persistencia

SQLite e o padrao, com WAL e PRAGMAs para uso em hardware modesto. PostgreSQL
e suportado pela troca de `DATABASE_URL`, mas os backups automaticos internos
so se aplicam a SQLite.

## Tarefas em Background

Durante o lifespan da aplicacao:

- `backup.backup_scheduler`: cria backups SQLite e aplica rotacao.
- `alerts.offline_alert_scheduler`: detecta telas offline e envia webhook/SMTP.
- `reports.report_scheduler`: envia relatorios BI por e-mail.

## Docstrings

O backend usa docstrings em portugues em modulos e funcoes principais. O padrao
adotado e explicar responsabilidade, parametros quando relevantes e efeito
operacional, evitando comentarios redundantes.
