# Configuracao e Dependencias

## Dependencias de Sistema

- Python 3.12+
- Node.js apenas para `node --check` dos arquivos JS
- Docker + Docker Compose para ambiente self-hosted
- Opcional: `ffmpeg` e `ffprobe` para processamento de video
- Opcional: Pillow para reescala/otimizacao de imagens

## Dependencias Python

Arquivo: `backend/requirements.txt`

- FastAPI e Uvicorn
- SQLAlchemy
- Pydantic
- python-dotenv
- python-multipart
- Alembic
- Requests
- Pillow opcional/recomendado

## Variaveis Principais

| Variavel | Uso |
|---|---|
| `APP_NAME` | Nome exibido na API |
| `ENVIRONMENT` | `development` ou `production` |
| `DEBUG` | Liga/desliga modo debug |
| `DATABASE_URL` | Conexao SQLAlchemy |
| `MEDIA_DIR` | Pasta persistente das midias |
| `FRONTEND_DIR` | Pasta do frontend estatico |
| `CORS_ORIGINS` | Origens permitidas, separadas por virgula |
| `ADMIN_PASSWORD` | Senha inicial do admin semeado |
| `SECRET_KEY` | Chave HMAC dos tokens |
| `TOKEN_TTL_HOURS` | Tempo de sessao |

## Seguranca

Em `ENVIRONMENT=production`, a aplicacao recusa iniciar se detectar:

- `SECRET_KEY=troque-esta-chave-em-producao`
- `ADMIN_PASSWORD=admin`
- CORS amplo quando combinado a configuracao insegura

Use tambem:

- `FORCE_HTTPS=true` quando estiver atras de proxy HTTPS confiavel.
- `SECURITY_HEADERS_ENABLED=true` para headers basicos.
- `API_DOCS_ENABLED=false` para ocultar `/docs`, `/redoc` e `/openapi.json`.

## Backups

| Variavel | Padrao |
|---|---|
| `BACKUP_ENABLED` | `true` |
| `BACKUP_DIR` | `/app/data/backups` no Docker |
| `BACKUP_INTERVAL_HOURS` | `24` |
| `BACKUP_KEEP` | `7` |

Os backups internos funcionam para SQLite. Para PostgreSQL, use `pg_dump`,
snapshots do provedor ou ferramenta equivalente.

## SMTP e Alertas

Variaveis SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`SMTP_FROM`) alimentam alertas de tela offline e relatorios BI.

Alertas de tela:

- `OFFLINE_ALERT_ENABLED`
- `OFFLINE_ALERT_AFTER_MINUTES`
- `OFFLINE_ALERT_REPEAT_MINUTES`
- `OFFLINE_ALERT_WEBHOOK_URL`
- `OFFLINE_ALERT_EMAIL_TO`

## Processamento de Midia

- `MEDIA_PROCESSING_ENABLED`
- `IMAGE_MAX_DIMENSION`
- `IMAGE_QUALITY`
- `VIDEO_MAX_HEIGHT`
- `VIDEO_CRF`
- `VIDEO_PRESET`
- `MEDIA_PROCESS_TIMEOUT`

Se as ferramentas nao existirem no ambiente, o backend marca processamento como
`skipped` e serve o arquivo original.

## Docker Compose

O Compose usa `.env`, monta `./frontend` como somente leitura e persiste dados
em `adsignage_data`.

```bash
docker compose up --build -d
docker compose logs -f app
docker compose down
```

## Producao com Proxy

Recomendacao:

1. Proxy HTTPS publico terminando TLS.
2. `CORS_ORIGINS=https://seu-dominio`.
3. `ENVIRONMENT=production`.
4. `API_DOCS_ENABLED=false`.
5. Backups externos conferidos periodicamente.
