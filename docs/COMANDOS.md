# Comandos de Uso

## Ambiente Local

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker

```powershell
docker compose up --build -d
docker compose logs -f app
docker compose ps
docker compose down
```

## Verificacao

```powershell
python -m compileall -q backend\app
node --check frontend\admin\app.js
node --check frontend\player\player.js
python -m pytest
```

## Banco e Backups

Backup manual via API:

```powershell
$token = "COLE_O_TOKEN"
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/system/backup -Headers @{ Authorization = "Bearer $token" }
```

Listar backups:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/system/backups -Headers @{ Authorization = "Bearer $token" }
```

## API Token

Use tokens `tvma_...` no mesmo header:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/media -Headers @{ Authorization = "Bearer tvma_xxx" }
```

## Healthcheck

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

## Git

```powershell
git init
git add .
git commit -m "chore: base tvmedia studio"
git branch -M main
git remote add origin https://github.com/ORG/REPO.git
git push -u origin main
```
