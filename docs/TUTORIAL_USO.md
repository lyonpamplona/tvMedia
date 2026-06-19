# Tutorial de Uso

## 1. Preparar o Sistema

1. Copie `.env.example` para `.env`.
2. Troque `ADMIN_PASSWORD` e `SECRET_KEY`.
3. Rode `docker compose up --build -d`.
4. Abra `/admin/`.

## 2. Criar Midias

No Studio, abra **Midias**:

- Envie imagem, video ou audio.
- Crie texto, HTML, URL, YouTube, HLS ou PDF.
- Use tags e pastas para organizar.
- Para widgets, escolha o tipo e preencha os campos do assistente.

## 3. Montar Playlists

1. Abra **Playlists**.
2. Crie uma nova playlist.
3. Adicione midias.
4. Ajuste duracao, transicao, foco, som, validade e limite por hora.
5. Use import/export quando quiser transportar uma playlist.

## 4. Criar Tela

1. Abra **Telas**.
2. Crie a tela com resolucao/orientacao.
3. Selecione a zona principal.
4. Vincule uma playlist padrao.
5. Copie a URL do player.

## 5. Abrir na TV

Abra no navegador/kiosk:

```bash
http://SERVIDOR:8000/player/?screen=SLUG
```

Para autoplay com som em Chromium:

```bash
chromium --kiosk --autoplay-policy=no-user-gesture-required "http://SERVIDOR:8000/player/?screen=SLUG"
```

## 6. Usar Agendamentos

No inspetor da zona:

1. Escolha playlist.
2. Defina horario inicial/final.
3. Escolha dias ou datas.
4. Defina prioridade.

## 7. Campanhas

Em uma playlist, abra **Campanhas**:

- Defina modo `scheduled` ou `interrupt`.
- Escolha alvo por tela, grupo ou zona.
- Configure janela de validade e prioridade.
- Use limite por hora para anuncios.

## 8. DataSets

No modal **DataSets**:

- Tabela JSON: cole linhas estruturadas.
- CSV: cole dados separados por virgula.
- JSON remoto: informe URL e use refresh.

Depois crie uma midia/widget do tipo DataSet e aponte para o DataSet cadastrado.

## 9. BI

Abra **BI / Proof-of-play**:

- Veja resumo por tela/midia.
- Exporte CSV.
- Crie relatorios agendados por e-mail.
- Desligue coleta por tela ou midia quando necessario.

## 10. Seguranca

Em **Configuracoes > Seguranca**:

- Ative 2FA com aplicativo autenticador.
- Crie tokens de API para integracoes.
- Revogue tokens que nao devem mais autenticar.

## 11. Backups

Em **Configuracoes > Plataforma**:

- Gere backup manual antes de manutencoes.
- Baixe backups disponiveis.
- Ajuste retencao por `.env`.
