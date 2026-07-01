# Roadmap Corretivo

Este roadmap nao substitui o `ROADMAP.md` funcional. Ele organiza as correcoes
e endurecimentos encontrados na auditoria.

## R1 - Seguranca de Integracoes

Objetivo: API tokens com menor privilegio real.

- Aplicar `scopes` por rota: `read`, `write`, `admin`, `analytics`, `system`.
- Criar dependencia `require_api_scope()`.
- Separar token de sessao humano de token de integracao.
- Registrar auditoria de uso de tokens sensiveis.
- Testar token `read` tentando escrever e recebendo `403`.

## R2 - Protecao SSRF e Fontes Remotas

Objetivo: impedir que URLs remotas acessem rede interna.

- Validar DNS/IP resolvido antes de `requests.get`.
- Bloquear `localhost`, ranges privados, link-local e metadata cloud.
- Criar allowlist opcional por dominio.
- Aplicar em importacao de midia, DataSets JSON e widgets externos.
- Adicionar testes unitarios para URLs bloqueadas.

## R3 - CSP e Headers por Superficie

Objetivo: reduzir risco de XSS/iframe sem quebrar embeds.

- CSP especifica para admin.
- CSP especifica para player, com allowlist de YouTube, Spotify, CDN HLS e fontes.
- `frame-ancestors` controlado.
- Opcao de CSP relaxada para ambientes que usam HTML customizado.

## R4 - Migracoes Alembic Reais

Objetivo: parar de depender de `create_all` em producao.

- Gerar revisao Alembic refletindo schema v35.
- Documentar `alembic upgrade head`.
- Manter migracao leve SQLite apenas como compatibilidade legada.
- Testar banco vazio e banco antigo.

## R5 - Testes de API

Objetivo: cobrir fluxos ponta a ponta.

- TestClient com SQLite temporario.
- Login, 2FA, API token, CRUD de midia, playlist, tela e display payload.
- Campanhas e limites por hora.
- Backups e permissao admin.
- WebSocket smoke test.

## R6 - Modularizacao do Admin

Objetivo: reduzir risco de regressao no `app.js`.

- Separar API client, estado, renderizadores e modais em arquivos menores.
- Manter sem build inicialmente usando `<script type="module">`.
- Criar testes pequenos para helpers puros.

## R7 - Operacao Offline Forte

Objetivo: funcionar melhor em intranet sem internet publica.

- Proxy local para QR code.
- Bundle local de HLS.js.
- Fallback configuravel para clima/cotacoes.
- Indicador no admin para widgets dependentes de rede externa.

## R8 - Git/GitHub e Release

Objetivo: evitar commits acidentais e melhorar entrega.

- Inicializar Git dentro da pasta do projeto, nao na home do usuario.
- Criar release notes por fase.
- Adicionar badge de CI ao README apos subir no GitHub.
- Definir licenca.
- Definir protecao de branch e PR obrigatorio.
