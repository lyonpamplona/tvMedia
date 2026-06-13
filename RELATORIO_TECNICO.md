# tvMedia — Relatório Técnico

**Data:** 12/06/2026  
**Escopo:** varredura completa de backend, frontend e infraestrutura.  
**Versão analisada:** estado atual do repositório `/data/adsignage`.

---

## 1. Veredito geral

**O sistema está APTO para uso** em cenário self-hosted/MVP (rede local ou interna de loja, instância única em Raspberry Pi 4). O backend compila sem erros, a arquitetura está coesa e o fluxo principal (cadastro de mídia → playlists → zonas → agendamento → exibição em tempo real via WebSocket) está completo e funcional.

**Ressalva:** para exposição direta à internet pública, há ajustes de segurança recomendados (seção 4). Nenhum deles bloqueia o uso interno imediato.

| Dimensão | Status |
|---|---|
| Compilação backend | OK |
| Fluxo funcional principal | Completo |
| Tempo real (WebSocket) | Funcional |
| Segurança para uso interno | Adequada |
| Segurança para internet pública | Requer ajustes |
| Testes automatizados | Ausentes |
| Migrações de banco | Ausentes (apenas create_all) |

---

## 2. Correções aplicadas nesta varredura

### 2.1 `realtime.py` — função `notify_playlist_screens` (corrigida)
A função consultava `models.Screen.playlist_id`, atributo que **não existe** no modelo `Screen` (a relação playlist→tela é indireta, via zonas e agendamentos). Era código sem chamadas ativas, mas geraria `AttributeError` se utilizada. Foi reescrita para resolver corretamente as telas afetadas, percorrendo `Zone.default_playlist_id` e `Schedule.playlist_id` (com `DISTINCT`).

### 2.2 `embeds.py` — verificação (sem alteração necessária)
As f-strings de YouTube e Spotify foram auditadas byte a byte. Estão **corretas**: produzem URLs limpas como `https://www.youtube.com/embed/VIDEO_ID`. A suspeita inicial de chaves duplicadas era um artefato de exibição do terminal, não um defeito real do código.

---

## 3. Estado por camada

### Backend (FastAPI, ~2.300 linhas)
- **Estrutura:** `main.py` (app + CORS + routers + arquivos estáticos), `auth.py`, `config.py`, `crud.py`, `models.py`, `database.py`, `embeds.py`, `realtime.py`, `websocket_manager.py`, `schemas.py` e 7 routers (auth, media, playlists, screens, zones, schedules, display).
- **Modelos:** Screen, Zone, Schedule, Playlist, PlaylistItem, Media. Slugs gerados com `secrets.token_urlsafe`. Resolução de playlist ativa por dia/horário com prioridade e fallback para playlist padrão da zona — lógica sólida.
- **Banco:** SQLite com PRAGMAs bem ajustados para RPi4 (WAL, busy_timeout, cache, mmap), pool configurado. Apenas `create_all` — sem versionamento de schema.
- **Tempo real:** WebSocket por tela (`/ws/display/{slug}`) com ping/pong e broadcast de recarga. Edições no admin disparam `notify_all_screens` — atualização ao vivo funciona.

### Frontend (admin + player)
- **Player:** consome `/api/display/{slug}`, renderiza zonas posicionadas, faz reconexão WebSocket e troca de mídia com transições. Computa revisão (hash) para evitar recargas desnecessárias.
- **Admin:** IDE estilo Tokyo Night, com onboarding/tutorial, toasts, diálogos customizados e gestão de mídia/playlists/zonas/agendamentos.

### Infraestrutura
- Docker `python:3.12-slim`, uvicorn 1 worker com limites de concorrência, `docker-compose` com `mem_limit` 512m, volume persistente, frontend montado read-only e healthcheck em `/api/health`. Adequado ao alvo RPi4 ARM64 4GB.

---

## 4. Ajustes recomendados (segurança e robustez)

Ordenados por prioridade.

**Alta — antes de expor à internet pública:**
1. **CORS:** hoje usa `allow_origins=["*"]` combinado com `allow_credentials=True`. Essa combinação é inválida para navegadores e amplia superfície a CSRF. Defina origens explícitas via `CORS_ORIGINS`.
2. **Credenciais padrão:** `ADMIN_PASSWORD=admin` e `SECRET_KEY` padrão devem ser obrigatoriamente trocados; idealmente, recusar inicialização com valores default em modo produção.
3. **Rate-limit no login:** atualmente não há proteção contra força bruta. Adicionar limite por IP/tentativas.

**Média:**
4. **Migrações de schema:** adotar Alembic. Hoje qualquer mudança de modelo exige recriar o banco manualmente.
5. **Validação de upload:** a checagem é só por extensão. Validar tipo real (mime/conteúdo) além do limite de 200 MB já existente.
6. **Sanitização de mídia HTML/texto:** conteúdo `html`/`text` é injetado no player; mesmo sendo admin-only, sanitizar para evitar XSS.
7. **Testes automatizados:** não há cobertura. Começar por testes de `crud.resolve_active_playlist_id`, autenticação e endpoints de display.

**Baixa:**
8. **Paginação** nas listagens (mídia/playlists) para escalar o volume.
9. **Token de autenticação:** o HMAC próprio funciona, mas considerar biblioteca madura (JWT) com revogação/refresh.
10. **Backups automáticos** do SQLite + pasta de mídia.

---

## 5. Funções novas sugeridas

- **Painel de saúde das telas:** já existe `last_seen`; expor status online/offline e último contato no admin.
- **Pré-visualização ao vivo** do layout de zonas no editor antes de publicar.
- **Agendamento por data específica** (campanhas com início/fim), além do atual por dia da semana + minutos.
- **Biblioteca de mídia** com pastas, tags e busca.
- **Proof-of-play / métricas de exibição** (o que tocou, quando, em qual tela).
- **Auditoria/logs** de alterações por usuário.
- **Multiusuário com papéis** (admin/operador).
- **Importação em massa** de mídia.

---

## 6. Conclusão

O código está **pronto para uso interno** e bem organizado. Para produção exposta publicamente, priorize os três itens de alta prioridade (CORS, credenciais, rate-limit). As demais recomendações são incrementos de robustez e escala, não bloqueios.
