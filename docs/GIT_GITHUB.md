# Git e GitHub

## Estado Detectado

Durante a varredura, `git rev-parse --show-toplevel` retornou:

```text
C:/Users/lyon
```

Isso indica que o Git esta enxergando a pasta do usuario como raiz, e nao
`Downloads/tvMedia-v35 (1)`. O efeito pratico e `git status` listar muitos
arquivos pessoais e pastas fora do projeto.

## Recomendacao

Use um repositorio dedicado para o projeto:

```powershell
cd "C:\Users\lyon\Downloads\tvMedia-v35 (1)"
git init
git add .
git commit -m "chore: base tvmedia studio"
git branch -M main
git remote add origin https://github.com/ORG/REPO.git
git push -u origin main
```

Se ja existir um Git na home sem querer, revise antes de remover. Nao execute
`git reset --hard` ou remocoes recursivas sem backup.

## Arquivos Adicionados

- `.gitignore`: ignora `.env`, caches, banco SQLite, dados gerados e ambientes.
- `.gitattributes`: normaliza EOL e marca binarios.
- `.github/workflows/ci.yml`: valida backend, frontend e testes no GitHub Actions.

## Checklist Antes de Publicar

- Criar `LICENSE`.
- Revisar `.env` e garantir que ele nao foi commitado.
- Definir `SECRET_KEY` e `ADMIN_PASSWORD` fora dos defaults.
- Configurar branch protection.
- Ativar CI no GitHub.
- Criar primeiro release/tag.

## CI

O workflow executa:

```bash
pip install -r backend/requirements.txt
python -m compileall -q backend/app
node --check frontend/admin/app.js
node --check frontend/player/player.js
python -m pytest
```
