# API Tecnica

## Autenticacao

Todas as rotas administrativas usam `Authorization: Bearer <token>`.

Ha dois tipos de Bearer:

- Token de sessao HMAC emitido por `POST /api/auth/login`.
- Token pessoal de API com prefixo `tvma_`, criado em Configuracoes > Seguranca.

## Rotas Publicas

| Metodo | Rota | Uso |
|---|---|---|
| `GET` | `/api/health` | Healthcheck |
| `POST` | `/api/display/pair` | Emparelhar tela por codigo |
| `GET` | `/api/display/{slug}` | Payload resolvido para o player |
| `POST` | `/api/display/{slug}/events` | Proof-of-play em lote |
| `POST` | `/api/display/{slug}/commands/{id}/result` | Retorno de comando do player |
| `WS` | `/ws/display/{slug}` | Canal em tempo real do player |
| `GET` | `/api/widgets/news` | Proxy RSS |
| `GET` | `/api/widgets/rates` | Cotacoes de moedas |
| `GET` | `/api/widgets/stocks` | Cotacoes de acoes |
| `GET` | `/api/widgets/datasets/{id}` | Dataset publico para player |

## Rotas Administrativas

| Familia | Rotas |
|---|---|
| Auth | `/api/auth/login`, `/me`, `/change-password`, `/logout`, `/2fa/*`, `/api-tokens` |
| Empresas | `/api/companies`, `/api/branding`, `/api/templates` |
| Usuarios | `/api/users` |
| Midias | `/api/media`, `/upload`, `/bulk`, `/bulk-tags`, `/import-url`, `/purge-unused` |
| Playlists | `/api/playlists`, `/items`, `/reorder`, `/import`, `/export`, `/folders` |
| Telas | `/api/screens`, `/publish`, `/layout-lock`, `/commands`, `/screenshot`, `/map` |
| Zonas | `/api/screens/{screen_id}/zones` |
| Overlays | `/api/screens/{screen_id}/overlays` |
| Agendas | `/api/zones/{zone_id}/schedules` |
| Grupos | `/api/screen-groups` |
| Campanhas | `/api/campaigns` |
| DataSets | `/api/datasets`, `/import-csv`, `/refresh` |
| Analytics | `/api/analytics/proof-of-play/*`, `/reports`, `/screens/health` |
| Sistema | `/api/system/backup`, `/api/system/backups` |
| Auditoria | `/api/audit` |

## Payload do Player

`GET /api/display/{slug}` devolve:

- `screen`: identificacao publica da tela.
- `revision`: hash do conteudo efetivo.
- `zones`: regioes em porcentagem.
- `items`: midias ja resolvidas para cada zona.
- `overlays`: camadas por cima do conteudo.
- `background_audio`: audio opcional da tela.
- `theme` e `emergency`: tema visual e mensagem emergencial.

O player so reinicia a exibicao quando a `revision` muda.

## WebSocket

Canal: `/ws/display/{slug}`

Mensagens do servidor:

```json
{"type": "reload", "reason": "screen_updated"}
```

```json
{"type": "command", "id": 12, "command": "identify", "payload": {}}
```

Mensagens do player:

```json
{"type": "pong"}
```

## Codigos de Erro Relevantes

| Codigo | Significado |
|---|---|
| `401` | Token ausente, expirado, revogado ou 2FA invalido |
| `403` | Papel insuficiente ou tentativa de acessar outra empresa |
| `404` | Recurso fora do escopo ou inexistente |
| `423` | Layout travado |
| `429` | Rate-limit de login |
| `502` | Falha ao buscar fonte remota de DataSet/widget |
