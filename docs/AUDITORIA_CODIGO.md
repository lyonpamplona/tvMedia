# Auditoria Completa do Codigo

Data da varredura: 18/06/2026  
Escopo: backend, frontend admin, player, Docker, Git/GitHub, docs e roadmap.

## Verificacoes Executadas

```powershell
python -m compileall -q backend\app
node --check frontend\admin\app.js
node --check frontend\player\player.js
python -m pytest
rg --files
rg "TODO|FIXME|XXX|HACK|pass$|NotImplemented|unsupported|except Exception|innerHTML|subprocess|shell=True|allow_origins|ADMIN_PASSWORD|SECRET_KEY|CORS_ORIGINS"
rg "router = APIRouter|@router|include_router"
rg "^class .*\\(Base\\)|mapped_column|relationship"
rg "^def |^async def |^class "
```

Resultado local:

- Backend compile: OK
- Admin JS check: OK
- Player JS check: OK
- Pytest: `7 passed, 11 skipped`
- Aviso anterior de cache do pytest tratado com `pytest.ini` (`-p no:cacheprovider`)

## Estado Geral

O sistema esta coeso e funcional para uso self-hosted. As fases P3-P8 estao
refletidas no codigo: organizacao, operacao de telas, DataSets/widgets,
campanhas, BI, seguranca, 2FA, backups e tokens de API.

Nao foram encontrados erros de sintaxe ativos. Os problemas restantes sao de
seguranca, robustez, cobertura, manutenibilidade e producao.

## Achados Ativos

### Alta Prioridade

1. **Escopos de API token ainda nao sao aplicados**

   Arquivos: `backend/app/auth.py`, `backend/app/crud.py`, `backend/app/routers/*`

   O token guarda `scopes`, mas `get_current_user()` autentica o usuario e nao
   restringe operacoes por escopo. Na pratica, um token criado com `read` pode
   herdar o poder integral do usuario dono.

   Impacto: integracoes externas ficam fortes demais.

2. **Busca de URLs remotas pode permitir SSRF em ambiente exposto**

   Arquivos: `backend/app/routers/media.py`, `backend/app/routers/datasets.py`,
   `backend/app/routers/widgets.py`

   Endpoints aceitam `http(s)` para importar midia, JSON remoto e feeds. Como
   sao rotas administrativas, o risco depende de credencial/token, mas em
   producao convem bloquear IPs internos, metadata services e hosts privados.

3. **CSP ausente**

   Arquivo: `backend/app/main.py`

   Headers basicos existem, mas ainda nao ha Content-Security-Policy. Como o
   player renderiza HTML administrado e usa embeds externos, a CSP deve ser
   planejada por modo (admin/player) para reduzir XSS e abuso de iframe/script.

### Media Prioridade

4. **Cobertura automatizada ainda pequena**

   Existem testes de seguranca, TOTP, token e agendamento/proof-of-play, mas
   muitos pulam quando dependencias nao estao instaladas. Falta cobertura de
   endpoints reais com TestClient e banco temporario.

5. **Alembic existe, mas o bootstrap real ainda usa `create_all` + migracao leve**

   Arquivos: `backend/migrations`, `backend/app/database.py`

   Funciona para SQLite local, mas producao multiambiente pede migracoes
   versionadas e revisadas.

6. **Frontend admin monolitico**

   Arquivo: `frontend/admin/app.js`

   O arquivo concentra API client, estado, componentes, modais e fluxos. Isso
   acelera entrega sem build, mas dificulta testes e revisao fina.

7. **Player depende de servicos externos em alguns widgets**

   Arquivo: `frontend/player/player.js`

   QR code, clima, HLS.js CDN e cotacoes dependem de internet. Para intranet
   fechada, e preciso proxy/cache local ou fallback explicito.

8. **Endpoint publico de display depende do slug**

   Arquivo: `backend/app/routers/display.py`

   O player e publico por design. O slug deve ser tratado como segredo de baixa
   sensibilidade; para instalacoes publicas, considerar assinatura curta,
   pairing reforcado ou VPN.

### Baixa Prioridade

9. **`.env` local pode continuar inseguro**

   `.env.example` e Compose foram ajustados, mas o `.env` real do ambiente deve
   ser revisado manualmente para remover `CORS_ORIGINS=*` e segredos padrao.

10. **Raiz Git atual parece estar fora do projeto**

    `git rev-parse --show-toplevel` retornou `C:/Users/lyon`, nao a pasta do
    projeto. Isso gera status poluido e risco de commit acidental da home.

11. **Diretorios temporarios antigos do pytest no workspace**

    Existem `pytest-cache-files-*` com acesso negado. Eles agora estao ignorados
    por `.gitignore`, mas podem ser limpos manualmente quando nao houver locks.

## Pontos Positivos Encontrados

- App registra todos os routers relevantes em `main.py`.
- Configuracao valida segredos em producao.
- CORS com credenciais so e permitido com origens explicitas.
- 2FA usa TOTP local sem dependencia externa.
- Senhas usam PBKDF2 com salt.
- Backups SQLite usam API nativa consistente.
- WebSocket e polling se complementam para resiliencia do player.
- P3-P8 foram documentadas no roadmap e refletidas em arquivos de codigo.

## Conclusao

O codigo esta apto para uso interno/self-hosted e proximo de producao controlada.
Para internet publica, priorize escopos reais em API tokens, protecao SSRF, CSP
e migracoes Alembic completas.
