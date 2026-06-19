# Relatorio Tecnico - tvMedia Studio v35

**Data:** 18/06/2026  
**Escopo:** varredura completa de backend, frontend, player, infra, docs, Git/GitHub e roadmap.  
**Base analisada:** `C:\Users\lyon\Downloads\tvMedia-v35 (1)`.

## Veredito

O sistema esta **funcional e coerente para uso self-hosted/interno**. As fases
P3 a P8 estao aplicadas no codigo, incluindo organizacao de biblioteca, gestao
de telas, DataSets/widgets, campanhas, BI, 2FA, API tokens e backups.

Para exposicao publica, ainda ha trabalho de endurecimento: aplicar escopos
reais nos tokens de API, proteger fetches remotos contra SSRF, adicionar CSP e
ampliar testes de API.

## Validacao Executada

| Check | Resultado |
|---|---|
| `python -m compileall -q backend\app` | OK |
| `node --check frontend\admin\app.js` | OK |
| `node --check frontend\player\player.js` | OK |
| `python -m pytest` | `7 passed, 11 skipped` |

Os skips locais ocorrem quando FastAPI/SQLAlchemy nao estao instalados no
ambiente de execucao. O workflow GitHub Actions instala dependencias antes de
rodar a suite.

## Estado por Camada

### Backend

- FastAPI com routers registrados em `main.py`.
- SQLAlchemy com SQLite padrao e suporte a PostgreSQL por `DATABASE_URL`.
- Configuracao centralizada em `config.py`, com validacao de segredos em producao.
- Autenticacao HMAC, papeis, multiempresa, 2FA TOTP e tokens pessoais de API.
- Tarefas de backup, alertas offline e relatorios agendados no lifespan.
- Docstrings em portugues presentes nos modulos principais.

### Admin

- PWA estatica sem build.
- Studio visual para midias, playlists, telas, zonas, agendas, campanhas,
  DataSets, BI, usuarios, auditoria, seguranca e backups.
- Monolitico em `frontend/admin/app.js`, o que e aceitavel para a estrategia
  sem build, mas deve ser modularizado no roadmap corretivo.

### Player

- Busca `/api/display/{slug}` e conecta em `/ws/display/{slug}`.
- Renderiza zonas, midias, widgets, overlays, HLS, YouTube e background audio.
- Registra proof-of-play e responde comandos do CMS.
- Usa polling como fallback ao WebSocket.

### Infra

- Docker Compose com container unico.
- `.env.example` atualizado para seguranca, CORS, processamento, backup e BI.
- `.gitignore`, `.gitattributes`, `pytest.ini` e CI GitHub Actions adicionados.

## Achados Criticos

1. **API token com escopos nao aplicados**  
   O campo `scopes` existe, mas as rotas ainda nao bloqueiam escrita/admin por
   escopo. Corrigir antes de expor tokens a integracoes externas.

2. **SSRF em fontes remotas**  
   Importacao por URL, DataSets JSON e widgets externos devem bloquear IPs
   privados, localhost e metadata services.

3. **CSP ausente**  
   Headers basicos existem, mas falta Content-Security-Policy por superficie
   (`admin` e `player`).

## Melhorias Aplicadas Nesta Rodada

- README raiz reescrito e personalizado.
- Documentacao tecnica criada em `docs/`.
- Pagina HTML de apresentacao criada.
- Roadmap corretivo criado.
- Compose ajustado para nao forcar CORS `*`.
- `.env.example` documenta variaveis que ja existiam no codigo.
- Git/GitHub configurados com ignore, attributes e CI.
- `pytest.ini` evita cache ruidoso no ambiente local.

## Conclusao

O codigo esta em bom estado para seguir evoluindo. A proxima frente recomendada
e aplicar o `docs/ROADMAP_CORRETIVO.md`, iniciando por escopos de API token e
protecao SSRF.
