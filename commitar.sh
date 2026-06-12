#!/usr/bin/env bash
set -e
# Recria o historico de commits do tvMedia a partir dos zips em downloads/.
# Rode dentro de um repositorio git vazio, com a pasta downloads/ ao lado.
git init -q 2>/dev/null || true
git symbolic-ref HEAD refs/heads/main 2>/dev/null || true

# ---- v01 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v01.zip -d .tmp_v01
cp -a .tmp_v01/tvmedia/. . && rm -rf .tmp_v01
git add -A
GIT_AUTHOR_DATE="2026-06-12T10:47:20" GIT_COMMITTER_DATE="2026-06-12T10:47:20" git commit -q -m "chore: versao inicial do tvMedia (prototipo AdSignage)"

# ---- v02 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v02.zip -d .tmp_v02
cp -a .tmp_v02/tvmedia/. . && rm -rf .tmp_v02
git add -A
GIT_AUTHOR_DATE="2026-06-12T13:17:02" GIT_COMMITTER_DATE="2026-06-12T13:17:02" git commit -q -m "feat(v02): embeds youtube/spotify, pwa painel, router: agendamentos"

# ---- v03 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v03.zip -d .tmp_v03
cp -a .tmp_v03/tvmedia/. . && rm -rf .tmp_v03
git add -A
GIT_AUTHOR_DATE="2026-06-12T17:41:02" GIT_COMMITTER_DATE="2026-06-12T17:41:02" git commit -q -m "feat(v03): migracoes/alembic, router: analytics, router: auditoria"

# ---- v04 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v04.zip -d .tmp_v04
cp -a .tmp_v04/tvmedia/. . && rm -rf .tmp_v04
git add -A
GIT_AUTHOR_DATE="2026-06-12T17:58:30" GIT_COMMITTER_DATE="2026-06-12T17:58:30" git commit -q -m "chore(v04): ajustes e melhorias (9 arquivos)"

# ---- v05 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v05.zip -d .tmp_v05
cp -a .tmp_v05/tvmedia/. . && rm -rf .tmp_v05
git add -A
GIT_AUTHOR_DATE="2026-06-12T18:21:12" GIT_COMMITTER_DATE="2026-06-12T18:21:12" git commit -q -m "chore(v05): ajustes e melhorias (3 arquivos)"

# ---- v06 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v06.zip -d .tmp_v06
cp -a .tmp_v06/tvmedia/. . && rm -rf .tmp_v06
git add -A
GIT_AUTHOR_DATE="2026-06-12T18:54:34" GIT_COMMITTER_DATE="2026-06-12T18:54:34" git commit -q -m "chore(v06): ajustes e melhorias (11 arquivos)"

# ---- v07 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v07.zip -d .tmp_v07
cp -a .tmp_v07/tvmedia/. . && rm -rf .tmp_v07
git add -A
GIT_AUTHOR_DATE="2026-06-12T21:10:00" GIT_COMMITTER_DATE="2026-06-12T21:10:00" git commit -q -m "chore(v07): ajustes e melhorias (9 arquivos)"

# ---- v08 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v08.zip -d .tmp_v08
cp -a .tmp_v08/tvmedia/. . && rm -rf .tmp_v08
git add -A
GIT_AUTHOR_DATE="2026-06-12T21:30:32" GIT_COMMITTER_DATE="2026-06-12T21:30:32" git commit -q -m "feat(v08): router: widgets"

# ---- v09 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v09.zip -d .tmp_v09
cp -a .tmp_v09/tvmedia/. . && rm -rf .tmp_v09
git add -A
GIT_AUTHOR_DATE="2026-06-12T22:00:48" GIT_COMMITTER_DATE="2026-06-12T22:00:48" git commit -q -m "feat(v09): multi-tenant (empresas)"

# ---- v10 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v10.zip -d .tmp_v10
cp -a .tmp_v10/tvmedia/. . && rm -rf .tmp_v10
git add -A
GIT_AUTHOR_DATE="2026-06-12T22:21:52" GIT_COMMITTER_DATE="2026-06-12T22:21:52" git commit -q -m "chore(v10): ajustes e melhorias (2 arquivos)"

# ---- v11 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v11.zip -d .tmp_v11
cp -a .tmp_v11/tvmedia/. . && rm -rf .tmp_v11
git add -A
GIT_AUTHOR_DATE="2026-06-12T10:56:44" GIT_COMMITTER_DATE="2026-06-12T10:56:44" git commit -q -m "chore(v11): ajustes e melhorias (22 arquivos)"

# ---- v12 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v12.zip -d .tmp_v12
cp -a .tmp_v12/tvmedia/. . && rm -rf .tmp_v12
git add -A
GIT_AUTHOR_DATE="2026-06-12T22:56:36" GIT_COMMITTER_DATE="2026-06-12T22:56:36" git commit -q -m "feat(v12): migracoes/alembic, multi-tenant (empresas), pwa painel"

# ---- v13 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v13.zip -d .tmp_v13
cp -a .tmp_v13/tvmedia/. . && rm -rf .tmp_v13
git add -A
GIT_AUTHOR_DATE="2026-06-12T23:13:52" GIT_COMMITTER_DATE="2026-06-12T23:13:52" git commit -q -m "chore(v13): ajustes e melhorias (4 arquivos)"

# ---- v14 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v14.zip -d .tmp_v14
cp -a .tmp_v14/tvmedia/. . && rm -rf .tmp_v14
git add -A
GIT_AUTHOR_DATE="2026-06-12T23:32:38" GIT_COMMITTER_DATE="2026-06-12T23:32:38" git commit -q -m "feat(v14): tamanho de tela (polegadas)"

# ---- v15 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v15.zip -d .tmp_v15
cp -a .tmp_v15/tvmedia/. . && rm -rf .tmp_v15
git add -A
GIT_AUTHOR_DATE="2026-06-13T08:52:00" GIT_COMMITTER_DATE="2026-06-13T08:52:00" git commit -q -m "chore(v15): ajustes e melhorias (2 arquivos)"

# ---- v16 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v16.zip -d .tmp_v16
cp -a .tmp_v16/tvmedia/. . && rm -rf .tmp_v16
git add -A
GIT_AUTHOR_DATE="2026-06-13T09:08:04" GIT_COMMITTER_DATE="2026-06-13T09:08:04" git commit -q -m "feat(v16): pwa player"

# ---- v17 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v17.zip -d .tmp_v17
cp -a .tmp_v17/tvmedia/. . && rm -rf .tmp_v17
git add -A
GIT_AUTHOR_DATE="2026-06-13T09:27:24" GIT_COMMITTER_DATE="2026-06-13T09:27:24" git commit -q -m "feat(v17): processamento de midia"

# ---- v18 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v18.zip -d .tmp_v18
cp -a .tmp_v18/tvmedia/. . && rm -rf .tmp_v18
git add -A
GIT_AUTHOR_DATE="2026-06-13T10:26:18" GIT_COMMITTER_DATE="2026-06-13T10:26:18" git commit -q -m "feat(v18): menus de contexto (p1), modo livre: snap/guias (p2), tocar completo / som (p0)"

# ---- v19 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v19.zip -d .tmp_v19
cp -a .tmp_v19/tvmedia/. . && rm -rf .tmp_v19
git add -A
GIT_AUTHOR_DATE="2026-06-12T11:17:14" GIT_COMMITTER_DATE="2026-06-12T11:17:14" git commit -q -m "feat(v19): frontend redesign (exp.)"

# ---- v20 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v20.zip -d .tmp_v20
cp -a .tmp_v20/tvmedia/. . && rm -rf .tmp_v20
git add -A
GIT_AUTHOR_DATE="2026-06-12T11:31:28" GIT_COMMITTER_DATE="2026-06-12T11:31:28" git commit -q -m "feat(v20): frontend ide (exp.)"

# ---- v21 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v21.zip -d .tmp_v21
cp -a .tmp_v21/tvmedia/. . && rm -rf .tmp_v21
git add -A
GIT_AUTHOR_DATE="2026-06-12T11:50:18" GIT_COMMITTER_DATE="2026-06-12T11:50:18" git commit -q -m "chore(v21): ajustes e melhorias (5 arquivos)"

# ---- v22 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v22.zip -d .tmp_v22
cp -a .tmp_v22/tvmedia/. . && rm -rf .tmp_v22
git add -A
GIT_AUTHOR_DATE="2026-06-12T12:23:46" GIT_COMMITTER_DATE="2026-06-12T12:23:46" git commit -q -m "chore(v22): ajustes e melhorias (3 arquivos)"

# ---- v23 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v23.zip -d .tmp_v23
cp -a .tmp_v23/tvmedia/. . && rm -rf .tmp_v23
git add -A
GIT_AUTHOR_DATE="2026-06-12T12:41:38" GIT_COMMITTER_DATE="2026-06-12T12:41:38" git commit -q -m "feat(v23): router: agendamentos, router: auth, router: zonas"

# ---- v24 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v24.zip -d .tmp_v24
cp -a .tmp_v24/tvmedia/. . && rm -rf .tmp_v24
git add -A
GIT_AUTHOR_DATE="2026-06-12T12:49:36" GIT_COMMITTER_DATE="2026-06-12T12:49:36" git commit -q -m "chore(v24): ajustes e melhorias (3 arquivos)"

# ---- v25 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v25.zip -d .tmp_v25
cp -a .tmp_v25/tvmedia/. . && rm -rf .tmp_v25
git add -A
GIT_AUTHOR_DATE="2026-06-12T13:08:30" GIT_COMMITTER_DATE="2026-06-12T13:08:30" git commit -q -m "chore(v25): ajustes e melhorias (4 arquivos)"

# ---- v26 ----
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name downloads ! -name commitar.sh -exec rm -rf {} +
unzip -q downloads/tvmedia-v26.zip -d .tmp_v26
cp -a .tmp_v26/tvmedia/. . && rm -rf .tmp_v26
git add -A
GIT_AUTHOR_DATE="2026-06-12T10:32:58" GIT_COMMITTER_DATE="2026-06-12T10:32:58" git commit -q -m "chore(v26): ajustes e melhorias (19 arquivos)"

echo "Pronto: 26 commits criados."
