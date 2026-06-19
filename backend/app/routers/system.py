"""Endpoints operacionais de plataforma (P8)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from .. import backup, models
from ..auth import require_admin
from ..config import settings

router = APIRouter(
    prefix="/api/system", tags=["system"], dependencies=[Depends(require_admin)]
)


def _backup_files() -> list[Path]:
    if not settings.backup_dir.exists():
        return []
    return sorted(
        settings.backup_dir.glob("tvmedia-*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


@router.post("/backup", response_model=dict)
def run_backup(user: models.User = Depends(require_admin)) -> dict:
    """Cria backup SQLite manual e aplica rotacao."""
    path = backup.run_backup_now()
    if path is None:
        raise HTTPException(status_code=400, detail="Backup aplicável apenas a SQLite.")
    return {"file": path.name, "size": path.stat().st_size}


@router.get("/backups", response_model=list[dict])
def list_backups(user: models.User = Depends(require_admin)) -> list[dict]:
    """Lista backups disponíveis para download."""
    return [
        {"file": p.name, "size": p.stat().st_size, "modified_at": p.stat().st_mtime}
        for p in _backup_files()
    ]


@router.get("/backups/{filename}")
def download_backup(
    filename: str, user: models.User = Depends(require_admin)
) -> FileResponse:
    """Baixa um backup pelo nome."""
    if "/" in filename or "\\" in filename or not filename.startswith("tvmedia-"):
        raise HTTPException(status_code=404, detail="Backup não encontrado.")
    path = settings.backup_dir / filename
    if not path.exists() or path not in _backup_files():
        raise HTTPException(status_code=404, detail="Backup não encontrado.")
    return FileResponse(path, filename=filename)
