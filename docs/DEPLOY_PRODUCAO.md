# Checklist de deploy em producao

Guia objetivo para subir o tvMedia em producao com seguranca. Itens marcados
com :rotating_light: sao **bloqueantes**: a aplicacao recusa iniciar com
`ENVIRONMENT=production` enquanto eles nao forem resolvidos (`validate_security`).

## 1. Segredos e identidade
- :rotating_light: `SECRET_KEY`: gere uma chave longa e aleatoria. Ex.: `python -c "import secrets;print(secrets.token_urlsafe(48))"`.
- :rotating_light: `ADMIN_PASSWORD`: defina uma senha forte (o valor padrao `admin` e recusado em producao). Troque a senha do usuario `admin` apos o primeiro login.
- `TOKEN_TTL_HOURS`: ajuste a validade do token de sessao conforme a politica interna.
- Ative TOTP (2FA) para as contas administrativas.

## 2. Rede e CORS
- :rotating_light: `CORS_ORIGINS`: liste apenas as origens HTTPS publicas reais (ex.: `https://painel.suaempresa.com`). Nunca use `*` em producao.
- `FORCE_HTTPS=true` quando estiver atras de um proxy HTTPS corretamente configurado.
- `SECURITY_HEADERS_ENABLED=true` e `HSTS_SECONDS=31536000` (1 ano).
- `API_DOCS_ENABLED=false` para ocultar `/docs`, `/redoc` e `/openapi.json`.

## 3. Banco de dados
- **SQLite** (padrao): adequado para uma instancia (Raspberry Pi / poucas dezenas de telas). O WAL ja vem habilitado. Garanta backups (`BACKUP_ENABLED=true`).
- **PostgreSQL** (escala/HA): defina `DATABASE_URL=postgresql+psycopg://user:senha@host:5432/adsignage`.
  - A migracao leve embutida e exclusiva de SQLite. Em Postgres, aplique o esquema via Alembic:
    ```bash
    cd backend
    alembic upgrade head
    ```
  - A revisao `0002_live_graphics` adiciona, de forma idempotente, o esquema das fases L1-L5 (overlays, `weight`, `is_ad`, tabela `media_cues`).

## 4. Retencao e armazenamento
- `PLAY_EVENTS_RETENTION_DAYS`: defina (ex.: `180`) para expurgar automaticamente eventos antigos de proof-of-play e evitar crescimento ilimitado. `0` desativa.
- `RETENTION_CHECK_HOURS`: intervalo da limpeza (padrao 24h).
- `MAX_UPLOAD_MB`: limite de upload de midia.

## 5. Observabilidade e operacao
- `GET /api/health`: liveness/Healthcheck do container.
- `GET /api/metrics`: metricas no formato Prometheus (requer token). Aponte o scraper com `Authorization: Bearer <token de API>`.
- Configure alertas de tela offline (`OFFLINE_ALERT_*`) e, opcionalmente, relatorios agendados (`REPORT_SCHEDULER_ENABLED`).
- A trilha de auditoria (`/api/audit`) registra acoes administrativas, incluindo disparos da mesa de transmissao ao vivo.

## 6. Backups
- `BACKUP_ENABLED=true`, `BACKUP_INTERVAL_HOURS`, `BACKUP_KEEP` para o SQLite.
- Em Postgres, use as ferramentas do proprio SGBD (`pg_dump`/snapshots).

## 7. Verificacao pos-deploy
- [ ] App sobe sem avisos de seguranca no log.
- [ ] Login com a nova senha funciona; senha padrao removida.
- [ ] `/docs` inacessivel (se desativado).
- [ ] Player de uma tela carrega via HTTPS.
- [ ] `GET /api/health` responde `200`.
- [ ] `alembic upgrade head` aplicado (somente Postgres).
