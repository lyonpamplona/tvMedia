# Fluxos do Sistema

## 1. Login e Sessao

1. Admin envia `POST /api/auth/login` com usuario, senha e opcionalmente 2FA.
2. `routers/auth.py` valida rate-limit, senha e TOTP quando habilitado.
3. `auth.create_token()` emite token HMAC com `sub`, `role`, `ver` e expiracao.
4. Admin guarda o token em `localStorage` e envia `Authorization: Bearer`.
5. Alterar senha incrementa `token_version` e invalida sessoes antigas.

## 2. Conteudo ate a TV

1. Operador cria midias em `/api/media`.
2. Midias entram em playlists por `/api/playlists/{id}/items`.
3. Playlist e vinculada a zona da tela ou a uma campanha.
4. Player chama `GET /api/display/{slug}`.
5. `services.build_display_payload()` resolve publicacao, campanha, agenda,
   limite por hora, midias ativas, overlays e tema.
6. Player renderiza zonas em porcentagem e roda o loop de reproducao.

## 3. Tempo Real

1. Player conecta em `WS /ws/display/{slug}`.
2. Alteracoes no admin chamam helpers de `realtime.py`.
3. WebSocket envia `reload`, `identify` ou comandos operacionais.
4. Player recarrega o payload quando a `revision` muda.
5. Como seguranca, o player tambem revalida periodicamente por polling.

## 4. Agendamento

1. Cada zona possui playlist padrao.
2. `Schedule` pode sobrescrever a playlist por dia, horario, data e prioridade.
3. O horario e calculado no fuso da tela (`Screen.timezone`).
4. Se nenhum agendamento bate, vence a playlist padrao.

## 5. Campanhas

1. Campanha aponta para playlist e alvos: tela, grupo ou zona.
2. Janela de validade, prioridade e modo (`scheduled`/`interrupt`) filtram a campanha.
3. O player recebe a playlist efetiva da campanha quando ela vence.
4. `max_plays_per_hour` usa proof-of-play para limitar repeticao.

## 6. DataSets e Widgets

1. Admin cria DataSet manual, CSV colado ou JSON remoto.
2. O backend armazena colunas, linhas, fallback e status de refresh.
3. Player usa widgets `dataset`, `stocks`, `rates`, `news`, `calendar`,
   `worldclock`, `menuboard`, `qrcode`, `weather`, `countdown` e outros.
4. Quando fonte externa falha, o player/backend tenta fallback local.

## 7. BI e Proof-of-Play

1. Player registra eventos em lote em `/api/display/{slug}/events`.
2. Backend descarta eventos quando coleta esta desligada na tela ou midia.
3. Admin consulta resumo, detalhes e CSV por `/api/analytics/proof-of-play/*`.
4. Relatorios agendados geram CSV e PDF textual e enviam por SMTP.

## 8. Operacao de Telas

1. Telas enviam `last_seen` ao buscar payload ou conectar via WebSocket.
2. Admin acompanha saude, mapa/lista, grupos e comandos pendentes.
3. Comandos suportados pelo player: recarregar, identificar e screenshot best-effort.
4. Comandos de hardware retornam `unsupported` sem agente externo.

## 9. Backup e Plataforma

1. `backup_scheduler` roda periodicamente quando `BACKUP_ENABLED=true`.
2. Admin pode gerar backup manual em `/api/system/backup`.
3. Backups aparecem em `/api/system/backups` e podem ser baixados.
4. A rotina vale para SQLite; PostgreSQL deve usar ferramenta propria.
