<p align="center">
  <img src="docs/assets/tvmedia-signal.svg" width="128" alt="tvMedia signal" />
</p>

# tvMedia Studio

**CMS autohospedado para sinalizacao digital**, com painel web, player para TVs,
WebSocket em tempo real, proof-of-play, campanhas, DataSets, widgets e controles
operacionais para uso em lojas, recepcoes, redes internas e ambientes self-hosted.

O projeto roda como um unico backend FastAPI que tambem serve o painel admin, o
player e os arquivos de midia. O frontend e HTML/CSS/JS puro, sem etapa de build.

## Visao Rapida

| Camada | Papel |
|---|---|
| Backend | FastAPI, SQLAlchemy, SQLite/PostgreSQL, API REST, WebSocket, tarefas em background |
| Admin | Studio visual para midias, playlists, telas, zonas, campanhas, BI e seguranca |
| Player | Aplicacao fullscreen para TV/kiosk que consome `/api/display/{slug}` |
| Infra | Docker Compose, backups SQLite, healthcheck, variaveis por `.env` |

## Recursos

- Autenticacao por usuario/senha, papeis, super admin, multiempresa e 2FA TOTP.
- Tokens Bearer pessoais (`tvma_...`) para integracoes externas.
- Mídias: imagem, video, texto, HTML, URL, YouTube, audio, HLS, PDF e widgets.
- Playlists com ordenacao, duracao, transicao, som, validade e limite por hora.
- Telas com zonas, temas, overlays, background audio, publicacao e trava de layout.
- Agendamentos por dia/horario, campanhas, grupos de telas e comandos ao player.
- DataSets internos, CSV colado e JSON remoto para widgets dinamicos.
- Proof-of-play, resumo BI, exportacao CSV e relatorios agendados por e-mail.
- Alertas de tela offline por webhook/SMTP e backup automatico SQLite.

## Como Rodar

### Docker Compose

```bash
cp .env.example .env
# edite ADMIN_PASSWORD, SECRET_KEY e CORS_ORIGINS antes de producao
docker compose up --build -d
```

Acesse:

- Painel: `http://localhost:8000/admin/`
- Player: `http://localhost:8000/player/?screen=SLUG`
- API docs: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/api/health`

### Desenvolvimento Local

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Primeiro Uso

1. Copie `.env.example` para `.env` e troque `ADMIN_PASSWORD` e `SECRET_KEY`.
2. Suba o sistema.
3. Entre no admin em `/admin/`.
4. Crie midias e uma playlist.
5. Crie uma tela, vincule a playlist na zona principal e copie a URL do player.
6. Abra a URL do player na TV/navegador kiosk.
7. Edite no painel: o player recebe WebSocket e recarrega quando a revisao muda.

## Documentacao

- [Arquitetura](docs/ARQUITETURA.md)
- [Fluxos do sistema](docs/FLUXOS.md)
- [Modulos do codigo](docs/MODULOS.md)
- [API tecnica](docs/API_TECNICA.md)
- [Configuracao e dependencias](docs/CONFIGURACAO.md)
- [Tutorial de uso](docs/TUTORIAL_USO.md)
- [Comandos operacionais](docs/COMANDOS.md)
- [Auditoria do codigo](docs/AUDITORIA_CODIGO.md)
- [Roadmap corretivo](docs/ROADMAP_CORRETIVO.md)
- [Git e GitHub](docs/GIT_GITHUB.md)
- [Pagina HTML de apresentacao](docs/APRESENTACAO.html)

## Verificacao

```bash
python -m compileall -q backend\app
node --check frontend\admin\app.js
node --check frontend\player\player.js
python -m pytest
```

Estado desta varredura: `7 passed, 11 skipped` no ambiente local atual. Os
skips ocorrem quando FastAPI/SQLAlchemy nao estao instalados no ambiente de
execucao dos testes.

## Producao

- Use `ENVIRONMENT=production`.
- Defina `SECRET_KEY` forte e `ADMIN_PASSWORD` fora dos valores padrao.
- Restrinja `CORS_ORIGINS` a origem HTTPS publica.
- Coloque atras de proxy reverso HTTPS (Caddy/Nginx/Traefik).
- Ative `FORCE_HTTPS=true` apenas quando o proxy/headers estiverem corretos.
- Configure backup, SMTP e politica de retencao conforme o ambiente.

## Licenca

Nao ha arquivo de licenca publicado neste checkout. Antes de abrir o repositorio
publicamente, defina a licenca desejada e inclua `LICENSE`.
